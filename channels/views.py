"""Webhook endpoint-ləri: Meta (WhatsApp+Instagram) və ManyChat relay."""

import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from assistant.models import Conversation, Message
from assistant.responder import generate_reply
from businesses.models import Business

from .signature import verify_signature
from .tasks import NON_TEXT_FALLBACK, process_incoming_payload

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def meta_webhook(request):
    if request.method == "GET":
        return _handle_verification(request)
    return _handle_event(request)


def _handle_verification(request):
    """Meta webhook qeydiyyatı zamanı hub.challenge yoxlaması."""
    mode = request.GET.get("hub.mode")
    token = request.GET.get("hub.verify_token")
    challenge = request.GET.get("hub.challenge", "")
    if mode == "subscribe" and token and token == settings.META_VERIFY_TOKEN:
        return HttpResponse(challenge)
    return HttpResponseForbidden("Verification failed")


def _handle_event(request):
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(settings.META_APP_SECRET, request.body, signature):
        return HttpResponseForbidden("Invalid signature")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    # Dərhal Celery-yə ötür, Meta-ya 200 qaytar (20 saniyə limiti)
    process_incoming_payload.delay(payload)
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_http_methods(["POST"])
def manychat_webhook(request):
    """ManyChat "External Request" addımından gələn relay sorğusu.

    Meta App Review (Advanced Access) keçilənə qədər Instagram DM axını
    ManyChat üzərindən gəlir: ManyChat mesajı bu endpoint-ə POST edir,
    cavab mətnini SİNXRON qaytarırıq, göndərməni ManyChat özü edir.
    Marşrutlaşdırma X-Relay-Token header-i ilədir (Business.manychat_token).
    """
    token = request.headers.get("X-Relay-Token", "")
    business = (
        Business.objects.filter(is_active=True, manychat_token=token).first()
        if token
        else None
    )
    if business is None:
        return HttpResponseForbidden("Invalid relay token")

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return HttpResponse(status=400)

    subscriber_id = str(payload.get("subscriber_id") or "").strip()
    if not subscriber_id:
        return HttpResponse(status=400)
    text = str(payload.get("text") or "").strip()

    conversation, _ = Conversation.objects.get_or_create(
        business=business,
        channel=Conversation.Channel.INSTAGRAM,
        external_user_id=subscriber_id,
    )

    if text:
        Message.objects.create(
            conversation=conversation, role=Message.Role.CUSTOMER, text=text
        )

    # Operator ələ alıbsa bot susur — boş cavabda ManyChat heç nə göndərmir
    if conversation.bot_paused:
        return JsonResponse({"reply": ""})

    reply = generate_reply(conversation) if text else NON_TEXT_FALLBACK

    Message.objects.create(
        conversation=conversation, role=Message.Role.BOT, text=reply
    )
    return JsonResponse({"reply": reply})
