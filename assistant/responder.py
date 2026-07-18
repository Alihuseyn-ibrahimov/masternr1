"""Danışığa cavab mətninin generasiyası — Claude tool-use agenti.

Agent üç davranışa malikdir:
- adi mətn cavabı ("answer") — klinikanın bilik bazasından cavab
- `create_appointment_request` — randevu sorğusunu qeyd et + Telegram bildirişi
- `handoff_to_operator` — botu pauza et + operatora Telegram bildirişi

Tibbi məsləhət qadağası system promptdadır (bax: `prompt.py`).
Task interfeysi sabitdir: `generate_reply(conversation) -> str`.
"""

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
        "name": "create_appointment_request",
        "description": (
            "Müştəri randevu istədikdə və lazımi məlumatları verdikdə çağır. "
            "Ən azı ad və telefon nömrəsi toplanmalıdır."
        ),
        "input_schema": {
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
    {
        "name": "handoff_to_operator",
        "description": (
            "Müştəri insan operatorla danışmaq istədikdə, sual həssas/çətin olduqda "
            "və ya narazılıq bildirdikdə çağır."
        ),
        "input_schema": {
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
]


def _get_client():
    import anthropic

    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _history_to_messages(conversation: Conversation) -> list[dict]:
    """Danışıq tarixçəsini Anthropic mesaj formatına çevirir."""
    recent = list(conversation.messages.all())[-MAX_HISTORY:]
    messages = []
    for m in recent:
        if not m.text:
            continue
        role = "user" if m.role == Message.Role.CUSTOMER else "assistant"
        messages.append({"role": role, "content": m.text})
    # API ilk mesajın "user" olmasını tələb edir
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return messages


def _text_of(response) -> str:
    parts = [b.text for b in response.content if b.type == "text"]
    return "\n".join(p for p in parts if p).strip()


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
    response = None
    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.messages.create(
            model=settings.ASSISTANT_MODEL,
            max_tokens=settings.ASSISTANT_MAX_TOKENS,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _handle_tool(conversation, block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})

    return _text_of(response) if response else ""


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
