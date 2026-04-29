# Compliance matrix

| Блок ТЗ/отчёта | Реализация | Статус |
|---|---|---|
| API и Web UI | FastAPI, `/web/`, Swagger | Выполнено |
| DOCX/PDF | parsers | Выполнено |
| Сущности | extractors | Выполнено |
| Формальные проверки | formal agents | Выполнено |
| Семантические проверки | semantic agents | Выполнено |
| RAG | app/rag, vector store | Выполнено |
| LLM interface | app/llm | Выполнено архитектурно |
| Агент-координатор | coordinators | Выполнено |
| Отчёт | ReportBuilder | Выполнено |
| Critical/Major/Minor | schemas/reports/checks | Выполнено |
| Evidence/recommendations | Issue/Recommendation | Выполнено |
| Хранение | SQLAlchemy, PostgreSQL/SQLite | Выполнено |
| Безопасность | no_store, masking, no raw_text | Выполнено |
| Docker | Dockerfile, docker-compose | Выполнено |
| Monitoring | Prometheus/Grafana | Выполнено |
| Backup/restore | scripts | Выполнено |
| Документация | docs/ | Выполнено |
| Тестирование | tests/ | Выполнено |
