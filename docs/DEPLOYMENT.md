# Развёртывание

Production-сервис: https://hr-checker.ru

Проект: HR Document Checker — прототип системы проверки HR- и бизнес-документов с использованием rule-based проверок, RAG, персональных FAISS-индексов и LLM-агентов.

## Данные production

Домен: `hr-checker.ru`.

IP сервера: `31.76.80.117`.

## Общая схема

```text
Пользователь
↓
https://hr-checker.ru
↓
Nginx
↓
127.0.0.1:8000
↓
Docker container hr_doc_checker_app
↓
PostgreSQL / FAISS index / logs / backups
```

## DNS

DNS-серверы Reg.ru: `ns1.reg.ru`, `ns2.reg.ru`.

A-записи:

```text
A @   → 31.76.80.117
A www → 31.76.80.117
```

Проверка:

```bash
nslookup hr-checker.ru 8.8.8.8
nslookup www.hr-checker.ru 8.8.8.8
```

## Docker Compose

В production приложение и служебные сервисы привязаны к localhost:

```text
app        → 127.0.0.1:8000
pgAdmin    → 127.0.0.1:5050
Prometheus → 127.0.0.1:9090
Grafana    → 127.0.0.1:3000
```

## Переменные окружения

Секреты хранятся в `.env` на сервере. Файл `.env` не должен попадать в Git.

```env
SMTP_PASSWORD=пароль_приложения_яндекс
```

## Запуск на сервере

```bash
cd ~/apps/hr-document-checker
git checkout main
git pull origin main
docker compose down
docker compose up --build -d
```

Проверка:

```bash
docker ps
curl http://127.0.0.1:8000/web/login
```

## Nginx

Файл: `/etc/nginx/sites-available/hr-checker`.

```nginx
server {
    listen 80;
    server_name hr-checker.ru www.hr-checker.ru;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Активация:

```bash
sudo ln -s /etc/nginx/sites-available/hr-checker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## HTTPS

```bash
sudo certbot --nginx -d hr-checker.ru -d www.hr-checker.ru
sudo certbot renew --dry-run
```

## SSH-туннели

```bash
ssh -L 5050:127.0.0.1:5050 deploy@31.76.80.117
ssh -L 3000:127.0.0.1:3000 deploy@31.76.80.117
ssh -L 9090:127.0.0.1:9090 deploy@31.76.80.117
```

## Проверка SMTP

```bash
docker exec -it hr_doc_checker_app python -c "import os; p=os.getenv('SMTP_PASSWORD',''); print('len=', len(p)); print('is_empty=', not bool(p))"
```
