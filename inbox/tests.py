from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from assistant.models import AppointmentRequest, Conversation, Message
from clinics.models import Clinic

from .models import ClinicMembership


def make_conversation(clinic, uid="994501112233"):
    return Conversation.objects.create(
        clinic=clinic,
        channel=Conversation.Channel.WHATSAPP,
        external_user_id=uid,
    )


class InboxAuthTests(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(name="A Klinika", slug="a")
        self.conv = make_conversation(self.clinic)

    def test_list_requires_login(self):
        resp = self.client.get(reverse("inbox:conversation_list"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_detail_requires_login(self):
        resp = self.client.get(
            reverse("inbox:conversation_detail", args=[self.conv.pk])
        )
        self.assertEqual(resp.status_code, 302)


class InboxTenantIsolationTests(TestCase):
    def setUp(self):
        self.clinic_a = Clinic.objects.create(name="A", slug="a")
        self.clinic_b = Clinic.objects.create(name="B", slug="b")
        self.conv_a = make_conversation(self.clinic_a, "a-user")
        self.conv_b = make_conversation(self.clinic_b, "b-user")

        self.user = User.objects.create_user("operator_a", password="pw12345")
        ClinicMembership.objects.create(user=self.user, clinic=self.clinic_a)
        self.client.force_login(self.user)

    def test_list_shows_only_own_clinic(self):
        resp = self.client.get(reverse("inbox:conversation_list"))
        convs = list(resp.context["conversations"])
        self.assertIn(self.conv_a, convs)
        self.assertNotIn(self.conv_b, convs)

    def test_cannot_open_other_clinic_conversation(self):
        resp = self.client.get(
            reverse("inbox:conversation_detail", args=[self.conv_b.pk])
        )
        self.assertEqual(resp.status_code, 404)

    def test_superuser_sees_all(self):
        admin = User.objects.create_superuser("root", "a@b.c", "pw12345")
        self.client.force_login(admin)
        resp = self.client.get(reverse("inbox:conversation_list"))
        convs = list(resp.context["conversations"])
        self.assertIn(self.conv_a, convs)
        self.assertIn(self.conv_b, convs)


class OperatorReplyTests(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(name="A", slug="a")
        self.conv = make_conversation(self.clinic)
        self.user = User.objects.create_user("op", password="pw12345")
        ClinicMembership.objects.create(user=self.user, clinic=self.clinic)
        self.client.force_login(self.user)

    @patch("inbox.views.send_reply")
    def test_reply_creates_message_pauses_bot_and_sends(self, mock_send):
        url = reverse("inbox:send_reply", args=[self.conv.pk])
        resp = self.client.post(url, {"text": "Salam, mən operatoram."})
        self.assertEqual(resp.status_code, 302)

        msg = self.conv.messages.get()
        self.assertEqual(msg.role, Message.Role.OPERATOR)
        self.assertEqual(msg.text, "Salam, mən operatoram.")

        self.conv.refresh_from_db()
        self.assertTrue(self.conv.bot_paused)
        mock_send.assert_called_once()

    @patch("inbox.views.send_reply")
    def test_empty_reply_ignored(self, mock_send):
        url = reverse("inbox:send_reply", args=[self.conv.pk])
        self.client.post(url, {"text": "   "})
        self.assertEqual(self.conv.messages.count(), 0)
        mock_send.assert_not_called()

    @patch("inbox.views.send_reply")
    def test_cannot_reply_to_other_clinic(self, mock_send):
        other = Clinic.objects.create(name="B", slug="b")
        other_conv = make_conversation(other, "x")
        url = reverse("inbox:send_reply", args=[other_conv.pk])
        resp = self.client.post(url, {"text": "hi"})
        self.assertEqual(resp.status_code, 404)
        mock_send.assert_not_called()

    def test_toggle_bot(self):
        url = reverse("inbox:toggle_bot", args=[self.conv.pk])
        self.client.post(url)
        self.conv.refresh_from_db()
        self.assertTrue(self.conv.bot_paused)
        self.client.post(url)
        self.conv.refresh_from_db()
        self.assertFalse(self.conv.bot_paused)


class AppointmentListTests(TestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(name="A", slug="a")
        self.other = Clinic.objects.create(name="B", slug="b")
        self.user = User.objects.create_user("op", password="pw12345")
        ClinicMembership.objects.create(user=self.user, clinic=self.clinic)
        self.client.force_login(self.user)
        AppointmentRequest.objects.create(
            clinic=self.clinic, customer_name="Mine", phone="1"
        )
        AppointmentRequest.objects.create(
            clinic=self.other, customer_name="Theirs", phone="2"
        )

    def test_only_own_appointments_listed(self):
        resp = self.client.get(reverse("inbox:appointment_list"))
        names = [a.customer_name for a in resp.context["appointments"]]
        self.assertEqual(names, ["Mine"])
