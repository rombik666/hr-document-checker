from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve.parents[2]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "indexes"
LOGS_DIR = BASE_DIR / "logs"

@dataclass(frozen = True)
class Settings:
    embedding_model_name: str = os.getenv(
        "EMBEDDING_MODEL_NAME",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    reranker_model_name: str = os.getenv(
    "RERANKER_MODEL_NAME",
    "cross-encoder/ms-marco-MiniLM-L6-v2",
    )
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None
    llm_api_key: str | None = os.getenv("LLM_API_KEY") or None

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    rerank_top_n: int = int(os.getenv("RERANK_TOP_N", "3"))

settings = Settings()