from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramCreds:
    api_id: int
    api_hash: str
    phone: str | None = None
