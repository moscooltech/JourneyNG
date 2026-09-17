# ADR 0006: Android Foreground Service Architecture

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

Location sharing must survive screen lock, Home, and app switching, while respecting strict Android background restrictions and Play policy. Covert/background starts are prohibited by the spec.

## Decision

- Native Kotlin `JourneyLocationService` with `foregroundServiceType="location"`, started **only** from the visible START JOURNEY action.
- **while-in-use** location permission only; no `ACCESS_BACKGROUND_LOCATION` request in V1.
- Persistent transparency notification ("Your location is being shared with …") with View Journey / Stop Sharing actions; removed when sharing stops.
- `START_NOT_STICKY`: process death never silently resumes sharing; the backend marks the participant stale instead.
- Permission revoked mid-journey ⇒ service stops safely; client never claims success when the service isn't running.
- Fused Location Provider with movement-aware intervals (≈4–15 s per spec §14).

## Rationale

Android 10–16 foreground-service rules (type declaration, `FOREGROUND_SERVICE_LOCATION`, notification requirements) make the foreground-service-with-visible-action pattern the only policy-compliant architecture for this UX. `START_NOT_STICKY` plus server-side staleness keeps the host view honest after OS kills.

## Consequences

- OEM battery optimization can still kill the service — mitigated by honest STALE/OFFLINE UI states and recovery instructions, not bypasses (spec §54 forbids bypassing Android security).
- Android version changes require re-verification against current official docs and Play policy at release time (spec §62).
