# User guide

## Purpose

This guide describes how to use HR Document Checker through the web interface.

## Start the system

```powershell
.\start.ps1 -NoBuild
```

Open:

```text
http://127.0.0.1:8000/web/
```

## Generate a report

1. Open the web interface.
2. Upload a DOCX or PDF document.
3. Optionally paste vacancy text.
4. Select storage mode.
5. Click the report generation button.
6. Review the generated report.

## Storage modes

| Mode | Description |
|---|---|
| `temporary` | Saves sanitized report and metadata |
| `metadata_only` | Saves limited metadata/report information |
| `no_store` | Does not persist report in DB |

## Report structure

The report includes:

- summary status;
- total number of issues;
- Critical issues;
- Major issues;
- Minor issues;
- recommendations;
- evidence fragments;
- vacancy relevance;
- technical information.

## DOCX export

If the report is saved, DOCX export is available through:

```text
GET /api/v1/documents/reports/{report_id}/export/docx
```

## Privacy

The system masks personal data before long-term storage.

The database should not contain:

- raw document text;
- original uploaded files;
- unmasked e-mails;
- unmasked phones.

Privacy check:

```text
http://127.0.0.1:8000/api/v1/admin/storage/privacy-check
```

## RAG and LLM

RAG status:

```text
http://127.0.0.1:8000/api/v1/rag/status
```

LLM status:

```text
http://127.0.0.1:8000/api/v1/llm/status
```

## Stop the system

```powershell
.\stop.ps1
```
