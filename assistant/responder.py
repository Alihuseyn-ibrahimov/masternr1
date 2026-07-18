"""Danışığa cavab mətninin generasiyası.

FAZA 2: sadə placeholder cavab. FAZA 3-də bu funksiyanın daxili məntiqi
Claude tool-use agenti ilə əvəzlənəcək (answer / create_appointment_request /
handoff_to_operator). Task interfeysi (`generate_reply(conversation) -> str`)
sabit qalır ki, webhook axını dəyişməsin.
"""

from assistant.models import Conversation

PLACEHOLDER_REPLY = (
    "Salam! Mesajınız üçün təşəkkür edirik. Suallarınızı qeyd etdik, "
    "tezliklə sizə kömək edəcəyik."
)


def generate_reply(conversation: Conversation) -> str:
    return PLACEHOLDER_REPLY
