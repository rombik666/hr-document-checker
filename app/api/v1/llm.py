from fastapi import APIRouter

from app.core.config import settings
from app.llm.factory import create_llm_client
from app.schemas.llm import (
    LlmGenerateRequest,
    LlmGenerateResponse,
    LlmStatusResponse,
)


router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/status", response_model=LlmStatusResponse)
def get_llm_status() -> LlmStatusResponse:
    client = create_llm_client()
    available = client.is_available()

    return LlmStatusResponse(
        enabled=settings.llm_enabled,
        provider=client.provider,
        model=client.model,
        base_url=settings.llm_base_url,
        available=available,
        message=(
            "LLM provider is available."
            if available
            else "LLM provider is not available."
        ),
    )


@router.post("/generate", response_model=LlmGenerateResponse)
def generate_text(
    request: LlmGenerateRequest,
) -> LlmGenerateResponse:
    client = create_llm_client()

    return client.generate(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )