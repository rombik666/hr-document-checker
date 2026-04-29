# Backup and restore

## Backup локально

```powershell
python scripts\backup_db.py
```

## Restore локально

```powershell
python scripts\restore_db.py backups\backup_YYYYMMDD_HHMMSS.json
```

## Backup в Docker

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

## Restore в Docker

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/restore_db.py "backups/backup_YYYYMMDD_HHMMSS.json"
```

В Docker используется Linux-путь через `/`, не Windows-путь через `\`.

## Содержимое backup

Backup содержит метаданные документов и сохранённые отчёты. Исходные DOCX/PDF и raw_text не сохраняются.
