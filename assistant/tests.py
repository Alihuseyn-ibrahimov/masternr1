from django.test import TestCase

from clinics.models import Clinic, Doctor, FAQItem, Service

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
