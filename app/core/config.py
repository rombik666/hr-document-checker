from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    project_name: str = "HR Document Checker"
    app_env: str = "local"
    debug: bool = True

    database_url: str = "sqlite:///./data/app.db"

    knowledge_base_dir: Path = BASE_DIR / "data" / "knowledge_base"

    rag_chunk_size_chars: int = 800
    rag_chunk_overlap_chars: int = 120
    rag_top_k: int = 3

    rag_use_vector_search: bool = True
    rag_embedding_dimension: int = 384
    rag_retriever_type: str = "faiss"
    rag_embedding_backend: str = "hashing"
    rag_embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_embedding_dimension: int = 384
    rag_index_dir: Path = BASE_DIR / "data" / "index"
    rag_allow_embedding_fallback: bool = True

    llm_provider: str = "mock"
    llm_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    llm_api_key: str | None = None
    llm_timeout_seconds: int = 60
    llm_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()