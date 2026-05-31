# Мониторинг

Production-сервис: https://hr-checker.ru

Проект: HR Document Checker — прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

## Endpoints

```text
GET /api/v1/metrics
GET /api/v1/metrics/prometheus
```

Production:

```text
https://hr-checker.ru/api/v1/metrics
https://hr-checker.ru/api/v1/metrics/prometheus
```

## Prometheus

Prometheus доступен на сервере локально: `http://127.0.0.1:9090`.

SSH-туннель:

```bash
ssh -L 9090:127.0.0.1:9090 deploy@31.76.80.117
```

## Grafana

Grafana доступна локально: `http://127.0.0.1:3000`.

```text
login: admin
password: admin
```

SSH-туннель:

```bash
ssh -L 3000:127.0.0.1:3000 deploy@31.76.80.117
```

## Логи

Логи приложения записываются в `logs/app.log`. Последние логи контейнера:

```bash
docker logs hr_doc_checker_app --tail 100
```

## Что не должно попадать в логи

Raw-текст документа, содержимое файлов, полный текст вакансии, немаскированные e-mail и телефоны, SMTP-пароль, JWT/cookie-секреты.

## Проверка production

```bash
docker ps
sudo nginx -t
sudo systemctl status nginx
docker logs hr_doc_checker_app --tail 100
curl https://hr-checker.ru/api/v1/health
curl https://hr-checker.ru/web/login
```

## Важные метрики

Доступность health endpoint, количество запросов, время обработки, ошибки парсинга, ошибки LLM, ошибки RAG, количество отчётов, статистика Critical/Major/Minor, состояние FAISS-индекса, ошибки SMTP и privacy diagnostics.
