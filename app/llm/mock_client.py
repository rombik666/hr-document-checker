from app.schemas.llm import LlmGenerateResponse


class MockLlmClient:

    provider = "mock"

    def __init__(self, model: str = "mock-llm") -> None:
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> LlmGenerateResponse:
        text = (
            "Mock LLM response: document analysis completed. "
            "The response is deterministic and safe for tests."
        )

        return LlmGenerateResponse(
            provider=self.provider,
            model=self.model,
            text=text,
            used_mock=True,
        )

    def is_available(self) -> bool:
        return True