# Архитектура

## Общее описание

**HR Document Checker** — это модульное FastAPI-приложение для проверки HR- и бизнес-документов.

Основной pipeline обработки:

```text
Загрузка DOCX/PDF
↓
ParserFactory
↓
DOCXParser / PDFParser
↓
Классификация документа
↓
Извлечение секций и сущностей
↓
Формальные агенты
↓
Семантические агенты
↓
FAISS RAG-контекст
↓
LLM semantic agent
↓
ReportBuilder
↓
Опциональное сохранение
↓
Web/API/DOCX export
```

## Основные слои приложения

```text
app/
├── api/              REST API-роутеры
├── agents/           формальные и семантические агенты проверки
├── coordinator/      оркестрация агентов
├── db/               SQLAlchemy-модели и сессии БД
├── extractors/       извлечение сущностей
├── llm/              абстракция LLM-провайдера
├── middleware/       логирование запросов
├── parsers/          парсеры DOCX/PDF
├── rag/              база знаний, чанкинг, эмбеддинги, FAISS
├── reports/          сборка отчёта и DOCX-экспорт
├── schemas/          Pydantic-схемы
├── services/         хранение, backup, privacy diagnostics
└── web/              минимальный веб-интерфейс
```

## Агентная архитектура

В системе используется мультиагентный подход: каждый агент отвечает за отдельный тип проверки документа.

Формальные агенты:

- `CompletenessAgent`;
- `ContactValidationAgent`;
- `SectionStructureAgent`;
- `DatePresenceAgent`.

Семантические агенты:

- `TextQualityAgent`;
- `ContradictionAgent`;
- `VacancyRelevanceAgent`;
- `LlmSemanticAgent`.

Координаторы:

- `FormalCheckCoordinator`;
- `SemanticCheckCoordinator`.

## Архитектура RAG

Основной Docker-режим использует:

```text
sentence-transformers/all-MiniLM-L6-v2
+
FAISS
```

Pipeline RAG-подсистемы:

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

Fallback/test-режимы:

- `HashingEmbeddingModel`;
- `InMemoryVectorStore`;
- `SimpleRagRetriever`.

## Архитектура LLM

LLM-слой реализован как провайдер-независимый интерфейс.

Поддерживаемые клиенты:

- `MockLlmClient`;
- `OllamaClient`;
- `OpenAICompatibleClient`.

Docker-демонстрация использует Ollama:

```text
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=qwen2.5:7b
```

Для стабильности автоматических тестов используется mock-режим.

## Архитектура хранения данных

Таблицы базы данных:

- `documents`;
- `reports`.

В базе данных хранятся:

- метаданные документов;
- очищенные/санитизированные отчёты;
- техническая информация отчёта.

В базе данных не хранятся:

- исходные загруженные DOCX/PDF-файлы;
- полный raw-текст документа;
- немаскированные персональные данные.

## Архитектура развёртывания

Сервисы Docker Compose:

- FastAPI-приложение;
- PostgreSQL;
- pgAdmin;
- Prometheus;
- Grafana.

## Мониторинг

Приложение предоставляет endpoints:

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
```

Prometheus собирает метрики приложения, а Grafana используется для их визуализации.
