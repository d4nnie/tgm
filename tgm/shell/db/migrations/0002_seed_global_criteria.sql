INSERT OR IGNORE INTO importance_criteria (scope, criteria_text, version, updated_at)
VALUES (
    'global',
    'Помечать как важное: сообщения, явно адресованные пользователю по имени или контексту без @username-mention; вопросы, требующие ответа от пользователя; решения и договорённости; дедлайны и даты.

Не помечать: сообщения с @username-mention пользователя (они и так уведомляют через Telegram); реакции; «спасибо», смайлы, мелкий шум.',
    1,
    CURRENT_TIMESTAMP
);
