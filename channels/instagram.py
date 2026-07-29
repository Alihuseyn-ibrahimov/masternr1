"""Instagram Messaging (Graph API) vasitəsilə mesaj göndərmə."""

import requests
from django.conf import settings


def send_text(page_id: str, to: str, text: str, access_token: str) -> dict:
    """Instagram user-ə mətn mesajı göndərir.

    page_id: müəssisənin bağlı Instagram/Facebook səhifəsinin ID-si.
    to: müştərinin Instagram-scoped user ID-si.
    access_token: bu müəssisəyə aid Graph API token-i.
    """
    url = (
        f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"
        f"/{page_id}/messages"
    )
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "recipient": {"id": to},
        "message": {"text": text},
    }
    resp = requests.post(url, headers=headers, json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()
