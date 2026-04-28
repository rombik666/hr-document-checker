import re
from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt", ".md"}

def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def read_text_file(file_path: Path, encoding: str = "utf-8") -> str:
    text = file_path.read_text(encoding=encoding)
    return normalize_text(text)

def load_documents(data_dir: Path) -> list[dict]:
    documents: list[dict] = []

    if not data_dir.exists():
        raise FileNotFoundError(f"Directory does not exist: {data_dir}")
    
    for file_path in sorted(data_dir.rglob("*")):
        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        text = read_text_file(file_path)

        if not text:
            continue

        documents.append(
            {
                "doc_id": str(len(documents)),
                "source": str(file_path),
                "file_name": file_path.name,
                "text": text,
            }
        )
    return documents