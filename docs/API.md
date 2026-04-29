# API documentation

## Базовый адрес

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

## Health

### GET `/api/v1/health`

Проверяет доступность приложения.

Пример ответа:

```json
{
  "status": "ok",
  "service": "HR Document Checker"
}
```

## Documents API

### POST `/api/v1/documents/parse`

Парсит DOCX/PDF-документ и возвращает структуру документа.

Формат запроса:

```text
multipart/form-data
```

Поля:

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `file` | file | да | DOCX/PDF-документ |

### POST `/api/v1/documents/check-formal`

Запускает формальные проверки документа.

Формальные агенты:

- `CompletenessAgent`;
- `ContactValidationAgent`;
- `SectionStructureAgent`;
- `DatePresenceAgent`.

### POST `/api/v1/documents/check-semantic`

Запускает семантические проверки документа.

Поля:

| Поле | Тип | Обязательное | Описание |
|---|---|---:|---|
| `file` | file | да | DOCX/PDF-документ |
| `vacancy_text` | string | нет | Текст вакансии |
| `storage_mode` | string | нет | `temporary`, `metadata_only`, `no_store` |

### POST `/api/v1/documents/report`

Главный endpoint полного цикла проверки:

```text
upload
↓
parse
↓
classify
↓
extract entities
↓
formal checks
↓
semantic checks
↓
RAG context
↓
LLM semantic agent
↓
report build
↓
optional DB save
```

### GET `/api/v1/documents/reports/{report_id}`

Возвращает сохранённый JSON-отчёт.

### GET `/api/v1/documents/reports/{report_id}/export/docx`

Экспортирует сохранённый отчёт в DOCX.

## RAG API

### GET `/api/v1/rag/status`

Возвращает техническое состояние RAG-подсистемы.

Ожидаемые поля:

```json
{
  "retriever_type": "faiss",
  "embedding_backend": "sentence_transformer",
  "embedding_model_name": "sentence-transformers/all-MiniLM-L6-v2",
  "index_exists": true
}
```

### POST `/api/v1/rag/search`

Выполняет поиск по базе знаний.

Пример запроса:

```json
{
  "query": "что должно быть в резюме python backend developer",
  "top_k": 3
}
```

## LLM API

### GET `/api/v1/llm/status`

Показывает состояние LLM-провайдера.

### POST `/api/v1/llm/generate`

Тестовая генерация ответа через выбранный LLM provider.

Пример запроса:

```json
{
  "system_prompt": "You are an HR document checking assistant.",
  "prompt": "Give one recommendation for improving a CV.",
  "temperature": 0.1,
  "max_tokens": 120
}
```

## Admin API

### GET `/api/v1/admin/status`

Проверка доступности административного слоя.

### GET `/api/v1/admin/roles`

Возвращает демонстрационные роли системы.

### GET `/api/v1/admin/db/status`

Возвращает состояние БД без раскрытия содержимого документов.

### GET `/api/v1/admin/storage/privacy-check`

Проверяет, что в сохранённых отчётах не обнаружены очевидные незащищённые e-mail и телефоны.

## Metrics API

### GET `/api/v1/metrics`

Возвращает метрики в JSON.

### GET `/api/v1/metrics/prometheus`

Возвращает метрики в формате Prometheus.
