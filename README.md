# HR Document Checker

Учебный прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, FAISS и ИИ-агентов.

## Назначение

HR Document Checker помогает выполнять первичную автоматизированную проверку документов:

- резюме;
- сопроводительных писем;
- анкет кандидатов;
- текстов вакансий и связанных HR-документов.

Система не принимает кадровые решения. Она формирует технический отчёт с замечаниями, рекомендациями и evidence-фрагментами.

## Возможности

- загрузка DOCX/PDF-документов;
- парсинг текста, таблиц и секций;
- извлечение e-mail, телефонов, ссылок, дат и навыков;
- формальные проверки документа;
- семантические проверки;
- FAISS RAG по базе знаний;
- LLM semantic agent через Ollama/OpenAI-compatible интерфейс;
- итоговый отчёт с уровнями Critical / Major / Minor;
- режим `no_store`;
- маскирование персональных данных перед сохранением;
- Web UI;
- Swagger API;
- DOCX export отчёта;
- PostgreSQL в Docker;
- pgAdmin;
- Prometheus и Grafana;
- backup/restore;
- unit, integration, privacy, RAG, LLM, performance и smoke tests.

## Быстрый запуск

Для запуска Docker-окружения:

```powershell
.\start.ps1
```

Если образ уже собран:

```powershell
.\start.ps1 -NoBuild
```

Остановка:

```powershell
.\stop.ps1
```

Полный сброс Docker volumes:

```powershell
.\reset.ps1
```

## Адреса

| Сервис | URL |
|---|---|
| Web UI | <http://127.0.0.1:8000/web/> |
| Swagger API | <http://127.0.0.1:8000/docs> |
| Health check | <http://127.0.0.1:8000/api/v1/health> |
| Metrics JSON | <http://127.0.0.1:8000/api/v1/metrics> |
| Prometheus metrics | <http://127.0.0.1:8000/api/v1/metrics/prometheus> |
| RAG status | <http://127.0.0.1:8000/api/v1/rag/status> |
| LLM status | <http://127.0.0.1:8000/api/v1/llm/status> |
| Prometheus | <http://127.0.0.1:9090> |
| Grafana | <http://127.0.0.1:3000> |
| pgAdmin | <http://127.0.0.1:5050> |

## Grafana

```text
login: admin
password: admin
```

## pgAdmin

```text
email: admin@example.com
password: admin
```

PostgreSQL connection в pgAdmin:

```text
Host: postgres
Port: 5432
Database: hr_doc_checker
Username: hr_user
Password: hr_password
```

## Основные endpoints

### Documents

```text
POST /api/v1/documents/parse
POST /api/v1/documents/check-formal
POST /api/v1/documents/check-semantic
POST /api/v1/documents/report
GET  /api/v1/documents/reports/{report_id}
GET  /api/v1/documents/reports/{report_id}/export/docx
```

### RAG

```text
GET  /api/v1/rag/status
POST /api/v1/rag/search
```

### LLM

```text
GET  /api/v1/llm/status
POST /api/v1/llm/generate
```

### Admin

```text
GET /api/v1/admin/status
GET /api/v1/admin/roles
GET /api/v1/admin/db/status
GET /api/v1/admin/storage/privacy-check
```

### Metrics

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
```

## FAISS RAG index

Построить индекс локально:

```powershell
python scripts\build_rag_index.py
```

Построить индекс внутри Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/build_rag_index.py
```

Сгенерированные файлы:

```text
data/index/faiss.index
data/index/chunks.json
```

Эти файлы являются артефактами и не должны попадать в Git.

## LLM / Ollama

Для Docker-демонстрации используется локальная Ollama:

```yaml
LLM_PROVIDER: "ollama"
LLM_BASE_URL: "http://host.docker.internal:11434"
LLM_MODEL: "qwen2.5:7b"
LLM_ENABLED: "true"
LLM_SEMANTIC_AGENT_ENABLED: "true"
```

Для стабильных локальных тестов можно использовать mock-режим:

```env
LLM_PROVIDER=mock
LLM_SEMANTIC_AGENT_ENABLED=false
```

## Тестирование

Запустить все тесты:

```powershell
python -m pytest
```

Запустить coverage:

```powershell
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

Запустить performance tests:

```powershell
python -m pytest -m performance
```

Запустить Docker smoke test:

```powershell
.\scripts\smoke_test.ps1
```

## Документация

См. папку [`docs/`](docs/).
