# Security

## Authentication

- **Access tokens**: JWT HS256, short-lived, minimal claims (`sub`, `typ`, `iss`, `iat`, `exp`, `jti`).
- **Refresh tokens**: opaque 32-byte random, SHA-256 hashed at rest, rotated on every use, device-scoped. **Reuse of a rotated token revokes the entire family** (theft detection).
- **Passwords**: Argon2id (t=3, m=64 MiB), strength policy enforced server-side.
- **Guest sessions**: journey-scoped random tokens, hashed, expire with the journey, revocable.

## Authorization

- Server-side at every protected resource; identity **always** derived from the presented token — client-supplied `user_id`/`participant_id` is never trusted (IDOR-tested).
- Consent = authorization: location ingestion and host viewing both re-verify an active `GRANTED` record.
- WebSocket connections are authenticated and carry a per-connection authorized set; every broadcast is filtered.

## Transport & headers

HTTPS enforced in production; CORS restricted to configured origins; request IDs on every response.

## Rate limiting (Redis-backed, 429 + retry guidance)

login · register · invitation creation · join redemption · location uploads · WebSocket connects · general API.

## Invitation abuse resistance

Short expiry · revocation · `max_uses` · throttled redemption · only SHA-256 hash stored · raw token never logged.

## Logging rules (enforced in `core/logging.py`)

Never logged: passwords, access/refresh tokens, raw invitation tokens, **raw GPS coordinates**, full notification payloads. Structured JSON logs carry request_id, route, status, duration, safe identifiers.

## Production checklist (spec §57)

See the spec's §57 list — CI enforces lint/type/tests; deployment must verify: no IDOR, consent gating, token hashing, rate limiting, WebSocket auth, HTTPS, CORS, secrets outside repo, dependency audit (pip-audit in CI), backups, deletion/retention tested.
