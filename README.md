# HR Document Checker

**HR Document Checker** — веб-приложение для автоматизированной проверки HR-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

Production-версия сервиса доступна по адресу:

```text
https://hr-checker.ru
```

## Назначение проекта

Система предназначена для первичной проверки резюме, сопроводительных писем, анкет кандидатов, вакансий и HR-регламентов. Система не принимает кадровые решения и не заменяет HR-специалиста. Она формирует структурированный отчёт с замечаниями, приоритетами, evidence-фрагментами и рекомендациями по улучшению документа.

## Основные возможности

- регистрация и вход пользователей;
- роли `candidate`, `hr`, `admin`;
- веб-интерфейс для кандидата и HR-специалиста;
- загрузка DOCX/PDF-документов;
- формальные и семантические проверки;
- LLM semantic agent через Ollama/OpenAI-compatible интерфейс;
- RAG-подсистема с пользовательскими источниками знаний;
- персональный FAISS-индекс для HR-пользователей;
- история отчётов и DOCX-экспорт;
- форма обратной связи через SMTP;
- PostgreSQL, pgAdmin, Prometheus, Grafana для отслеживания метрик;
- backup/restore и smoke tests.

## Production-адреса

| Раздел | URL |
|---|---|
| Web UI | `https://hr-checker.ru/web/` |
| Вход | `https://hr-checker.ru/web/login` |
| Регистрация | `https://hr-checker.ru/web/register` |
| Личный кабинет | `https://hr-checker.ru/web/dashboard` |
| История отчётов | `https://hr-checker.ru/web/reports` |
| RAG-источники | `https://hr-checker.ru/web/rag/sources` |
| Swagger API | `https://hr-checker.ru/docs` |
| Health check | `https://hr-checker.ru/api/v1/health` |
| RAG status | `https://hr-checker.ru/api/v1/rag/status` |
| LLM status | `https://hr-checker.ru/api/v1/llm/status` |

## Локальный запуск

```powershell
.\start.ps1
.\start.ps1 -NoBuild
.\stop.ps1
.\reset.ps1
```

## Локальные адреса

| Сервис | URL |
|---|---|
| Web UI | `http://127.0.0.1:8000/web/` |
| Swagger API | `http://127.0.0.1:8000/docs` |
| Prometheus | `http://127.0.0.1:9090` |
| Grafana | `http://127.0.0.1:3000` |
| pgAdmin | `http://127.0.0.1:5050` |

На сервере административные сервисы привязаны к `127.0.0.1` и не открываются напрямую в интернет.

## RAG и FAISS

HR-пользователь может загружать собственные источники знаний: вакансии, регламенты, требования, правила проверки и другие HR-документы. После изменения базы знаний пользователь запускает переиндексацию. На основе активных источников строится персональный FAISS-индекс.

## LLM / Ollama

Docker-демонстрация использует Ollama: `qwen2.5:3b`. Для стабильных автоматических тестов используется mock-режим.

## SMTP

Форма обратной связи отправляет сообщение на почту проекта через SMTP. Для Яндекс.Почты используется пароль приложения.

## Тестирование

```powershell
python -m pytest
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
.\scripts\smoke_test.ps1
```

## Документация

См. папку `docs/`.
