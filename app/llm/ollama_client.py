import httpx

from app.schemas.llm import LlmGenerateResponse


class OllamaClient:

    provider = "ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 60,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> LlmGenerateResponse:
        full_prompt = prompt

        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()

        return LlmGenerateResponse(
            provider=self.provider,
            model=self.model,
            text=data.get("response", ""),
            used_mock=False,
        )

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False