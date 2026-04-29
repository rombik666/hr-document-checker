from typing import Protocol

from app.schemas.llm import LlmGenerateResponse


class LlmClient(Protocol):

    provider: str
    model: str

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> LlmGenerateResponse:
        ...

    def is_available(self) -> bool:
        ...