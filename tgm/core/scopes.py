GLOBAL_SCOPE = "global"
_CHAT_PREFIX = "chat:"


def get_chat_scope(chat_id: int) -> str:
    return f"{_CHAT_PREFIX}{chat_id}"


def parse_chat_scope(scope: str) -> tuple[str, int | None]:
    if scope == GLOBAL_SCOPE:
        return (GLOBAL_SCOPE, None)
    if scope.startswith(_CHAT_PREFIX):
        suffix = scope[len(_CHAT_PREFIX) :]
        try:
            return ("chat", int(suffix))
        except ValueError as error:
            raise ValueError(f"chat:<id> must have integer id; got {scope!r}") from error
    raise ValueError(f"scope must be 'global' or 'chat:<id>'; got {scope!r}")
