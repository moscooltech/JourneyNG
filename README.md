# JourneyNG

[![Backend CI](https://github.com/moscooltech/JourneyNG/actions/workflows/backend.yml/badge.svg)](https://github.com/moscooltech/JourneyNG/actions/workflows/backend.yml)
[![Mobile CI](https://github.com/moscooltech/JourneyNG/actions/workflows/mobile.yml/badge.svg)](https://github.com/moscooltech/JourneyNG/actions/workflows/mobile.yml)
[![Docs Check](https://github.com/moscooltech/JourneyNG/actions/workflows/deploy-docs.yml/badge.svg)](https://github.com/moscooltech/JourneyNG/actions/workflows/deploy-docs.yml)
[![Release](https://github.com/moscooltech/JourneyNG/actions/workflows/release.yml/badge.svg)](https://github.com/moscooltech/JourneyNG/actions/workflows/release.yml)

> **Share your journey, not just your location.**

Consent-based journey sharing: a host creates a journey to a destination, invites visitors, and watches authorized participants travel there in real time — only while each participant explicitly consents.

This is **not** a surveillance or family-tracking app. Sharing is temporary, purpose-bound, and always participant-controlled.

## Repository layout

```
backend/    FastAPI + PostgreSQL + Redis API (Docker, Alembic, WebSocket)
mobile/     Flutter client + native Kotlin Android foreground location service
docs/       Architecture docs, ADRs, privacy/security/deployment guides
.github/    GitHub Actions CI (all builds/tests run in the cloud)
```

## Quick start (local)

```bash
# Backend stack: postgres + redis + api
docker compose up

# API:            http://localhost:8000
# OpenAPI docs:   http://localhost:8000/docs
# Health/ready:   /health  /ready
```

Mobile (needs Flutter SDK + Android tooling, or use CI):

```bash
cd mobile
flutter pub get
flutter run                       # emulator: API at http://10.0.2.2:8000
flutter build apk --debug         # or let GitHub Actions build it
```

## Cloud builds (GitHub Actions)

This project is designed so **no build runs locally** — CI is the build system:

| Workflow | What it does |
|---|---|
| `Backend CI` | ruff lint + format, mypy, pytest (unit/API/security), Alembic migrations against real Postgres, Docker image build, pip-audit |
| `Mobile CI` | flutter analyze, flutter test, Android debug APK artifact |
| `Docs Check` | verifies all required documentation and ADRs exist |

Artifacts (APK, coverage) appear under each run's **Actions** tab. Tagged releases (`v*`) additionally produce a signed-off debug APK attached to a GitHub Release.

## Deployment

### 1. Backend (Docker)

```bash
cd backend
cp .env.example .env         # set JWT_SECRET, DB creds, MAPBOX token
docker compose up -d --build
alembic upgrade head         # inside the api container: docker compose exec api alembic upgrade head
```

For production, deploy the image built by CI to any container host (Fly.io, Render, AWS ECS, a VPS behind Caddy/Nginx). Required env vars are listed in [backend/.env.example](backend/.env.example); database schema is applied with `alembic upgrade head` on deploy (see [docs/deployment.md](docs/deployment.md)).

### 2. Android app

Grab the debug APK from the latest **Mobile CI** run, or build a release APK:

```bash
cd mobile
flutter build apk --release \
  --dart-define=MAPBOX_PUBLIC_TOKEN=pk.your_token
```

Install with `adb install build/app/outputs/flutter-apk/app-release.apk`. Point the app at your backend by editing `mobile/lib/app/config.dart` (`AppConfig.production.apiBaseUrl`) before building.

### 3. Secrets / configuration

| Setting | Where | Notes |
|---|---|---|
| `JWT_SECRET`, DB creds | backend env | never in git; rotate periodically |
| `MAPBOX_PUBLIC_TOKEN` | `--dart-define` at APK build | public token only; server token stays server-side |
| API base URL | `mobile/lib/app/config.dart` | rebuild APK after changing |

## Key invariants (enforced server-side)

1. The participant always knows sharing is active (persistent notification).
2. The participant knows who can see their location (host only, V1).
3. Sharing ends on arrival, expiration, or participant action — automatically.
4. Consent is authorization: no active `GRANTED` consent record ⇒ no location accepted or shown.
5. The server derives identity from tokens; client-supplied IDs are never trusted.
6. Location is journey-scoped, TTL-bounded, and never a permanent history.

See [docs/privacy.md](docs/privacy.md), [docs/security.md](docs/security.md) and the [ADRs](docs/decisions/).
