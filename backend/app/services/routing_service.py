"""Routing provider abstraction (spec §55).

Domain code depends on RoutingProvider; Mapbox is one adapter. Future
adapters (OSRM, Google, HERE) plug in without touching domain logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class RoutePoint:
    latitude: float
    longitude: float


@dataclass(frozen=True)
class RouteResult:
    distance_m: float
    duration_s: float
    geometry: list[RoutePoint]


class RoutingProvider(Protocol):
    async def calculate_route(self, origin: RoutePoint, destination: RoutePoint) -> RouteResult: ...


class MapboxRoutingProvider:
    """Mapbox Directions adapter. Gracefully unavailable without a token."""

    BASE_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic"

    async def calculate_route(self, origin: RoutePoint, destination: RoutePoint) -> RouteResult:
        settings = get_settings()
        if not settings.mapbox_server_token:
            raise RuntimeError("Mapbox server token not configured")

        coords = (
            f"{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}"
        )
        url = f"{self.BASE_URL}/{coords}"
        params = {
            "overview": "simplified",
            "geometries": "geojson",
            "access_token": settings.mapbox_server_token,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        route = data["routes"][0]
        geometry = [
            RoutePoint(latitude=lat, longitude=lng) for lng, lat in route["geometry"]["coordinates"]
        ]
        return RouteResult(
            distance_m=float(route["distance"]),
            duration_s=float(route["duration"]),
            geometry=geometry,
        )


class UnavailableRoutingProvider:
    """Fallback when no provider is configured — ETA marked unavailable."""

    async def calculate_route(self, origin: RoutePoint, destination: RoutePoint) -> RouteResult:
        raise RuntimeError("Routing provider unavailable")


def get_routing_provider() -> RoutingProvider:
    if get_settings().mapbox_server_token:
        return MapboxRoutingProvider()
    return UnavailableRoutingProvider()
