# ADR 0002: Multi-Participant Journey Model

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

A host invites one or more visitors. Each visitor independently accepts, consents, starts, stops, arrives, leaves. V1 caps active participants at 10–20 (configurable).

## Decision

- One host per journey (represented both as `journeys.host_user_id` **and** a `HOST` row in `journey_participants` — preferred implementation so all participant operations use one model).
- Visitors are rows in `journey_participants` with **exactly one identity source**: `user_id` XOR `guest_session_id` (enforced by DB CHECK constraint).
- Arrival, consent, and sharing are **per-participant**: one participant arriving never stops others.
- Journey completes when all visitors reached terminal/ARRIVED states.

## Rationale

The host participant row unifies membership queries and authorization. The XOR constraint makes dual-identity bugs impossible at the storage layer. Independent state machines prevent cascade surprises.

## Consequences

- Group invitations need `max_uses > 1` tokens; each redemption creates an independent participant.
- Journey-level status never encodes arrival (spec §7.5) — derived from participant states by `maybe_complete_journey`.
