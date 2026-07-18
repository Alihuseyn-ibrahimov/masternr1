import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from assistant.models import Conversation, Message
from clinics.models import Clinic

from . import fixtures_payloads as fx
from .parsing import parse_webhook
from .signature import verify_signature

APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"


def sign(body: bytes, secret: str = APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class SignatureTests(TestCase):
    def test_valid_signature_passes(self):
        body = b'{"hello":"world"}'
        self.assertTrue(verify_signature(APP_SECRET, body, sign(body)))

    def test_tampered_body_fails(self):
        header = sign(b'{"hello":"world"}')
        self.assertFalse(verify_signature(APP_SECRET, b'{"hello":"evil"}', header))

    def test_missing_header_fails(self):
        self.assertFalse(verify_signature(APP_SECRET, b"x", None))

    def test_empty_secret_fails(self):
        body = b"x"
        self.assertFalse(verify_signature("", body, sign(body, "")))

    def test_malformed_header_fails(self):
        self.assertFalse(verify_signature(APP_SECRET, b"x", "deadbeef"))


class ParsingTests(TestCase):
    def test_whatsapp_text(self):
        msgs = parse_webhook(fx.whatsapp_text_message())
        self.assertEqual(len(msgs), 1)
        m = msgs[0]
        self.assertEqual(m.channel, Conversation.Channel.WHATSAPP)
        self.assertEqual(m.external_user_id, "994501112233")
        self.assertEqual(m.routing_id, "PHONE_NUMBER_ID")
        self.assertEqual(m.external_message_id, "wamid.TESTID1")
        self.assertTrue(m.is_text)
        self.assertIn("qiymət", m.text)

    def test_whatsapp_status_ignored(self):
        self.assertEqual(parse_webhook(fx.whatsapp_status_update()), [])

    def test_whatsapp_image_is_non_text(self):
        msgs = parse_webhook(fx.whatsapp_image_message())
        self.assertEqual(len(msgs), 1)
        self.assertFalse(msgs[0].is_text)
        self.assertEqual(msgs[0].text, "")

    def test_instagram_text(self):
        msgs = parse_webhook(fx.instagram_text_message())
        self.assertEqual(len(msgs), 1)
        m = msgs[0]
        self.assertEqual(m.channel, Conversation.Channel.INSTAGRAM)
        self.assertEqual(m.external_user_id, "ig-user-123")
        self.assertEqual(m.routing_id, "IG_PAGE_ID")
        self.assertTrue(m.is_text)

    def test_instagram_echo_ignored(self):
        self.assertEqual(parse_webhook(fx.instagram_echo_message()), [])

    def test_unknown_object_ignored(self):
        self.assertEqual(parse_webhook({"object": "page", "entry": []}), [])


@override_settings(
    META_APP_SECRET=APP_SECRET,
    META_VERIFY_TOKEN=VERIFY_TOKEN,
    CELERY_TASK_ALWAYS_EAGER=True,
)
class WebhookViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("meta_webhook")
        self.clinic = Clinic.objects.create(
            name="Dent Klinika",
            slug="dent",
            whatsapp_phone_number_id="PHONE_NUMBER_ID",
            instagram_page_id="IG_PAGE_ID",
        )

    # --- GET verification ---
    def test_get_verification_success(self):
        resp = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": VERIFY_TOKEN,
                "hub.challenge": "12345",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.decode(), "12345")

    def test_get_verification_wrong_token(self):
        resp = self.client.get(
            self.url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong",
                "hub.challenge": "12345",
            },
        )
        self.assertEqual(resp.status_code, 403)

    # --- POST events ---
    def _post(self, payload):
        body = json.dumps(payload).encode()
        return self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=sign(body),
        )

    def test_post_invalid_signature_rejected(self):
        body = json.dumps(fx.whatsapp_text_message()).encode()
        resp = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=bad",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(Message.objects.count(), 0)

    @patch("channels.tasks.generate_reply", return_value="Salam, necə kömək edim?")
    @patch("channels.tasks.send_reply")
    def test_post_whatsapp_creates_conversation_and_replies(self, mock_send, mock_reply):
        resp = self._post(fx.whatsapp_text_message())
        self.assertEqual(resp.status_code, 200)

        conv = Conversation.objects.get()
        self.assertEqual(conv.clinic, self.clinic)
        self.assertEqual(conv.channel, Conversation.Channel.WHATSAPP)
        roles = list(conv.messages.values_list("role", flat=True))
        self.assertEqual(roles, [Message.Role.CUSTOMER, Message.Role.BOT])
        mock_send.assert_called_once()

    @patch("channels.tasks.generate_reply", return_value="cavab")
    @patch("channels.tasks.send_reply")
    def test_duplicate_message_id_deduped(self, mock_send, mock_reply):
        self._post(fx.whatsapp_text_message(message_id="wamid.DUP"))
        self._post(fx.whatsapp_text_message(message_id="wamid.DUP"))
        conv = Conversation.objects.get()
        # İkinci dəfə eyni mesaj ID → yalnız bir customer + bir bot mesajı
        self.assertEqual(conv.messages.filter(role=Message.Role.CUSTOMER).count(), 1)
        self.assertEqual(mock_send.call_count, 1)

    @patch("channels.tasks.send_reply")
    def test_bot_paused_conversation_no_reply(self, mock_send):
        Conversation.objects.create(
            clinic=self.clinic,
            channel=Conversation.Channel.WHATSAPP,
            external_user_id="994501112233",
            bot_paused=True,
        )
        self._post(fx.whatsapp_text_message())
        conv = Conversation.objects.get()
        self.assertEqual(conv.messages.filter(role=Message.Role.BOT).count(), 0)
        mock_send.assert_not_called()

    @patch("channels.tasks.send_reply")
    def test_non_text_gets_fallback_reply(self, mock_send):
        self._post(fx.whatsapp_image_message())
        conv = Conversation.objects.get()
        bot_msg = conv.messages.get(role=Message.Role.BOT)
        self.assertIn("mətn", bot_msg.text.lower())
        mock_send.assert_called_once()

    @patch("channels.tasks.send_reply")
    def test_unknown_routing_id_skipped(self, mock_send):
        self._post(fx.whatsapp_text_message(phone_number_id="UNKNOWN"))
        self.assertEqual(Conversation.objects.count(), 0)
        mock_send.assert_not_called()

    @patch("channels.tasks.generate_reply", return_value="cavab")
    @patch("channels.tasks.send_reply")
    def test_instagram_message_routed(self, mock_send, mock_reply):
        self._post(fx.instagram_text_message())
        conv = Conversation.objects.get()
        self.assertEqual(conv.channel, Conversation.Channel.INSTAGRAM)
        mock_send.assert_called_once()
