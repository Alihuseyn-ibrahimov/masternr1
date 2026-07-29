"""WhatsApp Cloud API vasitəsilə mesaj göndərmə."""

import requests
from django.conf import settings


def send_text(phone_number_id: str, to: str, text: str, access_token: str) -> dict:
    """WhatsApp Cloud API ilə mətn mesajı göndərir.

    phone_number_id: müəssisənin WA nömrəsinin ID-si (göndərən).
    to: müştərinin WA nömrəsi.
    access_token: bu müəssisəyə aid Graph API token-i.
    """
    url = (
        f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"
        f"/{phone_number_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()
