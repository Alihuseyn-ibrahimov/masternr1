"""Meta webhook payload nümunələri — testlərdə istifadə üçün.

WhatsApp Cloud API və Instagram Messaging real payload strukturlarına uyğundur.
"""


def whatsapp_text_message(
    phone_number_id="PHONE_NUMBER_ID",
    from_="994501112233",
    text="Salam, qiymətləri öyrənmək istəyirəm",
    message_id="wamid.TESTID1",
    name="Orxan",
):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "994000000000",
                                "phone_number_id": phone_number_id,
                            },
                            "contacts": [
                                {"profile": {"name": name}, "wa_id": from_}
                            ],
                            "messages": [
                                {
                                    "from": from_,
                                    "id": message_id,
                                    "timestamp": "1690000000",
                                    "type": "text",
                                    "text": {"body": text},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def whatsapp_status_update(phone_number_id="PHONE_NUMBER_ID"):
    """Çatdırılma/oxunma bildirişi — mesaj DEYİL, ignore olunmalıdır."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "994000000000",
                                "phone_number_id": phone_number_id,
                            },
                            "statuses": [
                                {
                                    "id": "wamid.TESTID1",
                                    "status": "delivered",
                                    "timestamp": "1690000001",
                                    "recipient_id": "994501112233",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def whatsapp_image_message(
    phone_number_id="PHONE_NUMBER_ID",
    from_="994501112233",
    message_id="wamid.IMG1",
):
    """Mətn olmayan (şəkil) mesaj — MVP-də fallback cavab verilir."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "994000000000",
                                "phone_number_id": phone_number_id,
                            },
                            "contacts": [
                                {"profile": {"name": "Orxan"}, "wa_id": from_}
                            ],
                            "messages": [
                                {
                                    "from": from_,
                                    "id": message_id,
                                    "timestamp": "1690000000",
                                    "type": "image",
                                    "image": {"id": "MEDIA_ID", "mime_type": "image/jpeg"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def instagram_text_message(
    page_id="IG_PAGE_ID",
    sender_id="ig-user-123",
    text="Salam, iş saatlarınız necədir?",
    message_id="ig-mid-1",
):
    return {
        "object": "instagram",
        "entry": [
            {
                "id": page_id,
                "time": 1690000000,
                "messaging": [
                    {
                        "sender": {"id": sender_id},
                        "recipient": {"id": page_id},
                        "timestamp": 1690000000,
                        "message": {"mid": message_id, "text": text},
                    }
                ],
            }
        ],
    }


def instagram_echo_message(page_id="IG_PAGE_ID", sender_id="ig-user-123"):
    """Bizim öz göndərdiyimiz mesajın echo-su — ignore olunmalıdır."""
    return {
        "object": "instagram",
        "entry": [
            {
                "id": page_id,
                "time": 1690000000,
                "messaging": [
                    {
                        "sender": {"id": page_id},
                        "recipient": {"id": sender_id},
                        "timestamp": 1690000000,
                        "message": {
                            "mid": "ig-echo-1",
                            "text": "Bizim cavab",
                            "is_echo": True,
                        },
                    }
                ],
            }
        ],
    }
