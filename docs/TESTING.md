# Тестирование

Production-сервис: https://hr-checker.ru

Проект: HR Document Checker — прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

## Запуск всех тестов

```powershell
python -m pytest
```

## Coverage

```powershell
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

## Отдельные группы

```powershell
python -m pytest tests/test_web_interface.py
python -m pytest tests/test_text_quality_agent.py tests/test_llm_semantic_agent.py
python -m pytest tests/test_report_builder.py tests/test_report_api.py tests/test_docx_export.py
python -m pytest tests/test_rag*.py
python -m pytest -m performance
```

## Docker smoke test

```powershell
.\start.ps1 -NoBuild
.\scripts\smoke_test.ps1
```

Smoke test проверяет FastAPI health endpoint, метрики, RAG status, LLM status, admin DB status, privacy check, Web UI, Prometheus, Grafana и pgAdmin.

## Проверка production

```bash
docker ps
sudo nginx -t
sudo systemctl status nginx
docker logs hr_doc_checker_app --tail 100
curl https://hr-checker.ru/api/v1/health
curl https://hr-checker.ru/web/login
```

## Проверка Web UI вручную

1. Регистрация пользователя.
2. Вход пользователя.
3. Проверка документа кандидатом.
4. Просмотр отчёта.
5. Скачивание DOCX.
6. Просмотр истории отчётов.
7. Проверка локального времени в истории.
8. Открытие формы Email.
9. Отправка обращения.
10. Проверка RAG-страницы HR-пользователем.
11. Загрузка RAG-источника.
12. Переиндексация.
13. Повторная проверка документа с RAG-контекстом.

## Стабильность тестов

Для unit-тестов реальные вызовы LLM не требуются. Там, где необходимо, используются mock LLM-клиенты.

## Тесты приватности

Проверяют, что в долговременном хранилище не остаются исходные файлы, полный raw-текст документа, открытые email и телефоны.

## Тесты отчётов

Проверяют сборку summary, распределение замечаний по Critical/Major/Minor, наличие рекомендаций и evidence-фрагментов, корректный DOCX-экспорт и скрытие технических разделов для candidate/hr.
