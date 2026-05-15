import json

from jinja2 import Environment, PackageLoader, StrictUndefined

from tgm.core.types import FeedbackSample, Message, PerChatDigestPart

_PER_CHAT_SYSTEM_PROMPT = "Ты — ассистент, который делает краткие сводки чатов.\nВозвращай только валидный JSON."

_GLOBAL_SYSTEM_PROMPT = (
    "Ты — ассистент, который собирает общий обзор по нескольким чатам.\nВозвращай только валидный JSON."
)

_CRITERIA_RECALC_SYSTEM_PROMPT = (
    "Ты — ассистент, обновляющий критерии важности сообщений на основе примеров от пользователя.\n"
    "Возвращай только валидный JSON."
)


def render_message(message: Message) -> str:
    sender = message.sender_name or "unknown"
    text = message.text if message.text is not None else "<no text>"
    return f"[message_id={message.message_id}] {sender} ({message.timestamp.isoformat()}): {text}"  # noqa: WPS221  # message render template; interpolation chain is the readable form


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


_ENVIRONMENT = Environment(
    loader=PackageLoader("tgm.core", "templates"),
    autoescape=False,
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)
_ENVIRONMENT.globals["render_message"] = render_message  # ty: ignore[invalid-assignment]  # jinja2's stubbed globals dict is narrowed to its built-ins
_ENVIRONMENT.filters["to_json"] = _to_json


def build_per_chat_prompt(
    *,
    about_me: str,
    chat_description: str,
    rolling_summary: str,
    criteria_text: str,
    messages: list[Message],
) -> tuple[str, str]:
    user = _ENVIRONMENT.get_template("per_chat.j2").render(
        about_me=about_me,
        chat_description=chat_description,
        rolling_summary=rolling_summary,
        criteria_text=criteria_text,
        messages=messages,
    )
    return _PER_CHAT_SYSTEM_PROMPT, user


def build_global_prompt(
    *,
    about_me: str,
    global_criteria_text: str,
    per_chat_digests: list[PerChatDigestPart],
) -> tuple[str, str]:
    user = _ENVIRONMENT.get_template("global.j2").render(
        about_me=about_me,
        global_criteria_text=global_criteria_text,
        per_chat_digests=per_chat_digests,
    )
    return _GLOBAL_SYSTEM_PROMPT, user


def build_criteria_recalc_prompt(
    *,
    about_me: str,
    current_criteria_text: str,
    feedback_samples: list[FeedbackSample],
) -> tuple[str, str]:
    user = _ENVIRONMENT.get_template("criteria_recalc.j2").render(
        about_me=about_me,
        current_criteria_text=current_criteria_text,
        feedback_samples=feedback_samples,
    )
    return _CRITERIA_RECALC_SYSTEM_PROMPT, user
