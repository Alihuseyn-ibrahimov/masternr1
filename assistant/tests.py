from unittest.mock import patch

from django.test import TestCase

from businesses.models import Business, FAQItem, Service, StaffMember

from . import responder
from .models import Conversation, CustomerRequest, Message
from .prompt import build_system_prompt


def make_business(**overrides):
    defaults = dict(
        name="Test Tədris Mərkəzi",
        slug="test-tedris-merkezi",
        address="Bakı, Nizami küç. 5",
        phone="+994501234567",
        working_hours_text="B.e-Şənbə 10:00-19:00, Bazar bağlı",
        extra_info="Onlayn qruplar da var.",
        staff_label="Repetitorlar",
    )
    defaults.update(overrides)
    business = Business.objects.create(**defaults)
    Service.objects.create(
        business=business, name="Magistratura hazırlığı", price_text="300 AZN"
    )
    Service.objects.create(
        business=business,
        name="Doktorantura hazırlığı",
        price_text="500 AZN-dən",
        description="İlk dərs pulsuzdur",
    )
    Service.objects.create(
        business=business, name="Köhnə kurs", price_text="1 AZN", is_active=False
    )
    StaffMember.objects.create(
        business=business, name="Aysel Məmmədova", specialty="Riyaziyyat"
    )
    FAQItem.objects.create(
        business=business,
        question="Kartla ödəniş olur?",
        answer="Bəli, nağd və kartla ödəniş mümkündür.",
    )
    return business


class BuildSystemPromptTests(TestCase):
    def setUp(self):
        self.business = make_business()
        self.prompt = build_system_prompt(self.business)

    def test_contains_business_core_info(self):
        for fragment in [
            "Test Tədris Mərkəzi",
            "Bakı, Nizami küç. 5",
            "+994501234567",
            "B.e-Şənbə 10:00-19:00",
            "Onlayn qruplar da var.",
        ]:
            self.assertIn(fragment, self.prompt)

    def test_contains_active_services_with_prices(self):
        self.assertIn("Magistratura hazırlığı", self.prompt)
        self.assertIn("300 AZN", self.prompt)
        self.assertIn("Doktorantura hazırlığı", self.prompt)
        self.assertIn("500 AZN-dən", self.prompt)

    def test_excludes_inactive_services(self):
        self.assertNotIn("Köhnə kurs", self.prompt)

    def test_contains_staff_members_and_faq(self):
        self.assertIn("Aysel Məmmədova", self.prompt)
        self.assertIn("Riyaziyyat", self.prompt)
        self.assertIn("Kartla ödəniş olur?", self.prompt)
        self.assertIn("nağd və kartla", self.prompt)

    def test_uses_configured_staff_label(self):
        self.assertIn("Repetitorlar", self.prompt)

    def test_default_guardrail_applies_when_blank(self):
        self.assertIn("zəmanət", self.prompt.lower())

    def test_custom_guardrail_replaces_default(self):
        business = make_business(
            slug="ozel-guardrail",
            guardrail_text="Qəbul faizinə zəmanət vermə.",
        )
        prompt = build_system_prompt(business)
        self.assertIn("Qəbul faizinə zəmanət vermə.", prompt)
        self.assertNotIn("tibbi", prompt.lower())

    def test_azerbaijani_language_instruction(self):
        self.assertIn("Azərbaycan dilində", self.prompt)


class ConversationModelTests(TestCase):
    def setUp(self):
        self.business = make_business()

    def test_conversation_defaults(self):
        conv = Conversation.objects.create(
            business=self.business,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )
        self.assertFalse(conv.bot_paused)
        self.assertEqual(conv.messages.count(), 0)

    def test_unique_conversation_per_channel_user(self):
        from django.db import IntegrityError

        Conversation.objects.create(
            business=self.business,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )
        with self.assertRaises(IntegrityError):
            Conversation.objects.create(
                business=self.business,
                channel=Conversation.Channel.WHATSAPP,
                external_user_id="994501112233",
            )

    def test_message_ordering_is_chronological(self):
        conv = Conversation.objects.create(
            business=self.business,
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

    def test_customer_request_request_defaults_to_new(self):
        conv = Conversation.objects.create(
            business=self.business,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )
        req = CustomerRequest.objects.create(
            business=self.business,
            conversation=conv,
            customer_name="Orxan",
            phone="+994551234567",
            service_text="İmplant konsultasiyası",
            preferred_time_text="çərşənbə axşamüstü",
        )
        self.assertEqual(req.status, CustomerRequest.Status.NEW)


# --- Fake Groq client (OpenAI-uyğun tool-use agentini test etmək üçün) ---

import json as _json


class FakeFunctionCall:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = _json.dumps(arguments)


class FakeToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = FakeFunctionCall(name, arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeChoice:
    def __init__(self, message, finish_reason):
        self.message = message
        self.finish_reason = finish_reason


class FakeResponse:
    def __init__(self, message, finish_reason):
        self.choices = [FakeChoice(message, finish_reason)]


class FakeChatCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    """client.chat.completions.create(...) ardıcıl hazır cavablar qaytarır."""

    def __init__(self, responses):
        self.chat = self
        self.completions = FakeChatCompletions(responses)

    @property
    def calls(self):
        return self.completions.calls


def text_response(text):
    return FakeResponse(FakeMessage(content=text), "stop")


def tool_call_response(name, arguments, call_id="call_1"):
    return FakeResponse(
        FakeMessage(tool_calls=[FakeToolCall(call_id, name, arguments)]),
        "tool_calls",
    )


class AgentTests(TestCase):
    def setUp(self):
        self.business = make_business()
        self.conv = Conversation.objects.create(
            business=self.business,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
        )

    def _add_customer_msg(self, text):
        Message.objects.create(
            conversation=self.conv, role=Message.Role.CUSTOMER, text=text
        )

    def test_plain_answer_returned(self):
        self._add_customer_msg("Magistratura hazırlığı neçəyədir?")
        client = FakeClient([text_response("Magistratura hazırlığı 300 AZN-dir.")])
        reply = responder.generate_reply(self.conv, client=client)
        self.assertEqual(reply, "Magistratura hazırlığı 300 AZN-dir.")

    def test_history_maps_roles_and_starts_with_user(self):
        # Bot mesajı əvvəldə olsa da, ilk mesaj user olmalıdır
        Message.objects.create(
            conversation=self.conv, role=Message.Role.BOT, text="Xoş gəlmisiniz!"
        )
        self._add_customer_msg("Salam")
        client = FakeClient([text_response("Salam, necə kömək edə bilərəm?")])
        responder.generate_reply(self.conv, client=client)
        sent = client.calls[0]["messages"]
        self.assertEqual(sent[0]["role"], "system")
        self.assertEqual(sent[1]["role"], "user")
        self.assertEqual(sent[1]["content"], "Salam")

    @patch("assistant.notifications.notify_request")
    def test_customer_request_tool_creates_request_and_notifies(self, mock_notify):
        self._add_customer_msg("Qeydiyyatdan keçmək istəyirəm, Orxan, 0551234567")
        tool_use = tool_call_response(
            "create_customer_request",
            {
                "customer_name": "Orxan",
                "phone": "0551234567",
                "service": "magistratura hazırlığı",
                "preferred_time": "sabah",
            },
            call_id="toolu_1",
        )
        final = text_response("Məlumatlarınızı qeyd etdim, sizinlə əlaqə saxlanılacaq.")
        client = FakeClient([tool_use, final])

        reply = responder.generate_reply(self.conv, client=client)

        req = CustomerRequest.objects.get()
        self.assertEqual(req.customer_name, "Orxan")
        self.assertEqual(req.phone, "0551234567")
        self.assertEqual(req.business, self.business)
        mock_notify.assert_called_once()
        self.assertIn("qeyd etdim", reply)
        # İkinci çağırışda tool_result göndərilib
        self.assertEqual(len(client.calls), 2)

    @patch("assistant.notifications.notify_handoff")
    def test_handoff_tool_pauses_bot_and_notifies(self, mock_notify):
        self._add_customer_msg("Operatorla danışmaq istəyirəm")
        tool_use = tool_call_response(
            "handoff_to_operator",
            {"reason": "Müştəri operator istədi"},
            call_id="toolu_2",
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
                self.chat = self
                self.completions = self

            def create(self, **kwargs):
                raise RuntimeError("API down")

        reply = responder.generate_reply(self.conv, client=BoomClient())
        self.assertEqual(reply, responder.FALLBACK_REPLY)
        mock_notify.assert_called_once()

    def test_empty_history_returns_fallback(self):
        client = FakeClient([])
        reply = responder.generate_reply(self.conv, client=client)
        self.assertEqual(reply, responder.FALLBACK_REPLY)
