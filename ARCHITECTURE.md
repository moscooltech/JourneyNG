# Architecture

## High-level

```
Flutter (Android)
   │  HTTPS (REST)          WebSocket (/ws/journeys/{id})
   ▼
FastAPI
   ├── PostgreSQL  — durable state (users, journeys, participants, consents)
   ├── Redis/Valkey— live state (latest location, presence, rate limits; TTL everywhere)
   ├── FCM         — push notifications (no GPS in payloads)
   └── Mapbox      — maps/routing via provider abstraction
```

## Layering rules

- **UI never calls HTTP/DB/platform directly.** Flutter: widgets → notifiers → repositories → ApiClient. Backend: routers → services → repositories/models.
- **The backend owns authorization and sharing relationships.** The client never decides who sees location.
- **Mapbox specifics stay in adapters.** Domain code uses `RoutingProvider` / `MapProvider` interfaces (ADR 0005).

## Journey data flow (spec §51)

1. Host `POST /journeys` → journey `INVITED`, host participant row created.
2. Host `POST /journeys/{id}/invitations` → raw token only in the URL; DB stores SHA-256 hash.
3. Visitor opens deep link `/join/<token>` → accepts (registered) or guest session (scoped, hashed).
4. Visitor grants consent → `location_consents` row (`GRANTED`, viewer = host, expires with journey/arrival).
5. Visitor `POST /participants/me/start` → participant `ACTIVE`.
6. Kotlin `JourneyLocationService` (foreground) → movement-aware GPS → `POST /location`.
7. Ingestion pipeline re-verifies: membership → ACTIVE → consent GRANTED → journey ACTIVE → payload sanity → rate limit → Redis (TTL) + `location_latest`.
8. WebSocket broadcasts only to connections whose authorized set includes that participant.
9. Arrival (manual or geofence) → participant `ARRIVED`, consent revoked, service stops, others unaffected.
10. Journey completes when host ends it, it expires, or all visitors reached a terminal state.

## State machines

Journey: `DRAFT → INVITED → ACTIVE → COMPLETED/CANCELLED/EXPIRED` (no reactivation from terminal states).
Participant: `INVITED → ACCEPTED → ACTIVE → ARRIVED/LEFT/REMOVED/EXPIRED`.
Consent: `GRANTED → REVOKED/EXPIRED`; absence of consent = no access.

## Live location freshness

- `LIVE` — recent update within threshold
- `STALE` — no recent update, participant still ACTIVE (host sees "last updated")
- `OFFLINE` — beyond threshold; markers never fake liveness

## Degradation

- Redis down: ingestion persists to Postgres, live propagation pauses, `/ready` reports degraded. Never falsely claim live delivery.
- Routing provider down: ETA shows "unavailable", location sharing continues.

## Detailed docs

- API: [docs/api.md](api.md) · WebSocket: [docs/websocket.md](websocket.md)
- Database: [docs/database.md](database.md) · Android location: [docs/android-location.md](android-location.md)
- Maps: [docs/maps-navigation.md](maps-navigation.md)
