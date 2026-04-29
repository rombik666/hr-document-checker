# Demo scenario

## Goal

Demonstrate a full document checking cycle:

```text
start system
↓
open Web UI
↓
upload DOCX
↓
enter vacancy text
↓
run report generation
↓
inspect report
↓
export DOCX
↓
check RAG/LLM/Admin/metrics
```

## 1. Start the system

```powershell
.\start.ps1 -NoBuild
```

Open:

```text
http://127.0.0.1:8000/web/
```

## 2. Check infrastructure

Open:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/api/v1/health
http://127.0.0.1:8000/api/v1/rag/status
http://127.0.0.1:8000/api/v1/llm/status
http://127.0.0.1:3000
http://127.0.0.1:5050
```

## 3. Upload document

Use a demo DOCX or create a simple resume with:

- contacts;
- skills;
- work experience;
- education.

## 4. Vacancy text

Example:

```text
Требования: Python, FastAPI, PostgreSQL, Docker, Git, REST API, Linux.
```

## 5. Generate report

Select storage mode:

```text
temporary
```

Run the check.

Expected result:

- HTML report is displayed;
- report status is shown;
- Critical/Major/Minor sections are present;
- recommendations are generated;
- `report_id` is created;
- JSON link is available;
- DOCX export link is available.

## 6. Check LLM agent

In raw check results, verify that the following agent appears when enabled:

```text
LlmSemanticAgent
```

## 7. Check RAG

Open:

```text
http://127.0.0.1:8000/api/v1/rag/status
```

Expected:

```json
{
  "retriever_type": "faiss",
  "index_exists": true
}
```

If index does not exist:

```powershell
docker exec -it -w /app hr_doc_checker_app python scripts/build_rag_index.py
```

## 8. Check privacy

Open:

```text
http://127.0.0.1:8000/api/v1/admin/storage/privacy-check
```

Expected:

```json
{
  "passed": true,
  "unmasked_email_count": 0,
  "unmasked_phone_count": 0
}
```

## 9. Run smoke test

```powershell
.\scripts\smoke_test.ps1
```

Expected:

```text
[OK] Smoke test completed successfully.
```

## 10. Stop the system

```powershell
.\stop.ps1
```
