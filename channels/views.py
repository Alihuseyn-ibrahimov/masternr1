"""Meta webhook endpoint-i (WhatsApp + Instagram üçün ümumi)."""

import json
import logging

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .signature import verify_signature
from .tasks import process_incoming_payload

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
