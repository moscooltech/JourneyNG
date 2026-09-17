# WebSocket Protocol

Endpoint: `ws(s)://…/ws/journeys/{journey_id}?token=<access|guest:...>`

## Connection flow

1. Authenticate (JWT or `guest:` prefixed guest token) → `4401` on failure
2. Resolve identity, verify journey membership → `4403` if not a member, `4404` unknown journey
3. Compute per-connection authorized location set:
   - **Host** receives locations of ACTIVE participants with `GRANTED` consent
   - **Visitors** receive no other participants' locations in V1 (spec §12)
4. Send initial authorized snapshot
5. Handle `ping`/`pong`; server pushes events

## Initial snapshot

```json
{
  "type": "journey.snapshot",
  "journey": {"id": "…", "status": "ACTIVE", "destination_name": "…",
               "destination_lat": 6.6018, "destination_lng": 3.3515,
               "expires_at": "…"},
  "participants": [{"id": "…", "role": "VISITOR", "status": "ACTIVE", "display_name": "John", …}],
  "locations": [{"participant_id": "…", "status": "ACTIVE"}]
}
```

Only locations the connection is authorized to view are included.

## Events

- `location.updated` — `{type, journey_id, participant_id, location{latitude, longitude, accuracy_m, speed_mps, heading}, recorded_at, received_at}` — sent **only** to authorized viewers
- `journey.started|completed|cancelled|expired` — channel-wide, no location data
- `participant.joined|accepted|active|arrived|left|removed` — state changes
- `consent.granted|revoked|expired` — sharing relationship changes
- `location.unavailable|restored` — staleness transitions
- `eta.updated`, `route.deviation`, `near_destination` — navigation signals

## Authorization guarantee

The server enforces authorization **before every broadcast**. A participant's location is never broadcast to a connection whose authorized set doesn't include that participant (ADR 0003).

## Reconnection

Clients reconnect with exponential backoff and receive a **fresh snapshot** — no unbounded replay of historical locations.
