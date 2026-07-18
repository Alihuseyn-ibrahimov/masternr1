"""Instagram Messaging (Graph API) vasitəsilə mesaj göndərmə."""

import requests
from django.conf import settings


def send_text(page_id: str, to: str, text: str) -> dict:
    """Instagram user-ə mətn mesajı göndərir.

    page_id: klinikanın bağlı Instagram/Facebook səhifəsinin ID-si.
    to: müştərinin Instagram-scoped user ID-si.
    """
    url = (
        f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"
        f"/{page_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {
        "recipient": {"id": to},
        "message": {"text": text},
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()
