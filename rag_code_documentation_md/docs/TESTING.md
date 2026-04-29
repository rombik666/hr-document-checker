# Testing

## Запуск

```powershell
python -m pytest
```

## Покрытие

- parser tests;
- extractor tests;
- classifier tests;
- formal agent tests;
- semantic agent tests;
- RAG tests;
- report tests;
- storage tests;
- privacy/no_store tests;
- web tests;
- metrics tests;
- DOCX export tests;
- backup/restore tests;
- admin/LLM interface tests.

## Ключевые сценарии

1. Хорошее резюме -> `ready`.
2. Нет контактов -> `missing_email`, `missing_phone`.
3. Слабые формулировки -> `weak_phrase`, `water_phrase`.
4. Резюме + вакансия -> `vacancy_requirements_gap`.
5. no_store -> отчёт не сохраняется.
6. Экспорт DOCX -> сохранённый отчёт скачивается как Word-файл.
7. Backup/restore -> данные восстанавливаются без дублирования.
