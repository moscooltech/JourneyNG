# Deployment

## Environments (spec §49)

development · staging · production — each with separate Postgres, Redis, API URL, Mapbox config, FCM config, and secrets. Staging can never reach production datastores.

## Render-style deployment

1. **PostgreSQL** managed instance → `DATABASE_URL`
2. **Redis/Valkey** managed instance → `REDIS_URL`
3. **API** — Docker service from `backend/Dockerfile`:
   - build: CI produces the image (Backend CI workflow)
   - start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - health check: `/health`
4. **Workers** — two small services running:
   - `python -m app.workers.expiry_worker` (journey/consent expiration)
   - `python -m app.workers.cleanup_worker` (location retention)

## Required environment (spec §47)

Set via provider secret management — never committed:

```
APP_ENV, DATABASE_URL, REDIS_URL,
JWT_SECRET (32+ random chars; REQUIRED in production — server refuses to boot without it),
JWT_ACCESS_EXPIRES_MINUTES, JWT_REFRESH_EXPIRES_DAYS,
CORS_ORIGINS, MAPBOX_SERVER_TOKEN,
FCM_PROJECT_ID, FCM_CLIENT_EMAIL, FCM_PRIVATE_KEY,
SENTRY_DSN (optional)
```

## Mobile release

- Debug APK built by Mobile CI (artifact). Release builds require a signing config supplied via GitHub Secrets / local keystore **outside** the repository.
- Mapbox public token injected with `--dart-define=MAPBOX_PUBLIC_TOKEN=…` (public token only; server secrets never ship in apps).

## Local development

```bash
docker compose up   # postgres + redis + api (auto-migrates)
```
