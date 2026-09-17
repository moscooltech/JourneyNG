# ADR 0001: Technology Stack

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

Android-first product (Nigerian market initial validation) needing real-time consent-based location sharing, with a solo/small team and cloud-only builds (GitHub Actions).

## Decision

- **Mobile:** Flutter + Dart, Riverpod state management, GoRouter navigation, native Kotlin foreground service via platform channels/EventChannel, `flutter_secure_storage` for tokens.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic, PostgreSQL, Redis/Valkey, WebSockets, JWT + rotating refresh tokens, Argon2id.
- **Infra:** Docker + docker-compose, GitHub Actions CI, Render-compatible deployment, environment-based config.

## Rationale

- Flutter gives the fastest path to a polished Android app with a single codebase and easy native interop for the location service.
- FastAPI's async model fits WebSocket + high-frequency location ingestion; Pydantic gives contract safety shared with mobile models.
- PostgreSQL for durable relational state with strong constraints (XOR participant identity); Redis for TTL-bounded live state — never source of truth.
- Argon2id is the current password-hashing recommendation (PHC winner).

## Consequences

- Two runtimes to maintain; mitigated by typed contracts (OpenAPI + generated docs).
- WebSocket scaling requires a pub/sub story when horizontally scaling (Redis pub/sub is the natural next step; single-instance V1 acceptable).
