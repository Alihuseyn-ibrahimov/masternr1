"""Kanaldan asılı olmayan mesaj göndərmə dispetçeri."""

from assistant.models import Conversation

from . import instagram, whatsapp


def send_reply(conversation: Conversation, text: str) -> dict:
    """Danışığın kanalına uyğun göndərmə funksiyasını çağırır."""
    clinic = conversation.clinic
    if conversation.channel == Conversation.Channel.WHATSAPP:
        return whatsapp.send_text(
            phone_number_id=clinic.whatsapp_phone_number_id,
            to=conversation.external_user_id,
            text=text,
        )
    if conversation.channel == Conversation.Channel.INSTAGRAM:
        return instagram.send_text(
            page_id=clinic.instagram_page_id,
            to=conversation.external_user_id,
            text=text,
        )
    raise ValueError(f"Naməlum kanal: {conversation.channel}")
