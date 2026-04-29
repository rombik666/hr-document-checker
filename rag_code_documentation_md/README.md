# HR Document Checker

Учебный прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG и ИИ-агентов.

## Возможности

- загрузка DOCX/PDF;
- формальные и семантические проверки;
- RAG и векторный поиск по базе знаний;
- отчёт Critical / Major / Minor;
- no_store и маскирование персональных данных;
- Web UI, Swagger, DOCX export;
- Docker Compose с PostgreSQL, Prometheus и Grafana;
- backup/restore;
- автоматические тесты.

## Запуск локально

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload
```

## Docker

```powershell
docker compose up --build
```

## Адреса

```text
http://127.0.0.1:8000/web/
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/metrics
http://127.0.0.1:9090
http://127.0.0.1:3000
```

## Основные endpoints

```text
GET  /api/v1/health
GET  /api/v1/metrics
GET  /api/v1/metrics/prometheus
POST /api/v1/documents/parse
POST /api/v1/documents/check-formal
POST /api/v1/documents/check-semantic
POST /api/v1/documents/report
GET  /api/v1/documents/reports/{report_id}
GET  /api/v1/documents/reports/{report_id}/export/docx
POST /api/v1/rag/search
GET  /api/v1/rag/status
GET  /api/v1/admin/status
GET  /api/v1/admin/roles
```

## Тесты

```powershell
python -m pytest
```

## Документация

См. папку `docs/`.
