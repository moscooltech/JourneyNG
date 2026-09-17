# ADR 0004: Location Retention

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

The spec forbids permanent GPS history by default while allowing the host to see *current* position live.

## Decision

- **No historical location table exists.** Only `location_latest` (one row per participant) plus Redis live keys with TTL.
- Retention: `LOCATION_RETENTION_HOURS` (default 24) — a cleanup worker deletes older rows; Redis TTLs bound independently.
- On arrival/leave/removal/consent revocation/expiration: sharing stops immediately; no further locations accepted; the latest row stops being refreshed and ages out via retention.
- Analytics/audit never receive raw coordinates.

## Rationale

Data minimization is both a privacy principle and an NDPA-alignment requirement. A single mutable "latest" row gives the live product everything it needs while making history reconstruction structurally impossible.

## Consequences

- Route lines for the visitor rely on the navigation SDK's in-memory route, not server history.
- If an optional consented history feature is added later (spec §63), it requires a new explicit consent scope and a separate retention design.
