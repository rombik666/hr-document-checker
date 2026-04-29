# Резервное копирование и восстановление

## Назначение

В проекте реализованы JSON-скрипты резервного копирования и восстановления сохранённых метаданных документов и отчётов.

Backup реализован на уровне приложения, поэтому может работать как с PostgreSQL, так и с SQLite-совместимыми тестовыми окружениями.

## Скрипт резервного копирования

Запуск локально:

```powershell
python scripts\backup_db.py
```

Запуск внутри Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

Файлы backup создаются в папке:

```text
backups/
```

Пример:

```text
backups/backup_20260429_010013.json
```

## Скрипт восстановления

Запуск локально:

```powershell
python scripts\restore_db.py backups\backup_20260429_010013.json
```

Запуск внутри Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/restore_db.py "backups/backup_20260429_010013.json"
```

Внутри Docker нужно использовать Linux-style пути через `/`.

## Содержимое backup

Backup включает:

- метаданные документов;
- метаданные отчётов;
- санитизированный JSON отчёта.

Backup не включает:

- исходные DOCX/PDF-файлы;
- raw-текст документов;
- Hugging Face cache;
- файлы FAISS-индекса;
- логи.

## Безопасность

Перед разрушительными операциями, например:

```powershell
.\reset.ps1
```

создайте резервную копию:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

## Ограничения

Это MVP-уровень backup/restore. Для production-развёртывания PostgreSQL следует добавить нативный `pg_dump` и регулярные задачи резервного копирования по расписанию.
