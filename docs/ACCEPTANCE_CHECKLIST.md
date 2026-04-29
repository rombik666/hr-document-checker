# Acceptance checklist

## 1. General requirements

| Requirement | Status | Implementation |
|---|---|---|
| Server application | Done | FastAPI |
| REST API | Done | `/api/v1/*` |
| Minimal web interface | Done | `/web/` |
| DOCX support | Done | `DOCXParser` |
| PDF support | Done | `PDFParser` |
| PostgreSQL storage | Done | Docker Compose PostgreSQL |
| Docker deployment | Done | `Dockerfile`, `docker-compose.yml` |
| One-command startup | Done | `start.ps1` |
| Monitoring | Done | Prometheus, Grafana |
| Backup/restore | Done | `scripts/backup_db.py`, `scripts/restore_db.py` |

## 2. Document processing

| Requirement | Status |
|---|---|
| Text extraction | Done |
| Section extraction | Done |
| Table extraction for DOCX | Done |
| Entity extraction | Done |
| Document type classification | Done |
| Section classification | Done |

## 3. Agents

| Agent | Type | Status |
|---|---|---|
| `CompletenessAgent` | Formal | Done |
| `ContactValidationAgent` | Formal | Done |
| `SectionStructureAgent` | Formal | Done |
| `DatePresenceAgent` | Formal | Done |
| `TextQualityAgent` | Semantic | Done |
| `ContradictionAgent` | Semantic | Done |
| `VacancyRelevanceAgent` | Semantic | Done |
| `LlmSemanticAgent` | LLM semantic | Done |

## 4. RAG and LLM

| Requirement | Status | Implementation |
|---|---|---|
| Knowledge base | Done | `data/knowledge_base` |
| Chunking | Done | `TextChunker` |
| Embeddings | Done | `sentence-transformers/all-MiniLM-L6-v2` |
| FAISS index | Done | `FaissVectorStore` |
| RAG status API | Done | `/api/v1/rag/status` |
| LLM provider abstraction | Done | `app/llm` |
| Ollama support | Done | `OllamaClient` |
| Mock LLM for tests | Done | `MockLlmClient` |

## 5. Reports

| Requirement | Status |
|---|---|
| Critical/Major/Minor grouping | Done |
| Evidence fragments | Done |
| Recommendations | Done |
| Technical info | Done |
| Vacancy relevance | Done |
| JSON report | Done |
| DOCX export | Done |

## 6. Privacy and storage

| Requirement | Status |
|---|---|
| `no_store` mode | Done |
| Email masking | Done |
| Phone masking | Done |
| No raw text in long-term DB | Done |
| Storage privacy check endpoint | Done |
| pgAdmin visual inspection | Done |

## 7. Testing

| Test group | Status |
|---|---|
| Unit tests | Done |
| API tests | Done |
| Web interface tests | Done |
| Privacy tests | Done |
| RAG/FAISS tests | Done |
| LLM tests | Done |
| Backup/restore tests | Done |
| Metrics tests | Done |
| Performance test | Done |
| Docker smoke test | Done |

## Summary

The project implements the main functional, infrastructure, privacy, RAG/LLM and testing requirements for the educational prototype.
