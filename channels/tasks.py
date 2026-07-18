"""Gələn webhook payload-larının asinxron emalı (Celery)."""

import logging

from celery import shared_task

from assistant.models import Conversation, Message
from assistant.responder import generate_reply
from clinics.models import Clinic

from .parsing import IncomingMessage, parse_webhook
from .senders import send_reply

logger = logging.getLogger(__name__)

NON_TEXT_FALLBACK = (
    "Hələlik yalnız mətn mesajlarını emal edə bilirik. "
    "Zəhmət olmasa sualınızı mətn şəklində yazın."
)


@shared_task
def process_incoming_payload(payload: dict) -> None:
    for msg in parse_webhook(payload):
        try:
            _process_one(msg)
        except Exception:  # noqa: BLE001 — bir mesajın xətası digərlərini dayandırmasın
            logger.exception("Mesaj emalı uğursuz oldu: %s", msg.external_message_id)


def _route_clinic(msg: IncomingMessage) -> Clinic | None:
    if msg.channel == Conversation.Channel.WHATSAPP:
        lookup = {"whatsapp_phone_number_id": msg.routing_id}
    elif msg.channel == Conversation.Channel.INSTAGRAM:
        lookup = {"instagram_page_id": msg.routing_id}
    else:
        return None
    return Clinic.objects.filter(is_active=True, **lookup).first()


def _process_one(msg: IncomingMessage) -> None:
    clinic = _route_clinic(msg)
    if clinic is None:
        logger.warning(
            "Marşrutlaşdırıla bilməyən mesaj: kanal=%s routing_id=%s",
            msg.channel,
            msg.routing_id,
        )
        return

    conversation, _ = Conversation.objects.get_or_create(
        clinic=clinic,
        channel=msg.channel,
        external_user_id=msg.external_user_id,
    )

    # Dedup — Meta eyni webhook-u təkrar göndərə bilər
    if msg.external_message_id and conversation.messages.filter(
        external_message_id=msg.external_message_id
    ).exists():
        return

    Message.objects.create(
        conversation=conversation,
        role=Message.Role.CUSTOMER,
        text=msg.text,
        external_message_id=msg.external_message_id,
    )

    # Operator danışığı ələ alıbsa, bot susur
    if conversation.bot_paused:
        return

    reply = NON_TEXT_FALLBACK if not msg.is_text else generate_reply(conversation)

    Message.objects.create(
        conversation=conversation,
        role=Message.Role.BOT,
        text=reply,
    )
    send_reply(conversation, reply)
