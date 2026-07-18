from unittest.mock import patch

from django.test import TestCase

from clinics.models import Clinic, Doctor, FAQItem, Service

from . import responder
from .models import AppointmentRequest, Conversation, Message
from .prompt import build_system_prompt


def make_clinic():
    clinic = Clinic.objects.create(
        name="Dent Klinika",
        slug="dent-klinika",
        address="Bakı, Nizami küç. 5",
        phone="+994501234567",
        working_hours_text="B.e-Şənbə 09:00-19:00, Bazar bağlı",
        extra_info="Pulsuz parkinq var.",
    )
    Service.objects.create(
        clinic=clinic, name="Diş təmizliyi", price_text="50 AZN"
    )
    Service.objects.create(
        clinic=clinic,
        name="İmplant",
        price_text="800 AZN-dən",
        description="Konsultasiya pulsuzdur",
    )
    Service.objects.create(
        clinic=clinic, name="Köhnə xidmət", price_text="1 AZN", is_active=False
    )
    Doctor.objects.create(
        clinic=clinic, name="Dr. Aysel Məmmədova", specialty="Ortodont"
    )
    FAQItem.objects.create(
        clinic=clinic,
        question="Kartla ödəniş olur?",
        answer="Bəli, nağd və kartla ödəniş mümkündür.",
    )
    return clinic


class BuildSystemPromptTests(TestCase):
    def setUp(self):
        self.clinic = make_clinic()
        self.prompt = build_system_prompt(self.clinic)

    def test_contains_clinic_core_info(self):
        for fragment in [
            "Dent Klinika",
            "Bakı, Nizami küç. 5",
            "+994501234567",
            "B.e-Şənbə 09:00-19:00",
            "Pulsuz parkinq var.",
        ]:
            self.assertIn(fragment, self.prompt)

    def test_contains_active_services_with_prices(self):
        self.assertIn("Diş təmizliyi", self.prompt)
        self.assertIn("50 AZN", self.prompt)
        self.assertIn("İmplant", self.prompt)
        self.assertIn("800 AZN-dən", self.prompt)

    def test_excludes_inactive_services(self):
        self.assertNotIn("Köhnə xidmət", self.prompt)

    def test_contains_doctors_and_faq(self):
        self.assertIn("Dr. Aysel Məmmədova", self.prompt)
        self.assertIn("Ortodont", self.prompt)
        self.assertIn("Kartla ödəniş olur?", self.prompt)
        self.assertIn("nağd və kartla", self.prompt)

    def test_contains_medical_advice_guardrail(self):
        self.assertIn("tibbi məsləhət", self.prompt.lower())

    def test_azerbaijani_language_instruction(self):
        self.assertIn("Azərbaycan dilində", self.prompt)


class ConversationModelTests(TestCase):
    def setUp(self):
        self.clinic = make_clinic()

    def test_conversation_defaults(self):
        conv = Conversation.objects.create(
            clinic=self.clinic,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )
        self.assertFalse(conv.bot_paused)
        self.assertEqual(conv.messages.count(), 0)

    def test_unique_conversation_per_channel_user(self):
        from django.db import IntegrityError

        Conversation.objects.create(
            clinic=self.clinic,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )
        with self.assertRaises(IntegrityError):
            Conversation.objects.create(
                clinic=self.clinic,
                channel=Conversation.Channel.WHATSAPP,
                external_user_id="994501112233",
            )

    def test_message_ordering_is_chronological(self):
        conv = Conversation.objects.create(
            clinic=self.clinic,
            channel=Conversation.Channel.INSTAGRAM,
            external_user_id="ig-123",
        )
        first = Message.objects.create(
            conversation=conv, role=Message.Role.CUSTOMER, text="Salam"
        )
        second = Message.objects.create(
            conversation=conv, role=Message.Role.BOT, text="Xoş gəlmisiniz!"
        )
        self.assertEqual(list(conv.messages.all()), [first, second])

    def test_appointment_request_defaults_to_new(self):
        conv = Conversation.objects.create(
            clinic=self.clinic,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )
        req = AppointmentRequest.objects.create(
            clinic=self.clinic,
            conversation=conv,
            customer_name="Orxan",
            phone="+994551234567",
            service_text="İmplant konsultasiyası",
            preferred_time_text="çərşənbə axşamüstü",
        )
        self.assertEqual(req.status, AppointmentRequest.Status.NEW)


# --- Fake Anthropic client (tool-use agentini test etmək üçün) ---


class FakeBlock:
    def __init__(self, type, text=None, name=None, input=None, id=None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input or {}
        self.id = id


class FakeResponse:
    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


class FakeClient:
    """client.messages.create(...) ardıcıl hazır cavablar qaytarır."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def text_response(text):
    return FakeResponse([FakeBlock("text", text=text)], "end_turn")


class AgentTests(TestCase):
    def setUp(self):
        self.clinic = make_clinic()
        self.conv = Conversation.objects.create(
            clinic=self.clinic,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )

    def _add_customer_msg(self, text):
        Message.objects.create(
            conversation=self.conv, role=Message.Role.CUSTOMER, text=text
        )

    def test_plain_answer_returned(self):
        self._add_customer_msg("Diş təmizliyi neçəyədir?")
        client = FakeClient([text_response("Diş təmizliyi 50 AZN-dir.")])
        reply = responder.generate_reply(self.conv, client=client)
        self.assertEqual(reply, "Diş təmizliyi 50 AZN-dir.")

    def test_history_maps_roles_and_starts_with_user(self):
        # Bot mesajı əvvəldə olsa da, ilk mesaj user olmalıdır
        Message.objects.create(
            conversation=self.conv, role=Message.Role.BOT, text="Xoş gəlmisiniz!"
        )
        self._add_customer_msg("Salam")
        client = FakeClient([text_response("Salam, necə kömək edə bilərəm?")])
        responder.generate_reply(self.conv, client=client)
        sent = client.calls[0]["messages"]
        self.assertEqual(sent[0]["role"], "user")
        self.assertEqual(sent[0]["content"], "Salam")

    @patch("assistant.notifications.notify_appointment")
    def test_appointment_tool_creates_request_and_notifies(self, mock_notify):
        self._add_customer_msg("Sabaha randevu istəyirəm, Orxan, 0551234567")
        tool_use = FakeResponse(
            [
                FakeBlock(
                    "tool_use",
                    name="create_appointment_request",
                    id="toolu_1",
                    input={
                        "customer_name": "Orxan",
                        "phone": "0551234567",
                        "service": "diş təmizliyi",
                        "preferred_time": "sabah",
                    },
                )
            ],
            "tool_use",
        )
        final = text_response("Məlumatlarınızı qeyd etdim, sizinlə əlaqə saxlanılacaq.")
        client = FakeClient([tool_use, final])

        reply = responder.generate_reply(self.conv, client=client)

        appt = AppointmentRequest.objects.get()
        self.assertEqual(appt.customer_name, "Orxan")
        self.assertEqual(appt.phone, "0551234567")
        self.assertEqual(appt.clinic, self.clinic)
        mock_notify.assert_called_once()
        self.assertIn("qeyd etdim", reply)
        # İkinci çağırışda tool_result göndərilib
        self.assertEqual(len(client.calls), 2)

    @patch("assistant.notifications.notify_handoff")
    def test_handoff_tool_pauses_bot_and_notifies(self, mock_notify):
        self._add_customer_msg("Operatorla danışmaq istəyirəm")
        tool_use = FakeResponse(
            [
                FakeBlock(
                    "tool_use",
                    name="handoff_to_operator",
                    id="toolu_2",
                    input={"reason": "Müştəri operator istədi"},
                )
            ],
            "tool_use",
        )
        client = FakeClient([tool_use, text_response("Sizi operatora yönləndirirəm.")])

        responder.generate_reply(self.conv, client=client)

        self.conv.refresh_from_db()
        self.assertTrue(self.conv.bot_paused)
        mock_notify.assert_called_once()

    @patch("assistant.notifications.notify_handoff")
    def test_llm_error_falls_back_and_alerts(self, mock_notify):
        self._add_customer_msg("Salam")

        class BoomClient:
            def __init__(self):
                self.messages = self

            def create(self, **kwargs):
                raise RuntimeError("API down")

        reply = responder.generate_reply(self.conv, client=BoomClient())
        self.assertEqual(reply, responder.FALLBACK_REPLY)
        mock_notify.assert_called_once()

    def test_empty_history_returns_fallback(self):
        client = FakeClient([])
        reply = responder.generate_reply(self.conv, client=client)
        self.assertEqual(reply, responder.FALLBACK_REPLY)
