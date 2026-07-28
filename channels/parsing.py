"""Meta webhook payload-larının normallaşdırılması.

WhatsApp Cloud API və Instagram Messaging fərqli payload strukturlarına malikdir;
bu modul hər ikisini vahid `IncomingMessage` formasına gətirir.
"""

from dataclasses import dataclass

from assistant.models import Conversation


@dataclass
class IncomingMessage:
    channel: str  # Conversation.Channel dəyəri
    external_user_id: str  # göndərən müştəri (WA nömrəsi / IG user id)
    routing_id: str  # müəssisəni tapmaq üçün (WA phone_number_id / IG page id)
    external_message_id: str
    text: str
    is_text: bool  # False → mətn olmayan (şəkil, audio və s.)


def parse_webhook(payload: dict) -> list[IncomingMessage]:
    """Payload obyektinə görə düzgün parser-i seçir. Statuslar/echo-lar atılır."""
    obj = payload.get("object")
    if obj == "whatsapp_business_account":
        return _parse_whatsapp(payload)
    if obj == "instagram":
        return _parse_instagram(payload)
    return []


def _parse_whatsapp(payload: dict) -> list[IncomingMessage]:
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            # statuses → çatdırılma/oxunma bildirişləri, ignore
            if "messages" not in value:
                continue
            phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
            for msg in value["messages"]:
                msg_type = msg.get("type")
                is_text = msg_type == "text"
                text = msg.get("text", {}).get("body", "") if is_text else ""
                out.append(
                    IncomingMessage(
                        channel=Conversation.Channel.WHATSAPP,
                        external_user_id=msg.get("from", ""),
                        routing_id=phone_number_id,
                        external_message_id=msg.get("id", ""),
                        text=text,
                        is_text=is_text,
                    )
                )
    return out


def _parse_instagram(payload: dict) -> list[IncomingMessage]:
    out = []
    for entry in payload.get("entry", []):
        page_id = entry.get("id", "")
        for event in entry.get("messaging", []):
            message = event.get("message")
            if not message:
                continue
            # is_echo → bizim öz göndərdiyimiz mesaj, ignore
            if message.get("is_echo"):
                continue
            text = message.get("text", "")
            is_text = bool(text)
            out.append(
                IncomingMessage(
                    channel=Conversation.Channel.INSTAGRAM,
                    external_user_id=event.get("sender", {}).get("id", ""),
                    routing_id=page_id,
                    external_message_id=message.get("mid", ""),
                    text=text,
                    is_text=is_text,
                )
            )
    return out
