# Database

PostgreSQL 16 · UUID PKs · UTC timezone-aware timestamps · Alembic migrations.

## Tables

| Table | Purpose | Notable constraints |
|---|---|---|
| `users` | Accounts | email/phone UNIQUE (normalized); status `ACTIVE/SUSPENDED/DELETED`; never expose `password_hash` |
| `profiles` | Display data | 1:1 with users |
| `refresh_tokens` | Sessions | SHA-256 **hash only**; `revoked_at` for rotation; reuse ⇒ family revocation |
| `guest_sessions` | Journey-scoped guests | token hash UNIQUE; status `ACTIVE/EXPIRED/REVOKED/COMPLETED` |
| `journeys` | Trips | status machine `INVITED→ACTIVE→COMPLETED/CANCELLED/EXPIRED`; `expires_at` NOT NULL |
| `journey_participants` | Membership | **CHECK: user_id XOR guest_session_id**; roles `HOST/VISITOR`; status machine |
| `journey_invitations` | Invite links | token_hash UNIQUE; `max_uses`/`use_count`; `expires_at`; revocable |
| `location_consents` | Authorization | purpose `TRAVEL_TO_DESTINATION`, scope `LIVE_LOCATION`, status `GRANTED/REVOKED/EXPIRED`; viewer = host (V1) |
| `location_latest` | Current position | one row per participant; **temporary** (retention worker deletes) |
| `devices` | Push tokens | protected |
| `notifications` | In-app inbox | **no raw GPS** in payloads |
| `audit_logs` | Sensitive actions | **no raw GPS, tokens or credentials** |
| `privacy_settings` | User prefs | analytics flags (never override legal logging) |
| `trusted_contacts` | Future feature | table exists, no UI in V1 |

## Indexes (spec §8)

- `users(email)`, `users(phone)`
- `journeys(host_user_id, created_at DESC)`, `journeys(status, expires_at)`
- `journey_participants(journey_id, status)`, `(user_id)`, `(guest_session_id)`
- `journey_invitations(token_hash)`, `(journey_id, expires_at)`
- `location_consents(participant_id, status)`, `(viewer_user_id, status)`
- `location_latest(journey_id)`
- `notifications(user_id, created_at DESC)`
- `audit_logs(resource_type, resource_id, created_at DESC)`

## Source of truth

PostgreSQL is durable truth. Redis holds only TTL-bounded live state (`journey:{id}:participant:{pid}:location` etc.) and is safe to lose.

## Retention

`location_latest` rows older than `LOCATION_RETENTION_HOURS` are deleted by the cleanup worker. No historical GPS table exists.
