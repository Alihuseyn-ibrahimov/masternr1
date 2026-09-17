"""Danışığa cavab mətninin generasiyası — LangChain + ChatGroq tool-use agenti.

System prompt `ChatPromptTemplate` ilə qurulur, alətlər `bind_tools` ilə
modelə bağlanır, tool loop əl ilə idarə olunur (max 4 dövr).
Agent üç davranışa malikdir:
- adi mətn cavabı — müəssisənin bilik bazasından cavab
- `create_customer_request` — randevu sorğusunu qeyd et + Telegram bildirişi
- `handoff_to_operator` — botu pauza et + operatora Telegram bildirişi

Müəssisəyə xas qadağa qaydası (guardrail) system promptdadır (bax: `prompt.py`).
Task interfeysi sabitdir: `generate_reply(conversation) -> str`.
"""

import logging

from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from . import notifications
from .models import Conversation, CustomerRequest, Message
from .prompt import build_system_prompt

logger = logging.getLogger(__name__)

MAX_HISTORY = 20
MAX_TOOL_ITERATIONS = 4

FALLBACK_REPLY = (
    "Bağışlayın, texniki səbəbdən cavab verə bilmədim. "
    "Sorğunuzu operatora ötürdüm, tezliklə sizinlə əlaqə saxlanılacaq."
)

REQUEST_ACK = "Məlumatlarınızı qeyd etdim, tezliklə sizinlə əlaqə saxlanılacaq."
HANDOFF_ACK = "Sizi bir operatorumuza yönləndirirəm, bir az gözləyin."

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_customer_request",
            "description": (
                "Müştəri randevu/qeydiyyat istədikdə və lazımi məlumatları verdikdə çağır. "
                "Ən azı ad və telefon nömrəsi toplanmalıdır."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string", "description": "Müştərinin adı"},
                    "phone": {"type": "string", "description": "Əlaqə nömrəsi"},
                    "service": {
                        "type": "string",
                        "description": "İstənilən xidmət/proqram (varsa)",
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


# System prompt dəyişən kimi ötürülür — KB mətnindəki `{}` simvolları
# template placeholder-i kimi şərh olunmasın deyə.
PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_prompt}"),
        MessagesPlaceholder("messages"),
    ]
)


def _get_client():
    from langchain_groq import ChatGroq

    model = ChatGroq(
        model=settings.ASSISTANT_MODEL,
        temperature=0.3,
        max_tokens=settings.ASSISTANT_MAX_TOKENS,
        api_key=settings.GROQ_API_KEY,
    )
    return model.bind_tools(TOOLS)


def _message_text(message) -> str:
    """AIMessage məzmununu mətnə çevirir (blok siyahısı da ola bilər)."""
    content = message.content
    if isinstance(content, list):
        parts = [
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        ]
        content = "".join(parts)
    return (content or "").strip()


def _history_to_messages(conversation: Conversation) -> list:
    """Danışıq tarixçəsini LangChain mesaj obyektlərinə çevirir."""
    recent = list(conversation.messages.all())[-MAX_HISTORY:]
    messages = []
    for m in recent:
        if not m.text:
            continue
        if m.role == Message.Role.CUSTOMER:
            messages.append(HumanMessage(content=m.text))
        else:
            messages.append(AIMessage(content=m.text))
    # İlk mesaj müştəri mesajı olmalıdır
    while messages and not isinstance(messages[0], HumanMessage):
        messages.pop(0)
    return messages


def _handle_tool(conversation: Conversation, name: str, tool_input: dict) -> str:
    if name == "create_customer_request":
        customer_request = CustomerRequest.objects.create(
            business=conversation.business,
            conversation=conversation,
            customer_name=tool_input.get("customer_name", ""),
            phone=tool_input.get("phone", ""),
            service_text=tool_input.get("service", ""),
            preferred_time_text=tool_input.get("preferred_time", ""),
        )
        notifications.notify_request(customer_request)
        return REQUEST_ACK

    if name == "handoff_to_operator":
        conversation.bot_paused = True
        conversation.save(update_fields=["bot_paused", "updated_at"])
        notifications.notify_handoff(conversation, tool_input.get("reason", ""))
        return HANDOFF_ACK

    logger.warning("Naməlum alət çağırıldı: %s", name)
    return "OK"


def _run_agent(client, conversation, system, messages) -> str:
    full_messages = PROMPT.format_messages(system_prompt=system, messages=messages)
    response = None

    for _ in range(MAX_TOOL_ITERATIONS):
        response = client.invoke(full_messages)

        if not getattr(response, "tool_calls", None):
            return _message_text(response)

        full_messages.append(response)
        for call in response.tool_calls:
            result = _handle_tool(conversation, call["name"], call.get("args") or {})
            full_messages.append(
                ToolMessage(content=result, tool_call_id=call.get("id") or "")
            )

    if response is not None:
        return _message_text(response)
    return ""


def generate_reply(conversation: Conversation, client=None) -> str:
    client = client or _get_client()
    system = build_system_prompt(conversation.business)
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
