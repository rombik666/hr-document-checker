from typing import Any
from datetime import datetime

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


class RagStatus(BaseModel):
    mode: str = "db_sources"
    source_backend: str = "database"
    user_scope: str = "user"

    knowledge_base_dir: str | None = None
    sources_count: int
    active_sources_count: int = 0
    inactive_sources_count: int = 0
    chunks_count: int

    retriever_type: str
    embedding_dimension: int | None = None
    embedding_backend: str | None = None
    embedding_model_name: str | None = None

    index_dir: str | None = None
    index_exists: bool = False
    reindex_required: bool = False

class RagSourceInfo(BaseModel):
    source_id: str
    title: str
    path: str
    content_length: int


class RagSourcesResponse(BaseModel):
    knowledge_base_dir: str
    sources_count: int
    sources: list[RagSourceInfo] = Field(default_factory=list)


class RagReindexResponse(BaseModel):
    status: str
    message: str
    mode: str = "db_sources"
    source_backend: str = "database"
    sources_count: int
    active_sources_count: int = 0
    chunks_count: int
    embedding_dimension: int | None = None
    index_path: str | None = None
    chunks_path: str | None = None

class UserRagSourceListItem(BaseModel):
    source_id: str
    title: str
    filename: str
    source_type: str
    source_format: str
    content_length: int
    file_size_bytes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserRagSourcesListResponse(BaseModel):
    sources_count: int
    sources: list[UserRagSourceListItem] = Field(default_factory=list)


class UserRagSourceDetails(BaseModel):
    source_id: str
    title: str
    filename: str
    source_type: str
    source_format: str
    content: str
    content_length: int
    file_size_bytes: int
    content_hash: str
    is_active: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class UserRagSourceUploadResponse(BaseModel):
    source: UserRagSourceDetails


class UserRagSourceDeleteResponse(BaseModel):
    source_id: str
    deleted: bool
    message: str