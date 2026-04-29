# Демонстрационный сценарий

## Цель

Показать полный цикл проверки документа:

```text
запуск системы
↓
открытие Web UI
↓
загрузка DOCX
↓
ввод текста вакансии
↓
генерация отчёта
↓
просмотр отчёта
↓
экспорт DOCX
↓
проверка RAG/LLM/Admin/метрик
```

## 1. Запуск системы

```powershell
.\start.ps1 -NoBuild
```

Откройте:

```text
http://127.0.0.1:8000/web/
```

## 2. Проверка инфраструктуры

Откройте:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8000/api/v1/rag/status
http://127.0.0.1:8000/api/v1/llm/status
http://127.0.0.1:3000
http://127.0.0.1:5050
```

## 3. Загрузка документа

Используйте демонстрационный DOCX-файл или создайте простое резюме со следующими блоками:

- контакты;
- навыки;
- опыт работы;
- образование.

## 4. Текст вакансии

Пример:

```text
Требования: Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux.
```

## 5. Генерация отчёта

Выберите режим хранения:

```text
temporary
```

Запустите проверку.

Ожидаемый результат:

- отображается HTML-отчёт;
- показывается статус отчёта;
- присутствуют секции Critical/Major/Minor;
- сформированы рекомендации;
- создан `report_id`;
- доступна ссылка на JSON;
- доступна ссылка на DOCX export.

## 6. Проверка LLM-агента

В raw check results убедитесь, что при включённом LLM-агенте появился агент:

```text
LlmSemanticAgent
```

## 7. Проверка RAG

Откройте:

```text
http://127.0.0.1:8000/api/v1/rag/status
```

Ожидаемый результат:

```json
{
  "retriever_type": "faiss",
  "index_exists": true
}
```

Если индекс не существует:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/build_rag_index.py
```

## 8. Проверка приватности

Откройте:

```text
http://127.0.0.1:8000/api/v1/admin/storage/privacy-check
```

Ожидаемый результат:

```json
{
  "passed": true,
  "unmasked_email_count": 0,
  "unmasked_phone_count": 0
}
```

## 9. Запуск smoke test

```powershell
.\scripts\smoke_test.ps1
```

Ожидаемый результат:

```text
[OK] Smoke test completed successfully.
```

## 10. Остановка системы

```powershell
.\stop.ps1
```
