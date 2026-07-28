from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from assistant.models import CustomerRequest, Conversation, Message
from businesses.models import Business

from .models import BusinessMembership


def make_conversation(business, uid="994501112233"):
    return Conversation.objects.create(
        business=business,
        channel=Conversation.Channel.WHATSAPP,
        external_user_id=uid,
    )


class InboxAuthTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(name="A Mərkəzi", slug="a")
        self.conv = make_conversation(self.business)

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
        self.business_a = Business.objects.create(name="A", slug="a")
        self.business_b = Business.objects.create(name="B", slug="b")
        self.conv_a = make_conversation(self.business_a, "a-user")
        self.conv_b = make_conversation(self.business_b, "b-user")

        self.user = User.objects.create_user("operator_a", password="pw12345")
        BusinessMembership.objects.create(user=self.user, business=self.business_a)
        self.client.force_login(self.user)

    def test_list_shows_only_own_business(self):
        resp = self.client.get(reverse("inbox:conversation_list"))
        convs = list(resp.context["conversations"])
        self.assertIn(self.conv_a, convs)
        self.assertNotIn(self.conv_b, convs)

    def test_cannot_open_other_business_conversation(self):
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
        self.business = Business.objects.create(name="A", slug="a")
        self.conv = make_conversation(self.business)
        self.user = User.objects.create_user("op", password="pw12345")
        BusinessMembership.objects.create(user=self.user, business=self.business)
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
    def test_cannot_reply_to_other_business(self, mock_send):
        other = Business.objects.create(name="B", slug="b")
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
        self.business = Business.objects.create(name="A", slug="a")
        self.other = Business.objects.create(name="B", slug="b")
        self.user = User.objects.create_user("op", password="pw12345")
        BusinessMembership.objects.create(user=self.user, business=self.business)
        self.client.force_login(self.user)
        CustomerRequest.objects.create(
            business=self.business, customer_name="Mine", phone="1"
        )
        CustomerRequest.objects.create(
            business=self.other, customer_name="Theirs", phone="2"
        )

    def test_only_own_customer_requests_listed(self):
        resp = self.client.get(reverse("inbox:request_list"))
        names = [a.customer_name for a in resp.context["customer_requests"]]
        self.assertEqual(names, ["Mine"])
