# Final project summary

## Project name

**HR Document Checker**

Official description:

```text
Прототип системы проверки HR- и бизнес-документов с использованием ИИ-агентов
```

## Purpose

The project implements an educational prototype for automated checking of HR and business documents.

The system helps identify:

- missing information;
- weak structure;
- contact issues;
- vague wording;
- possible inconsistencies;
- gaps between a CV and a vacancy;
- general document quality issues.

The system does not make hiring decisions.

## Implemented functionality

### Document processing

- DOCX parsing;
- PDF parsing;
- text extraction;
- table extraction for DOCX;
- section extraction;
- entity extraction.

### Agents

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

### RAG

Implemented:

- knowledge base loader;
- chunker;
- sentence-transformers embeddings;
- FAISS vector store;
- RAG search API;
- RAG status API.

### LLM

Implemented:

- provider-agnostic LLM interface;
- mock client;
- Ollama client;
- OpenAI-compatible client;
- LLM status endpoint;
- LLM generation endpoint;
- LLM semantic agent.

### Reports

Report contains:

- status;
- summary;
- Critical issues;
- Major issues;
- Minor issues;
- evidence fragments;
- recommendations;
- vacancy relevance;
- technical info;
- raw check results.

### Infrastructure

Implemented:

- Dockerfile;
- Docker Compose;
- PostgreSQL;
- pgAdmin;
- Prometheus;
- Grafana;
- logs;
- backup/restore;
- smoke tests.

### Privacy

Implemented:

- `no_store` mode;
- masking of e-mail and phone values;
- no raw text in long-term DB;
- storage privacy diagnostics.

## MVP limitations

The following items are implemented at demonstration/MVP level:

- role model is represented through admin endpoints and documentation;
- full authentication/authorization is not implemented;
- vacancy comparison is performed through `vacancy_text` in one request;
- explicit `comparison_group_id` may be added in future versions;
- production-grade backup scheduling is not implemented.

## Status

The project is ready for educational demonstration and corresponds to the main technical specification requirements.
