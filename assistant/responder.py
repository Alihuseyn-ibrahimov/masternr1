"""Danışığa cavab mətninin generasiyası — Groq (Llama) tool-use agenti.

Groq API OpenAI-uyğun formatdadır (chat.completions.create + tools).
Agent üç davranışa malikdir:
- adi mətn cavabı — klinikanın bilik bazasından cavab
- `create_appointment_request` — randevu sorğusunu qeyd et + Telegram bildirişi
- `handoff_to_operator` — botu pauza et + operatora Telegram bildirişi

Tibbi məsləhət qadağası system promptdadır (bax: `prompt.py`).
Task interfeysi sabitdir: `generate_reply(conversation) -> str`.
"""

import json
import logging

from django.conf import settings

from . import notifications
from .models import AppointmentRequest, Conversation, Message
from .prompt import build_system_prompt

logger = logging.getLogger(__name__)

MAX_HISTORY = 20
MAX_TOOL_ITERATIONS = 4

FALLBACK_REPLY = (
    "Bağışlayın, texniki səbəbdən cavab verə bilmədim. "
    "Sorğunuzu operatora ötürdüm, tezliklə sizinlə əlaqə saxlanılacaq."
)

APPOINTMENT_ACK = "Məlumatlarınızı qeyd etdim, randevunuz üçün sizinlə əlaqə saxlanılacaq."
HANDOFF_ACK = "Sizi bir operatorumuza yönləndirirəm, bir az gözləyin."

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_appointment_request",
            "description": (
                "Müştəri randevu istədikdə və lazımi məlumatları verdikdə çağır. "
                "Ən azı ad və telefon nömrəsi toplanmalıdır."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Müştərinin adı"},
                    "phone": {"type": "string", "description": "Əlaqə nömrəsi"},
                    "service": {
                        "type": "string",
                        "description": "İstənilən xidmət (varsa)",
                    },
                    "preferred_time": {
                        "type": "string",
                        "description": "İstənilən vaxt, sərbəst mətn (varsa)",
                    },
                },
                "required": ["customer_name", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_operator",
            "description": (
                "Müştəri insan operatorla danışmaq istədikdə, sual həssas/çətin olduqda "
                "və ya narazılıq bildirdikdə çağır."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Operatora ötürmə səbəbi (qısa)",
                    },
                },
                "required": ["reason"],
            },
        },
    },
]


def _get_client():
    import groq

    return groq.Groq(api_key=settings.GROQ_API_KEY)


def _history_to_messages(conversation: Conversation) -> list[dict]:
    """Danışıq tarixçəsini OpenAI-uyğun mesaj formatına çevirir."""
    recent = list(conversation.messages.all())[-MAX_HISTORY:]
    messages = []
    for m in recent:
        if not m.text:
            continue
        role = "user" if m.role == Message.Role.CUSTOMER else "assistant"
        messages.append({"role": role, "content": m.text})
    # İlk mesaj "user" olmalıdır
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


def _handle_tool(conversation: Conversation, name: str, tool_input: dict) -> str:
    if name == "create_appointment_request":
        appt = AppointmentRequest.objects.create(
            clinic=conversation.clinic,
            conversation=conversation,
            customer_name=tool_input.get("customer_name", ""),
            phone=tool_input.get("phone", ""),
            service_text=tool_input.get("service", ""),
            preferred_time_text=tool_input.get("preferred_time", ""),
        )
        notifications.notify_appointment(appt)
        return APPOINTMENT_ACK

    if name == "handoff_to_operator":
        conversation.bot_paused = True
        conversation.save(update_fields=["bot_paused", "updated_at"])
        notifications.notify_handoff(conversation, tool_input.get("reason", ""))
        return HANDOFF_ACK

    logger.warning("Naməlum alət çağırıldı: %s", name)
    return "OK"


def _run_agent(client, conversation, system, messages) -> str:
    full_messages = [{"role": "system", "content": system}, *messages]
    response = None

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.chat.completions.create(
            model=settings.ASSISTANT_MODEL,
            max_tokens=settings.ASSISTANT_MAX_TOKENS,
            messages=full_messages,
            tools=TOOLS,
        )
        choice = response.choices[0]
        message = choice.message

        if choice.finish_reason != "tool_calls" or not message.tool_calls:
            return (message.content or "").strip()

        full_messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
        )
        for call in message.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            result = _handle_tool(conversation, call.function.name, args)
            full_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": result,
                }
            )

    if response is not None:
        return (response.choices[0].message.content or "").strip()
    return ""


def generate_reply(conversation: Conversation, client=None) -> str:
    client = client or _get_client()
    system = build_system_prompt(conversation.clinic)
    messages = _history_to_messages(conversation)
    if not messages:
        return FALLBACK_REPLY
    try:
        reply = _run_agent(client, conversation, system, messages)
        return reply or FALLBACK_REPLY
    except Exception:  # noqa: BLE001 — LLM/şəbəkə xətası → operatora ötür
        logger.exception("Agent cavabı uğursuz oldu")
        notifications.notify_handoff(conversation, "Sistem xətası (LLM)")
        return FALLBACK_REPLY
