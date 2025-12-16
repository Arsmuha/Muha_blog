# MuhaBlog (FastAPI + Jinja2 + SQLite)

Учебный проект: платформа блога.

## Быстрый запуск (по умолчанию — SQLite)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Открой: http://127.0.0.1:8000

По умолчанию создаётся `blog.db` и наполняется:
- категории
- админ: **admin@blog.com / admin123**

## Возможности

- CRUD постов, комментариев, категорий, пользователей (через `/api/...`)
- HTML-страницы (Jinja2): лента, пост, создание/редактирование, профиль, избранное, поиск пользователей, админ-дашборд
- Лайки/дизлайки, избранное
- Подписки (follow/unfollow)
- Full-text search в SQLite через **FTS5** (`posts_fts`)
- Кэширование результатов поиска (TTLCache)
- Markdown-рендеринг постов
- WebSocket `/ws` (уведомления о новых постах/комментариях)
- PWA (manifest + service worker)
- Метрики Prometheus: `/metrics`

## Миграции (Alembic)

```bash
pip install -r requirements.txt
alembic upgrade head
```

## Тесты + покрытие

```bash
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
```

## Docker

```bash
docker compose up --build
```
