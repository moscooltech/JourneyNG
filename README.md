# JourneyNG

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

Artifacts (APK, coverage) appear under each run's **Actions** tab.

## Key invariants (enforced server-side)

1. The participant always knows sharing is active (persistent notification).
2. The participant knows who can see their location (host only, V1).
3. Sharing ends on arrival, expiration, or participant action — automatically.
4. Consent is authorization: no active `GRANTED` consent record ⇒ no location accepted or shown.
5. The server derives identity from tokens; client-supplied IDs are never trusted.
6. Location is journey-scoped, TTL-bounded, and never a permanent history.

See [docs/privacy.md](docs/privacy.md), [docs/security.md](docs/security.md) and the [ADRs](docs/decisions/).
