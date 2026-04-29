# Admin guide

## Назначение

Административный слой демонстрирует роль администратора системы.

Он используется для:

- проверки состояния приложения;
- просмотра демонстрационных ролей;
- диагностики базы данных;
- проверки privacy/storage требований;
- доступа к метрикам;
- контроля RAG/LLM состояния;
- демонстрации PostgreSQL через pgAdmin.

## Роли

| Роль | Назначение |
|---|---|
| `candidate` | Загружает документы и получает отчёт |
| `hr` | Проверяет документы кандидатов и анализирует отчёты |
| `admin` | Контролирует правила, агентов, RAG, метрики, backup/restore и документацию |

Полноценная авторизация пользователей не входит в MVP. Роли реализованы как демонстрационный административный слой и отражены в API/documentation.

## Admin endpoints

```text
GET /api/v1/admin/status
GET /api/v1/admin/roles
GET /api/v1/admin/db/status
GET /api/v1/admin/storage/privacy-check
```

## Related endpoints

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
GET /api/v1/rag/status
GET /api/v1/llm/status
GET /api/v1/documents/reports/{report_id}
```

## pgAdmin

pgAdmin доступен по адресу:

```text
http://127.0.0.1:5050
```

Данные входа:

```text
Email: admin@example.com
Password: admin
```

Подключение к PostgreSQL:

```text
Host: postgres
Port: 5432
Database: hr_doc_checker
Username: hr_user
Password: hr_password
```

## Что проверять в БД

Таблицы:

- `documents`;
- `reports`.

В долгосрочном хранилище не должны храниться:

- исходные DOCX/PDF-файлы;
- полный `raw_text` документа;
- открытые e-mail;
- открытые телефоны.

Проверка privacy доступна через endpoint:

```text
GET /api/v1/admin/storage/privacy-check
```
