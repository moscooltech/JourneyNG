# Android Location

## Architecture

```
Flutter UI (START JOURNEY — always a visible user action)
  → MethodChannel journey/location_service
  → JourneyLocationService (foreground, foregroundServiceType="location")
  → FusedLocationProviderClient (movement-aware interval)
  → EventChannel journey/location_events
  → LocationSharingController (validation + throttled upload)
  → POST /journeys/{id}/location
```

## Permissions (verify current Android docs at implementation time)

Manifest declares:
- `ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`
- `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_LOCATION`
- `POST_NOTIFICATIONS` (Android 13+ runtime)

The service declares `android:foregroundServiceType="location"`. V1 uses **while-in-use** permission only — no `ACCESS_BACKGROUND_LOCATION` request (spec §18).

## Foreground notification (transparency feature)

> **Journey active** — Your location is being shared with Babatunde.

Actions: **View Journey** · **Stop Sharing**. Removed the moment sharing stops.

## Movement-aware intervals (spec §14)

| State | Interval |
|---|---|
| Moving fast (>8 m/s) | ~4 s |
| Normal movement | ~6 s |
| Stationary/slow | ~15 s |

Intervals are starting values; the server policy and real-device testing tune them.

## Handled failure modes (spec §15, §31)

Permission denied/revoked → service stops safely, UI explains. Location services off → clear guidance. Network lost → GPS may continue, uploads pause, host sees STALE with last-updated time, no backlog on reconnect (latest wins). Battery saver/OEM kills → backend marks location stale; never fake liveness; no prohibited background starts. App killed → `START_NOT_STICKY` prevents zombie sharing; participant is marked stale server-side.

**The client never claims sharing is active unless the service is actually running.**

## Device test matrix (spec §38)

Android 10–16; permission granted/approximate/denied/revoked; screen on/off; background; battery saver; poor/no network; process death; restart; OEM battery optimization; multiple manufacturers (not emulator-only).
