# Testing

## Overview

The project includes automated tests for:

- parsers;
- extractors;
- classifiers;
- formal agents;
- semantic agents;
- LLM infrastructure;
- RAG and FAISS;
- report building;
- storage;
- privacy;
- API endpoints;
- web interface;
- metrics;
- backup/restore;
- performance;
- Docker smoke testing.

## Run all tests

```powershell
python -m pytest
```

## Run tests with verbose output

```powershell
python -m pytest -v
```

## Coverage

Generate coverage report:

```powershell
python -m pytest --cov=app --cov-report=term-missing --cov-report=html
```

HTML report:

```text
htmlcov/index.html
```

Generated coverage files are ignored by Git:

```text
htmlcov/
.coverage
coverage.xml
```

## Performance tests

Performance tests are marked with:

```text
performance
```

Run:

```powershell
python -m pytest -m performance
```

## Docker smoke test

Start the environment:

```powershell
.\start.ps1 -NoBuild
```

Run smoke test:

```powershell
.\scripts\smoke_test.ps1
```

The smoke test checks:

- FastAPI health endpoint;
- metrics endpoint;
- Prometheus metrics endpoint;
- RAG status;
- LLM status;
- admin DB status;
- privacy check;
- Web UI;
- Prometheus;
- Grafana;
- pgAdmin.

## Test stability

Real LLM calls are not required for unit tests. Tests use mock LLM clients where needed.

Docker demonstration can use Ollama with:

```text
LLM_PROVIDER=ollama
```
