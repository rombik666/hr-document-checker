# Architecture

## Overview

HR Document Checker is a modular FastAPI application for checking HR and business documents.

Main pipeline:

```text
Upload DOCX/PDF
↓
ParserFactory
↓
DOCXParser / PDFParser
↓
Document classification
↓
Section and entity extraction
↓
Formal agents
↓
Semantic agents
↓
FAISS RAG context
↓
LLM semantic agent
↓
ReportBuilder
↓
Optional storage
↓
Web/API/DOCX export
```

## Main layers

```text
app/
├── api/              REST API routers
├── agents/           formal and semantic checking agents
├── coordinator/      agent orchestration
├── db/               SQLAlchemy models and DB session
├── extractors/       entity extraction
├── llm/              LLM provider abstraction
├── middleware/       request logging
├── parsers/          DOCX/PDF parsers
├── rag/              knowledge base, chunking, embeddings, FAISS
├── reports/          report builder and DOCX exporter
├── schemas/          Pydantic schemas
├── services/         storage, backup, privacy diagnostics
└── web/              minimal web interface
```

## Agent architecture

The system uses a multi-agent approach.

Formal agents:

- `CompletenessAgent`;
- `ContactValidationAgent`;
- `SectionStructureAgent`;
- `DatePresenceAgent`.

Semantic agents:

- `TextQualityAgent`;
- `ContradictionAgent`;
- `VacancyRelevanceAgent`;
- `LlmSemanticAgent`.

Coordinators:

- `FormalCheckCoordinator`;
- `SemanticCheckCoordinator`.

## RAG architecture

The main Docker mode uses:

```text
sentence-transformers/all-MiniLM-L6-v2
+
FAISS
```

RAG pipeline:

```text
data/knowledge_base/*.md
↓
KnowledgeLoader
↓
TextChunker
↓
SentenceTransformerEmbeddingModel
↓
FaissVectorStore
↓
data/index/faiss.index
data/index/chunks.json
```

Fallback/test modes:

- `HashingEmbeddingModel`;
- `InMemoryVectorStore`;
- `SimpleRagRetriever`.

## LLM architecture

LLM layer is provider-agnostic.

Supported clients:

- `MockLlmClient`;
- `OllamaClient`;
- `OpenAICompatibleClient`.

Docker demo uses Ollama:

```text
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=qwen2.5:7b
```

Tests use mock mode for stability.

## Storage architecture

Database tables:

- `documents`;
- `reports`.

The database stores:

- document metadata;
- sanitized reports;
- technical report information.

The database does not store:

- original uploaded files;
- full raw document text;
- unmasked personal data.

## Deployment architecture

Docker Compose services:

- FastAPI application;
- PostgreSQL;
- pgAdmin;
- Prometheus;
- Grafana.

## Monitoring

Application exposes:

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
```

Prometheus scrapes application metrics. Grafana visualizes them.
