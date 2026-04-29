from pydantic import BaseModel, Field


class LlmMessage(BaseModel):
    role: str = Field(..., examples=["system", "user", "assistant"])
    content: str


class LlmGenerateRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None
    temperature: float = 0.1
    max_tokens: int = 700


class LlmGenerateResponse(BaseModel):
    provider: str
    model: str
    text: str
    used_mock: bool = False


class LlmStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    base_url: str | None = None
    available: bool
    message: str