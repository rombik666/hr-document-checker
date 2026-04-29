# Architecture

## Pipeline

```text
DOCX/PDF
↓
ParserFactory
↓
DOCXParser / PDFParser
↓
ParsedDocument
↓
DocumentTypeClassifier + SectionClassifier + EntityExtractor
↓
FormalCheckCoordinator
↓
SemanticCheckCoordinator + RagService
↓
ReportBuilder
↓
ReportStorageService
↓
API / Web / DOCX export
```

## Модули

- `app/api/v1` — API;
- `app/web` — Web UI;
- `app/parsers` — DOCX/PDF parsing;
- `app/extractors` — contacts, dates, skills, urls, sections;
- `app/agents/formal` — rule-based agents;
- `app/agents/semantic` — semantic-like agents;
- `app/rag` — RAG, chunks, embeddings, vector search;
- `app/llm` — provider-agnostic LLM interface;
- `app/reports` — report builder and DOCX export;
- `app/db` — SQLAlchemy models/session;
- `app/core` — config, privacy, logging, metrics.

## RAG

Текущий vector search реализован детерминированно через `HashingEmbeddingModel` и `InMemoryVectorStore`. Архитектура допускает замену на `sentence-transformers`, FAISS, OpenAI embeddings или локальную embedding-модель.

## Хранение

Локально используется SQLite, в Docker — PostgreSQL. Raw text документа в БД не сохраняется.

## Безопасность

Система маскирует e-mail и телефоны, поддерживает `no_store`, удаляет временные файлы и не логирует содержимое документов.
