"""Klinika personalına Telegram bildirişləri (randevu sorğusu, operator handoff)."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _send(chat_id: str, text: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        logger.info("Telegram konfiqurasiya olunmayıb, bildiriş atlanır: %s", text)
        return
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except requests.RequestException:
        logger.exception("Telegram bildirişi göndərilə bilmədi")


def notify_appointment(appointment) -> None:
    clinic = appointment.clinic
    text = (
        "🗓 <b>Yeni randevu sorğusu</b>\n"
        f"Klinika: {clinic.name}\n"
        f"Ad: {appointment.customer_name}\n"
        f"Telefon: {appointment.phone}\n"
        f"Xidmət: {appointment.service_text or '—'}\n"
        f"İstənilən vaxt: {appointment.preferred_time_text or '—'}"
    )
    _send(clinic.telegram_chat_id, text)


def notify_handoff(conversation, reason: str) -> None:
    clinic = conversation.clinic
    text = (
        "🙋 <b>Operatora ötürüldü</b>\n"
        f"Klinika: {clinic.name}\n"
        f"Kanal: {conversation.get_channel_display()}\n"
        f"Müştəri: {conversation.external_user_id}\n"
        f"Səbəb: {reason}"
    )
    _send(clinic.telegram_chat_id, text)
