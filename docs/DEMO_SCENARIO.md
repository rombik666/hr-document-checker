# Demo scenario

## Запуск

```powershell
docker compose up --build
```

## Сценарий 1

Открыть `/web/`, загрузить хорошее резюме, добавить вакансию, выбрать `temporary`, получить отчёт и скачать DOCX.

## Сценарий 2

Загрузить резюме со слабыми фразами. Ожидаемые issues: `weak_phrase`, `water_phrase`, `vacancy_requirements_gap`.

## Сценарий 3

Проверить `no_store`: отчёт показывается, но не сохраняется.

## Сценарий 4

Проверить Swagger endpoints и RAG status/search.

## Сценарий 5

Открыть Grafana и убедиться, что метрики меняются после генерации отчётов.

## Сценарий 6

Создать backup и выполнить restore через Docker.
