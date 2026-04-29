# Monitoring

## Purpose

Monitoring is used to observe application health, request processing and document checking metrics.

The project includes:

- JSON metrics endpoint;
- Prometheus metrics endpoint;
- Prometheus service;
- Grafana service;
- persistent application logs.

## Endpoints

### JSON metrics

```text
GET /api/v1/metrics
```

### Prometheus metrics

```text
GET /api/v1/metrics/prometheus
```

## Prometheus

Prometheus is available at:

```text
http://127.0.0.1:9090
```

Prometheus scrapes:

```text
http://app:8000/api/v1/metrics/prometheus
```

## Grafana

Grafana is available at:

```text
http://127.0.0.1:3000
```

Credentials:

```text
login: admin
password: admin
```

## Application logs

Logs are written to:

```text
logs/app.log
```

The `logs/` folder is ignored by Git except `.gitkeep`.

## Request logging

The application logs:

- request ID;
- HTTP method;
- path;
- status code;
- duration.

The application does not log:

- raw document text;
- uploaded file content;
- vacancy text;
- unmasked e-mail;
- unmasked phone.

## Noisy endpoints

Prometheus polling endpoint is excluded from regular request INFO logs:

```text
/api/v1/metrics/prometheus
```

This prevents log flooding.
