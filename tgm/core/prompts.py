import json

from tgm.core.types import FeedbackSample, Message, PerChatDigestPart

_PER_CHAT_SYSTEM_PROMPT = "Ты — ассистент, который делает краткие сводки чатов.\nВозвращай только валидный JSON."

_GLOBAL_SYSTEM_PROMPT = (
    "Ты — ассистент, который собирает общий обзор по нескольким чатам.\nВозвращай только валидный JSON."
)

_CRITERIA_RECALC_SYSTEM_PROMPT = (
    "Ты — ассистент, обновляющий критерии важности сообщений на основе примеров от пользователя.\n"
    "Возвращай только валидный JSON."
)

_PER_CHAT_TASK = (
    "Задача:\n"
    "1. Кратко суммаризируй обсуждение за этот период (на языке чата).\n"
    "2. Выдели важные сообщения по критериям выше — для каждого message_id и краткое объяснение why.\n"
    "3. Обнови rolling_summary, чтобы он отражал актуальное состояние обсуждения."
)

_GLOBAL_TASK = (
    "Задача:\n"
    "Собери единый обзор: где требуется внимание пользователя, где есть решения / дедлайны,\n"
    "что можно проигнорировать. Highlights — со ссылкой на конкретный чат и сообщение."
)

_CRITERIA_RECALC_TASK = (
    "Задача:\n"
    "Перепиши criteria_text так, чтобы он учитывал эти примеры (и продолжал учитывать всё,\n"
    "что было раньше). Не теряй старые правила без причины."
)


def build_per_chat_prompt(
    *,
    about_me: str,
    chat_description: str,
    rolling_summary: str,
    criteria_text: str,
    messages: list[Message],
) -> tuple[str, str]:
    sections = [
        _section("About me", about_me),
        _section("Chat profile", chat_description),
        _section("Importance criteria", criteria_text),
        _section("Previous rolling summary", rolling_summary),
        _section("New messages (chronological)", _render_messages(messages)),
        _PER_CHAT_TASK,
    ]
    return _PER_CHAT_SYSTEM_PROMPT, "\n\n".join(sections)


def build_global_prompt(
    *,
    about_me: str,
    global_criteria_text: str,
    per_chat_digests: list[PerChatDigestPart],
) -> tuple[str, str]:
    sections = [
        _section("About me", about_me),
        _section("Importance criteria (global)", global_criteria_text),
        _section("Per-chat digests за последний цикл", _render_digest_parts(per_chat_digests)),
        _GLOBAL_TASK,
    ]
    return _GLOBAL_SYSTEM_PROMPT, "\n\n".join(sections)


def build_criteria_recalc_prompt(
    *,
    about_me: str,
    current_criteria_text: str,
    feedback_samples: list[FeedbackSample],
) -> tuple[str, str]:
    sections = [
        _section("About me", about_me),
        _section("Current criteria text", current_criteria_text),
        _section("Feedback samples", _render_feedback_samples(feedback_samples)),
        _CRITERIA_RECALC_TASK,
    ]
    return _CRITERIA_RECALC_SYSTEM_PROMPT, "\n\n".join(sections)


def _section(header: str, body: str) -> str:
    return f"=== {header} ===\n{body}"


def _render_messages(messages: list[Message]) -> str:
    if not messages:
        return ""
    return "\n".join(_render_message(message) for message in messages)


def _render_message(message: Message) -> str:
    sender = message.sender_name or "unknown"
    text = message.text if message.text is not None else "<no text>"
    return f"[message_id={message.message_id}] {sender} ({message.timestamp.isoformat()}): {text}"


def _render_digest_parts(parts: list[PerChatDigestPart]) -> str:
    if not parts:
        return ""
    return "\n---\n".join(_render_digest_part(part) for part in parts)


def _render_digest_part(part: PerChatDigestPart) -> str:
    highlights = ", ".join(
        f"{{message_id={highlight.message_id}, why={json.dumps(highlight.why, ensure_ascii=False)}}}"
        for highlight in part.highlights
    )
    title = json.dumps(part.title, ensure_ascii=False)
    return f"[chat_id={part.chat_id}, title={title}]\nsummary: {part.summary}\nhighlights: [{highlights}]"


def _render_feedback_samples(samples: list[FeedbackSample]) -> str:
    if not samples:
        return ""
    blocks = []
    for index, sample in enumerate(samples, start=1):
        comment = json.dumps(sample.user_comment or "", ensure_ascii=False)
        rendered_messages = "\n    ".join(_render_message(message) for message in sample.messages)
        blocks.append(f"[sample {index}]\n  comment: {comment}\n  messages:\n    {rendered_messages}")
    return "\n".join(blocks)
