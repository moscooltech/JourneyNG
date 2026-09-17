# API Reference

Base URL: `/api/v1` · Interactive docs: `/docs` (OpenAPI 3.1 via FastAPI).

All protected endpoints require `Authorization: Bearer <access_token>`, or `X-Guest-Token: <token>` for guest-scoped actions.

## Error envelope

```json
{
  "error": {
    "code": "JOURNEY_NOT_ACTIVE",
    "message": "The journey is not active.",
    "request_id": "…"
  }
}
```

Internal exception traces are never exposed.

## Authentication

| Method | Path | Notes |
|---|---|---|
| POST | `/auth/register` | `{display_name, email, phone?, password}` → user + token pair. 409 `EMAIL_TAKEN`, 422 `WEAK_PASSWORD` |
| POST | `/auth/login` | `{identifier, password}` (email; phone ready) → token pair |
| POST | `/auth/refresh` | `{refresh_token}` → **rotated** pair. Reuse of a rotated token revokes the whole family |
| POST | `/auth/logout` | Revokes the presented refresh token |

## Users

| Method | Path | Notes |
|---|---|---|
| GET | `/me` | Profile + account metadata |
| PATCH | `/me` | Update display name / photo |
| DELETE | `/me` | 202 accepted — deactivation workflow (spec §30) |

## Journeys

| Method | Path | Authorization |
|---|---|---|
| POST | `/journeys` | Registered host. Creates journey `INVITED` + host participant |
| GET | `/journeys` | Journeys where user is host or participant |
| GET | `/journeys/{id}` | Host or participant (guest: own journey only) |
| POST | `/journeys/{id}/start` | Host-only. `INVITED → ACTIVE` |
| POST | `/journeys/{id}/cancel` | Host-only |
| POST | `/journeys/{id}/complete` | Host-only. Revokes all active sharing |

## Invitations

| Method | Path | Notes |
|---|---|---|
| POST | `/journeys/{id}/invitations` | Host-only. `{max_uses?, expires_in_minutes}` → `{invitation_id, invite_url, expires_at}`. Raw token never stored server-side |
| POST | `/journeys/{id}/invitations/{iid}/revoke` | Host-only |
| POST | `/join/{token}/guest` | `{display_name}` → guest session (journey-scoped, hashed) + participant |
| POST | `/join/{token}/accept` | Registered user accepts |
| POST | `/join/{token}/decline` | Marks participant `DECLINED` |

## Consent & participants

| Method | Path | Notes |
|---|---|---|
| POST | `/journeys/{id}/consent` | Grants `LIVE_LOCATION` for `TRAVEL_TO_DESTINATION`, viewer = host |
| POST | `/journeys/{id}/consent/revoke` | Participant revokes own sharing |
| GET | `/journeys/{id}/consent` | Own consent records only |
| POST | `/journeys/{id}/participants/me/start` | Requires consent granted + accepted state |
| POST | `/journeys/{id}/participants/me/leave` | Terminal `LEFT` |
| POST | `/journeys/{id}/participants/me/arrive` | `ARRIVED`; consent revoked; sharing stops |
| POST | `/journeys/{id}/participants/{pid}/remove` | Host-only |

## Location

| Method | Path | Notes |
|---|---|---|
| POST | `/journeys/{id}/location` | Identity **derived from auth**; never client-supplied. Validates: membership, ACTIVE, consent GRANTED, journey ACTIVE, coordinates, timestamp, rate limit → `{accepted, server_received_at, server_sequence}` |
| GET | `/journeys/{id}/locations` | Host-only (V1). Authorized ACTIVE participants with freshness `LIVE/STALE/OFFLINE`. No history |

## Privacy

| Method | Path | Notes |
|---|---|---|
| GET | `/privacy/active-sharing` | Who can see me, why, until when |
| POST | `/privacy/stop-all-sharing` | Revokes all active consents immediately |

## Health

`GET /health` liveness · `GET /ready` checks Postgres (fail) and Redis (degraded).

## Rate limiting

Redis-backed per scope (login, register, invitations, join, location, WebSocket). Exceeded → `429` with `RATE_LIMITED`.
