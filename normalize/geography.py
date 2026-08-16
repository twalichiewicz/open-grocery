from __future__ import annotations

from typing import Any


US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE",
    "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
    "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY",
}


def normalize_state(value: Any) -> str | None:
    if value is None:
        return None

    state = str(value).strip().upper()

    if state in US_STATE_CODES:
        return state

    return state or None


def normalize_postal_code(value: Any) -> str | None:
    if value is None:
        return None

    postal_code = str(value).strip()

    return postal_code or None


def normalize_coordinates(
    latitude: Any,
    longitude: Any,
) -> tuple[float | None, float | None]:
    try:
        lat = float(latitude)
    except (TypeError, ValueError):
        lat = None

    try:
        lon = float(longitude)
    except (TypeError, ValueError):
        lon = None

    if lat is not None and not -90 <= lat <= 90:
        lat = None

    if lon is not None and not -180 <= lon <= 180:
        lon = None

    return lat, lon
