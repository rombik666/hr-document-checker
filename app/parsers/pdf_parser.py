from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

import fitz

from app.parsers.base import DocumentParser
from app.schemas.common import DocumentType, ProcessingStatus, SourceFormat, StorageMode
from app.schemas.documents import DocumentMetadata, DocumentSection, ParsedDocument


class PDFParser(DocumentParser):
    """
    Парсер PDF-документов.

    PDF хуже сохраняет структуру, чем DOCX.
    Поэтому здесь мы читаем документ постранично:
    одна страница PDF = одна секция ParsedDocument.

    В metadata добавляем предупреждение о возможной потере структуры.
    """

    def parse(self, file_path: Path) -> ParsedDocument:
        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        if file_path.suffix.lower() != ".pdf":
            raise ValueError(f"PDFParser поддерживает только .pdf, получено: {file_path.suffix}")

        sections: list[DocumentSection] = []
        text_parts: list[str] = []

        with fitz.open(file_path) as pdf_document:
            for page_index, page in enumerate(pdf_document):
                text = page.get_text("text").strip()

                if not text:
                    continue

                section = DocumentSection(
                    section_id=str(uuid4()),
                    section_type="page",
                    title=f"Страница {page_index + 1}",
                    text=text,
                    position_in_document=page_index,
                    metadata={
                        "source": "pdf_page",
                        "page_number": page_index + 1,
                    },
                )

                sections.append(section)
                text_parts.append(text)

        raw_text = "\n\n".join(text_parts)

        metadata = DocumentMetadata(
            document_id=str(uuid4()),
            document_type=DocumentType.UNKNOWN,
            source_format=SourceFormat.PDF,
            filename=file_path.name,
            upload_time=datetime.now(timezone.utc),
            processing_status=ProcessingStatus.PARSED,
            storage_mode=StorageMode.TEMPORARY,
            hash=None,
            warnings=[
                "PDF может частично терять структуру документа при извлечении текста."
            ],
        )

        return ParsedDocument(
            metadata=metadata,
            raw_text=raw_text,
            sections=sections,
            entities=[],
        )