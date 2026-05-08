from datetime import UTC, datetime

from tgm.core.prompts import (
    build_criteria_recalc_prompt,
    build_global_prompt,
    build_per_chat_prompt,
)
from tgm.core.types import (
    FeedbackSample,
    Message,
    PerChatDigestPart,
    PerChatHighlightPart,
)


def _message(message_id: int, text: str | None, sender_name: str | None = "Alice") -> Message:
    return Message(
        chat_id=999,
        message_id=message_id,
        timestamp=datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
        sender_id=100,
        sender_name=sender_name,
        text=text,
        reply_to_message_id=None,
        edited_at=None,
        raw_json="{}",
    )


def test_build_per_chat_prompt_golden():
    system, user = build_per_chat_prompt(
        about_me="Я бэкенд-разработчик.",
        chat_description="Команда X, фокус на ингест.",
        rolling_summary="Прошлый раз обсуждали retry policy.",
        criteria_text="Важно: блокеры, дедлайны, решения.",
        messages=[
            _message(42, "deploy planned"),
            _message(43, "rollback initiated", sender_name="Bob"),
        ],
    )

    assert system == "Ты — ассистент, который делает краткие сводки чатов.\nВозвращай только валидный JSON."
    assert user == (
        "=== About me ===\nЯ бэкенд-разработчик.\n\n"
        "=== Chat profile ===\nКоманда X, фокус на ингест.\n\n"
        "=== Importance criteria ===\nВажно: блокеры, дедлайны, решения.\n\n"
        "=== Previous rolling summary ===\nПрошлый раз обсуждали retry policy.\n\n"
        "=== New messages (chronological) ===\n"
        "[message_id=42] Alice (2026-05-07T12:00:00+00:00): deploy planned\n"
        "[message_id=43] Bob (2026-05-07T12:00:00+00:00): rollback initiated\n\n"
        "Задача:\n"
        "1. Кратко суммаризируй обсуждение за этот период (на языке чата).\n"
        "2. Выдели важные сообщения по критериям выше — для каждого message_id и краткое объяснение why.\n"
        "3. Обнови rolling_summary, чтобы он отражал актуальное состояние обсуждения."
    )


def test_build_per_chat_prompt_handles_empty_messages():
    _, user = build_per_chat_prompt(
        about_me="x",
        chat_description="y",
        rolling_summary="z",
        criteria_text="c",
        messages=[],
    )

    assert "=== New messages (chronological) ===\n\n\n" in user


def test_build_per_chat_prompt_renders_none_text_and_sender():
    _, user = build_per_chat_prompt(
        about_me="x",
        chat_description="y",
        rolling_summary="z",
        criteria_text="c",
        messages=[_message(1, None, sender_name=None)],
    )

    assert "[message_id=1] unknown (2026-05-07T12:00:00+00:00): <no text>" in user


def test_build_global_prompt_golden():
    system, user = build_global_prompt(
        about_me="Я разработчик.",
        global_criteria_text="Важно: дедлайны, блокеры.",
        per_chat_digests=[
            PerChatDigestPart(
                chat_id=111,
                title="Team X",
                summary="Обсудили деплой.",
                highlights=[PerChatHighlightPart(message_id=42, why="блокер")],
            ),
            PerChatDigestPart(
                chat_id=222,
                title="Team Y",
                summary="Без новостей.",
                highlights=[],
            ),
        ],
    )

    assert (
        system == "Ты — ассистент, который собирает общий обзор по нескольким чатам.\nВозвращай только валидный JSON."
    )
    assert '[chat_id=111, title="Team X"]\nsummary: Обсудили деплой.' in user
    assert 'highlights: [{message_id=42, why="блокер"}]' in user
    assert "---" in user
    assert '[chat_id=222, title="Team Y"]' in user
    assert user.endswith(
        "Задача:\n"
        "Собери единый обзор: где требуется внимание пользователя, где есть решения / дедлайны,\n"
        "что можно проигнорировать. Highlights — со ссылкой на конкретный чат и сообщение."
    )


def test_build_criteria_recalc_prompt_golden():
    system, user = build_criteria_recalc_prompt(
        about_me="Я разработчик.",
        current_criteria_text="Старые правила.",
        feedback_samples=[
            FeedbackSample(
                user_comment="Это важно потому что блокер",
                messages=[_message(7, "deploy stuck")],
            ),
        ],
    )

    assert system.startswith("Ты — ассистент, обновляющий критерии")
    assert "=== Current criteria text ===\nСтарые правила." in user
    assert "[sample 1]" in user
    assert 'comment: "Это важно потому что блокер"' in user
    assert "[message_id=7] Alice" in user
    assert user.endswith(
        "Задача:\n"
        "Перепиши criteria_text так, чтобы он учитывал эти примеры (и продолжал учитывать всё,\n"
        "что было раньше). Не теряй старые правила без причины."
    )


def test_per_chat_system_prompt_does_not_mention_response_format():
    system, _ = build_per_chat_prompt(
        about_me="x",
        chat_description="y",
        rolling_summary="z",
        criteria_text="c",
        messages=[],
    )

    assert "формате" not in system.lower()
    assert "schema" not in system.lower()


def test_global_system_prompt_does_not_mention_response_format():
    system, _ = build_global_prompt(about_me="x", global_criteria_text="y", per_chat_digests=[])

    assert "формате" not in system.lower()
    assert "schema" not in system.lower()


def test_criteria_recalc_system_prompt_does_not_mention_response_format():
    system, _ = build_criteria_recalc_prompt(
        about_me="x",
        current_criteria_text="y",
        feedback_samples=[],
    )

    assert "формате" not in system.lower()
    assert "schema" not in system.lower()
