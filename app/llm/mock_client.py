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
        if "Return only valid JSON" in prompt or "Return only valid JSON" in (
            system_prompt or ""
        ):
            text = json.dumps(
                {
                    "issues": [
                        {
                            "severity": "Minor",
                            "issue_type": "llm_style_recommendation",
                            "description": (
                                "LLM detected that the document can be improved "
                                "by adding more concrete achievements and measurable results."
                            ),
                            "evidence_fragment": "Занимался разработкой backend.",
                            "recommendation": (
                                "Replace vague descriptions with specific results, "
                                "technologies and measurable impact."
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