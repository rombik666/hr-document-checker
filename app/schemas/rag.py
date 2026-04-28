from typing import Any

from pydantic import BaseModel, Field


class RagSource(BaseModel):

    source_id: str
    title: str
    path: str
    content: str


class RagChunk(BaseModel):

    chunk_id: str
    source_id: str
    title: str
    text: str
    position: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagSearchRequest(BaseModel):
    """
    Запрос к RAG-подсистеме.
    """

    query: str
    top_k: int = 3


class RagSearchResult(BaseModel):

    chunk_id: str
    source_id: str
    title: str
    text: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagContext(BaseModel):

    query: str
    results: list[RagSearchResult] = Field(default_factory=list)