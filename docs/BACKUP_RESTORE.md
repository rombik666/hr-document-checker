# Резервное копирование и восстановление

Production-сервис: https://hr-checker.ru

Проект: HR Document Checker — прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

## Что входит в backup

Backup включает метаданные документов, метаданные отчётов и санитизированный JSON отчёта.

Backup не включает исходные DOCX/PDF-файлы, raw-текст документов, Hugging Face cache, бинарные FAISS-индексы, `chunks.json`, логи, Docker volumes, SMTP-секреты и `.env`.

## Backup

Локально:

```powershell
python scripts\backup_db.py
```

В Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

На сервере:

```bash
cd ~/apps/hr-document-checker
docker exec -it -w /app hr_doc_checker_app python scripts/backup_db.py
```

Файлы создаются в папке `backups/`.

## Restore

```powershell
python scripts\restore_db.py backups\backup_20260429_010013.json
```

В Docker:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/restore_db.py "backups/backup_20260429_010013.json"
```

## pg_dump для production

```bash
docker exec -t hr_doc_checker_postgres pg_dump -U hr_user -d hr_doc_checker > backups/postgres_dump.sql
```

Восстановление:

```bash
cat backups/postgres_dump.sql | docker exec -i hr_doc_checker_postgres psql -U hr_user -d hr_doc_checker
```

## Рекомендации

Перед обновлением production и перед полным сбросом Docker volumes обязательно создавать резервную копию. Для production-эксплуатации рекомендуется добавить регулярный `pg_dump`, хранение backup вне сервера и проверку восстановления на тестовом окружении.
