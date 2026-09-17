# ADR 0003: Consent Model

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

Location sharing must be explicit, purpose-bound, revocable, and verifiable server-side. "No active consent" must equal "no location access" with no exceptions.

## Decision

- Consent is stored as a first-class row (`location_consents`): purpose, scope, viewer, granted/expires timestamps, version.
- **Viewer is the journey host in V1.** Arbitrary viewers are not permitted yet.
- Duration `UNTIL_ARRIVAL` maps consent expiry to the journey expiry; arrival revokes immediately.
- Consent is re-verified on **every** ingestion path (`require_active_consent`) and at WebSocket authorization — not cached across requests.
- Grant/revocation transitions follow the state machine (`GRANTED → REVOKED/EXPIRED`); absence or expiry raises `CONSENT_REQUIRED`/`CONSENT_REVOKED` (403).

## Rationale

Treating consent as an authorization state (not a UI preference) makes the privacy invariant mechanically enforceable and testable. The spec's rule 6 — "The backend enforces these rules" — is satisfied by making the consent check a hard gate in the ingestion pipeline.

## Consequences

- Slight per-update overhead (one indexed lookup) — acceptable at V1 scale.
- Future features (trusted contacts, extra viewers) extend the viewer model without changing the ingestion gate.
