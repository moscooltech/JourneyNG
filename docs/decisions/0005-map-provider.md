# ADR 0005: Map Provider Abstraction

- **Status:** Accepted
- **Date:** 2026-09-17

## Context

Mapbox is the initial provider (maps, routing, navigation), but pricing/terms change and alternative providers (OSRM, Google, HERE) may be needed — especially for Nigerian road-coverage testing (Lagos, Abuja, PH, Ibadan).

## Decision

- Domain-level interfaces: `MapProvider`, `RoutingProvider`, `NavigationProvider`, `GeocodingProvider` (backend: `services/routing_service.py`; mobile: adapter layer around `mapbox_maps_flutter`).
- Mapbox is one adapter. No Mapbox SDK object leaks into domain/business models.
- Server holds `MAPBOX_SERVER_TOKEN`; mobile ships only the public token via `--dart-define`.
- Unavailable provider ⇒ ETA "unavailable", location sharing continues (graceful degradation).

## Rationale

The spec mandates this abstraction (§55). Provider lock-in is a commercial and technical risk; routing quality in target cities must be validated empirically before committing.

## Consequences

- Slight indirection cost; interfaces stay minimal (calculateRoute, reroute, geocode).
- Before production: routing/ETA/address-search quality tested in Lagos Island, Ikeja, Alagbado, Agege, Yaba, Lekki, Surulere, Oshodi, Ikorodu, Abuja, Port Harcourt, Ibadan.
