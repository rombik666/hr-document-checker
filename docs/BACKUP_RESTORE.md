# Backup and restore

## Purpose

The project includes JSON-based backup and restore scripts for stored document metadata and reports.

Backup is implemented at application level, so it can work with both PostgreSQL and SQLite-compatible test environments.

## Backup script

Run locally:

```powershell
python scripts\backup_db.py
```

Run inside Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

Backup files are created in:

```text
backups/
```

Example:

```text
backups/backup_20260429_010013.json
```

## Restore script

Run locally:

```powershell
python scripts\restore_db.py backups\backup_20260429_010013.json
```

Run inside Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/restore_db.py "backups/backup_20260429_010013.json"
```

Inside Docker use Linux-style paths with `/`.

## Backup content

Backup includes:

- document metadata;
- report metadata;
- sanitized report JSON.

Backup does not include:

- original DOCX/PDF files;
- raw document text;
- Hugging Face cache;
- FAISS index files;
- logs.

## Safety

Before destructive operations such as:

```powershell
.\reset.ps1
```

create a backup:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

## Limitations

This is MVP-level backup/restore. For production PostgreSQL deployment, native `pg_dump` and scheduled backup jobs should be added.
