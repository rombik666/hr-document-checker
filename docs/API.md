# API documentation

Production-сервис: https://hr-checker.ru

Проект: HR Document Checker — прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

## Базовые адреса

Production: `https://hr-checker.ru`.

Swagger UI: `https://hr-checker.ru/docs`.

Локально: `http://127.0.0.1:8000`.

## Health

`GET /api/v1/health` — проверяет доступность приложения.

## Documents API

```text
POST /api/v1/documents/parse
POST /api/v1/documents/check-formal
POST /api/v1/documents/check-semantic
POST /api/v1/documents/report
GET  /api/v1/documents/reports/{report_id}
GET  /api/v1/documents/reports/{report_id}/export/docx
```

`POST /api/v1/documents/report` — главный endpoint полного цикла проверки: upload → parse → classify → entities → formal checks → semantic checks → RAG context → LLM semantic agent → report build → optional DB save.

Формат запроса: `multipart/form-data`. Основные поля: `file`, `vacancy_text`, `storage_mode`.

## RAG API

```text
GET  /api/v1/rag/status
POST /api/v1/rag/search
```

`GET /api/v1/rag/status` возвращает техническое состояние RAG-подсистемы.

`POST /api/v1/rag/search` выполняет поиск по базе знаний.

## LLM API

```text
GET  /api/v1/llm/status
POST /api/v1/llm/generate
```

## Admin API

```text
GET /api/v1/admin/status
GET /api/v1/admin/roles
GET /api/v1/admin/db/status
GET /api/v1/admin/storage/privacy-check
```

## Metrics API

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
```

## Web routes

```text
GET  /web/login
POST /web/login
GET  /web/register
POST /web/register
GET  /web/dashboard
GET  /web/reports
GET  /web/report/{report_id}
GET  /web/rag/sources
POST /web/contact
```

## Приватность API

API и Web UI не должны сохранять исходные загруженные файлы в долговременном хранилище. При сохранении отчёта используется санитизация данных: маскирование e-mail и телефонов, исключение raw-текста документа и ограничение технической информации для обычных пользователей.
