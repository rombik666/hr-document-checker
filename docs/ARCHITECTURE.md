# Архитектура

Production-сервис: https://hr-checker.ru

Проект: HR Document Checker — прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

## Основной pipeline

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
├── rag/              база знаний, пользовательские источники, чанкинг, эмбеддинги, FAISS
├── reports/          сборка отчёта и DOCX-экспорт
├── schemas/          Pydantic-схемы
├── services/         хранение, backup, privacy diagnostics
└── web/              веб-интерфейс
```

## Роли

`candidate`, `hr`, `admin`.

## Агенты

Формальные агенты: `CompletenessAgent`, `ContactValidationAgent`, `SectionStructureAgent`, `DatePresenceAgent`.

Семантические агенты: `TextQualityAgent`, `ContradictionAgent`, `VacancyRelevanceAgent`, `LlmSemanticAgent`.

Координаторы: `FormalCheckCoordinator`, `SemanticCheckCoordinator`.

## Архитектура RAG

RAG-подсистема предоставляет проверкам дополнительный HR-контекст. Есть базовая база знаний проекта и пользовательские RAG-источники HR-пользователей. Пользовательские источники используются для построения персонального FAISS-индекса.

Статусы индекса: `missing`, `stale`, `building`, `ready`, `failed`.

## LLM

LLM-слой реализован как провайдер-независимый интерфейс. Поддерживаются mock client, Ollama client и OpenAI-compatible client. Docker-демонстрация использует Ollama и модель `qwen2.5:3b`.

## Хранение данных

В БД не должны храниться исходные DOCX/PDF-файлы, полный raw-текст проверяемого документа, немаскированные e-mail и телефоны.

## Развёртывание

Production-схема: Internet → `https://hr-checker.ru` → Nginx → `127.0.0.1:8000` → `hr_doc_checker_app` → PostgreSQL / RAG index / logs / backups.
