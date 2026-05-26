"""
Geospatial utilities for delivery radius matching.

- haversine_distance: Pure math distance calc between two GPS points
- geocode_address: Nominatim API call to convert address → lat/lng
- reverse_geocode: Nominatim API call to convert lat/lng → address
- search_address: Nominatim search for address autocomplete
- filter_by_radius: SQLAlchemy helper to filter rows within a radius
"""

import math
import httpx
from typing import Optional, Tuple
from datetime import datetime, timedelta

# ── Configuration ──────────────────────────────────────────────────────────────
DELIVERY_RADIUS_KM = 10        # Partner sees orders within this range
RESTAURANT_RADIUS_KM = 15     # User sees restaurants within this range
LOCATION_STALE_MINUTES = 10   # Partner location older than this is considered stale
NOMINATIM_TIMEOUT = 5.0       # Seconds before geocoding request times out
USER_AGENT = "FujiSakuraFoodApp/1.0 (delivery platform; contact: admin@fujisakura.com)"


def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate that coordinates are within valid ranges."""
    return -90 <= lat <= 90 and -180 <= lng <= 180


def is_location_stale(location_updated_at: Optional[datetime]) -> bool:
    """Check if a delivery partner's location is too old to be useful."""
    if not location_updated_at:
        return True
    return datetime.now() - location_updated_at > timedelta(minutes=LOCATION_STALE_MINUTES)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth
    using the Haversine formula.

    Args:
        lat1, lon1: Coordinates of point 1 (degrees)
        lat2, lon2: Coordinates of point 2 (degrees)

    Returns:
        Distance in kilometers
    """
    R = 6371.0  # Earth's radius in km

    # Convert to radians
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(dlat / 2) ** 2 + \
        math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def geocode_address(address: str, country_code: str = "in") -> Optional[Tuple[float, float]]:
    """
    Convert a text address to (latitude, longitude) using Nominatim.

    Returns None on any failure — never blocks the calling flow.
    Rate limit: Nominatim allows 1 req/sec.
    """
    if not address or not address.strip():
        return None

    try:
        response = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": address.strip(),
                "format": "json",
                "limit": 1,
                "countrycodes": country_code,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=NOMINATIM_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json()

        if results and len(results) > 0:
            lat = float(results[0]["lat"])
            lon = float(results[0]["lon"])
            if validate_coordinates(lat, lon):
                return (lat, lon)

        return None

    except httpx.TimeoutException:
        return None
    except httpx.HTTPStatusError as e:
        return None
    except Exception as e:
        return None


def reverse_geocode(lat: float, lng: float) -> Optional[dict]:
    """
    Convert (latitude, longitude) to a structured address using Nominatim reverse geocoding.

    Returns dict with: full_address, city, area, state, country
    Returns None on failure.
    """
    if not validate_coordinates(lat, lng):
        return None

    try:
        response = httpx.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lng,
                "format": "json",
                "addressdetails": 1,
                "zoom": 18,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=NOMINATIM_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()

        if not result or "error" in result:
            return None

        address = result.get("address", {})
        
        # Extract city — Nominatim uses different keys depending on location
        city = (
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("county") or
            address.get("state_district") or
            ""
        )
        
        # Extract area/locality
        area = (
            address.get("suburb") or
            address.get("neighbourhood") or
            address.get("locality") or
            address.get("hamlet") or
            ""
        )

        return {
            "full_address": result.get("display_name", ""),
            "city": city,
            "area": area,
            "state": address.get("state", ""),
            "country": address.get("country", ""),
            "postcode": address.get("postcode", ""),
        }

    except httpx.TimeoutException:
        return None
    except httpx.HTTPStatusError as e:
        return None
    except Exception as e:
        return None


def search_address(query: str, country_code: str = "in", limit: int = 5) -> list:
    """
    Search for addresses matching a query string (autocomplete).
    Returns a list of suggestions with display_name, lat, lng.
    """
    if not query or len(query.strip()) < 3:
        return []

    try:
        response = httpx.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query.strip(),
                "format": "json",
                "limit": limit,
                "countrycodes": country_code,
                "addressdetails": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=NOMINATIM_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json()

        suggestions = []
        for r in results:
            lat = float(r["lat"])
            lon = float(r["lon"])
            if not validate_coordinates(lat, lon):
                continue
                
            address = r.get("address", {})
            city = (
                address.get("city") or
                address.get("town") or
                address.get("village") or
                address.get("county") or
                ""
            )
            area = (
                address.get("suburb") or
                address.get("neighbourhood") or
                address.get("locality") or
                ""
            )
            suggestions.append({
                "display_name": r.get("display_name", ""),
                "latitude": lat,
                "longitude": lon,
                "city": city,
                "area": area,
            })

        return suggestions

    except httpx.TimeoutException:
        return []
    except httpx.HTTPStatusError as e:
        return []
    except Exception as e:
        return []


def bounding_box(lat: float, lng: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Calculate a rough bounding box around a point.
    Used as a fast pre-filter before exact Haversine calc.

    Returns (min_lat, max_lat, min_lng, max_lng)
    """
    # 1 degree latitude ≈ 111 km
    lat_delta = radius_km / 111.0
    # 1 degree longitude ≈ 111 * cos(latitude) km
    lng_delta = radius_km / (111.0 * math.cos(math.radians(lat)))

    return (
        lat - lat_delta,
        lat + lat_delta,
        lng - lng_delta,
        lng + lng_delta,
    )


def get_nearby_ids(
    db,
    model_class,
    center_lat: float,
    center_lng: float,
    radius_km: float,
    extra_filters=None,
) -> list[int]:
    """
    Get IDs of rows from `model_class` within `radius_km` of the center point.

    Uses bounding box pre-filter (fast, uses DB indexes) then
    exact Haversine post-filter (accurate).

    Args:
        db: SQLAlchemy session
        model_class: ORM model with .id, .latitude, .longitude columns
        center_lat, center_lng: Center point coordinates
        radius_km: Search radius in kilometers
        extra_filters: Optional list of SQLAlchemy filter conditions

    Returns:
        List of matching row IDs
    """
    min_lat, max_lat, min_lng, max_lng = bounding_box(center_lat, center_lng, radius_km)

    # Build query with bounding box pre-filter
    query = db.query(model_class.id, model_class.latitude, model_class.longitude).filter(
        model_class.latitude.isnot(None),
        model_class.longitude.isnot(None),
        model_class.latitude >= min_lat,
        model_class.latitude <= max_lat,
        model_class.longitude >= min_lng,
        model_class.longitude <= max_lng,
    )

    # Apply any extra filters (e.g. status == 1)
    if extra_filters:
        for f in extra_filters:
            query = query.filter(f)

    candidates = query.all()

    # Post-filter with exact Haversine distance
    result_ids = []
    for row_id, row_lat, row_lng in candidates:
        dist = haversine_distance(center_lat, center_lng, float(row_lat), float(row_lng))
        if dist <= radius_km:
            result_ids.append(row_id)

    return result_ids
