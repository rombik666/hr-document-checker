# Admin guide

## Назначение

Административный слой демонстрирует роль администратора системы.

## Роли

- candidate — загружает документы и получает отчёт;
- hr — проверяет документы кандидатов;
- admin — контролирует правила, агенты, RAG, метрики, backup/restore и документацию.

## Endpoints

```text
GET /api/v1/admin/status
GET /api/v1/admin/roles
```

## Связанные endpoints

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
GET /api/v1/rag/status
GET /api/v1/documents/reports/{report_id}
```
