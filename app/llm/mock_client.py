import json

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
        prompt_text = f"{system_prompt or ''}\n{prompt}"

        expects_json = (
            "Return only valid JSON" in prompt_text
            or "Верни только валидный JSON" in prompt_text
            or "валидный JSON" in prompt_text
        )

        if expects_json:
            text = json.dumps(
                {
                    "issues": [
                        {
                            "severity": "Minor",
                            "issue_type": "llm_style_recommendation",
                            "description": (
                                "LLM отметил, что описание опыта можно усилить "
                                "конкретными достижениями и измеримыми результатами."
                            ),
                            "evidence_fragment": "Занимался разработкой backend.",
                            "recommendation": (
                                "Добавьте конкретный результат, использованные технологии "
                                "и измеримый эффект работы."
                            ),
                            "confidence_score": 0.72,
                        }
                    ]
                },
                ensure_ascii=False,
            )
        else:
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