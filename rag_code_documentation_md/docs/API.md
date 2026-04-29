# API documentation

## Базовый адрес

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

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
GET  /web/
POST /web/report
```

## Главный endpoint

`POST /api/v1/documents/report` выполняет полный цикл: upload, parse, classify, extract entities, formal checks, semantic checks, RAG, report build, optional DB save.

## Параметры form-data

| Поле | Тип | Описание |
|---|---|---|
| file | file | DOCX/PDF |
| vacancy_text | string | текст вакансии, optional |
| storage_mode | string | temporary / metadata_only / no_store |

## RAG

`POST /api/v1/rag/search` выполняет поиск по базе знаний.  
`GET /api/v1/rag/status` возвращает состояние RAG-подсистемы.

## Экспорт отчёта

`GET /api/v1/documents/reports/{report_id}/export/docx` возвращает сохранённый отчёт в DOCX.
