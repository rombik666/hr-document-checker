from app.core.config import settings
from app.core.logging import get_logger
from app.llm.base import LlmClient
from app.llm.mock_client import MockLlmClient
from app.llm.ollama_client import OllamaClient
from app.llm.openai_compatible_client import OpenAICompatibleClient


logger = get_logger(__name__)


def create_llm_client() -> LlmClient:

    provider = settings.llm_provider.lower().strip()

    if not settings.llm_enabled:
        logger.info("llm_disabled using_mock_client")
        return MockLlmClient(model="mock-disabled")

    if provider == "ollama":
        return OllamaClient(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    if provider == "openai_compatible":
        return OpenAICompatibleClient(
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    return MockLlmClient(
        model=settings.llm_model or "mock-llm",
    )