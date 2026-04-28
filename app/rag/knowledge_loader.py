from pathlib import Path
from uuid import uuid4

from app.schemas.rag import RagSource


class KnowledgeLoader:
    """
    Загружает текстовые источники из базы знаний.

    """

    SUPPORTED_SUFFIXES = {".md", ".txt"}

    def load_sources(self, knowledge_base_dir: Path) -> list[RagSource]:
        if not knowledge_base_dir.exists():
            return []

        sources: list[RagSource] = []

        for file_path in knowledge_base_dir.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.SUPPORTED_SUFFIXES:
                continue

            content = file_path.read_text(encoding="utf-8").strip()

            if not content:
                continue

            sources.append(
                RagSource(
                    source_id=str(uuid4()),
                    title=file_path.stem,
                    path=str(file_path),
                    content=content,
                )
            )

        return sources