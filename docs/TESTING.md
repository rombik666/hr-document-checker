# Тестирование

## Общее описание

Проект содержит автоматизированные тесты для следующих компонентов:

- парсеры;
- экстракторы;
- классификаторы;
- формальные агенты;
- семантические агенты;
- LLM-инфраструктура;
- RAG и FAISS;
- сборка отчётов;
- хранение данных;
- приватность;
- API endpoints;
- веб-интерфейс;
- метрики;
- backup/restore;
- производительность;
- Docker smoke testing.

## Запуск всех тестов

```powershell
python -m pytest
```

## Запуск тестов с подробным выводом

```powershell
python -m pytest -v
```

## Покрытие тестами

Сформировать отчёт покрытия:

```powershell
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

HTML-отчёт:

```text
htmlcov/index.html
```

Сгенерированные файлы покрытия игнорируются Git:

```text
htmlcov/
.coverage
coverage.xml
```

## Performance-тесты

Performance-тесты отмечены маркером:

```text
performance
```

Запуск:

```powershell
python -m pytest -m performance
```

## Docker smoke test

Запустите окружение:

```powershell
.\start.ps1 -NoBuild
```

Запустите smoke test:

```powershell
.\scripts\smoke_test.ps1
```

Smoke test проверяет:

- FastAPI health endpoint;
- endpoint метрик;
- Prometheus metrics endpoint;
- RAG status;
- LLM status;
- admin DB status;
- privacy check;
- Web UI;
- Prometheus;
- Grafana;
- pgAdmin.

## Стабильность тестов

Для unit-тестов реальные вызовы LLM не требуются. Там, где необходимо, используются mock LLM-клиенты.

Docker-демонстрация может использовать Ollama с настройкой:

```text
LLM_PROVIDER=ollama
```
