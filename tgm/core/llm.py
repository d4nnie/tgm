from typing import Any, Protocol, runtime_checkable

JsonSchema = dict[str, Any]


class LLMBudgetExceededError(RuntimeError):
    pass


@runtime_checkable
class LLMProvider(Protocol):
    async def call_json(
        self,
        system: str,
        user: str,
        schema: JsonSchema,
        max_input_tokens: int,
    ) -> dict: ...
