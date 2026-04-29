# Architecture

## Общая архитектура

HR Document Checker построен как модульное FastAPI-приложение.

Основной pipeline:

```text
DOCX/PDF
↓
ParserFactory
↓
DOCXParser / PDFParser
↓
ParsedDocument
↓
DocumentTypeClassifier
↓
SectionClassifier
↓
EntityExtractor
↓
FormalCheckCoordinator
↓
SemanticCheckCoordinator + RAG
↓
ReportBuilder
↓
ReportStorageService
↓
API / Web interface