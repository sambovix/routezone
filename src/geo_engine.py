"""Geodetic calculations and transit time estimation engine."""

import math
from typing import Dict, List, Tuple
from config import DEFAULT_OPERATIONAL_CONFIG, OperationalConfig


def haversine_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate great-circle distance between two points on Earth using Haversine formula.

    Args:
        lat1: Latitude of origin in decimal degrees.
        lon1: Longitude of origin in decimal degrees.
        lat2: Latitude of destination in decimal degrees.
        lon2: Longitude of destination in decimal degrees.

    Returns:
        Great-circle distance in kilometers.
    """
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Spherical trigonometry formulation
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_km * c


def estimate_road_distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    circuity_factor: float = DEFAULT_OPERATIONAL_CONFIG.road_circuity_factor,
) -> float:
    """Estimate practical road distance applying terrain circuity factor.

    Args:
        lat1: Origin latitude.
        lon1: Origin longitude.
        lat2: Destination latitude.
        lon2: Destination longitude.
        circuity_factor: Road network detour coefficient over geodesic line.

    Returns:
        Estimated road distance in kilometers.
    """
    direct_km = haversine_distance_km(lat1, lon1, lat2, lon2)
    return direct_km * circuity_factor


def estimate_lead_time_days(
    road_distance_km: float,
    config: OperationalConfig = DEFAULT_OPERATIONAL_CONFIG,
) -> int:
    """Estimate transit duration in integer operational calendar days.

    Args:
        road_distance_km: Road distance between nodes in kilometers.
        config: Operational parameters including truck velocity and driver hours.

    Returns:
        Estimated delivery time in integer days (minimum 1 day).
    """
    daily_capacity_km = config.average_truck_speed_kmh * config.max_driving_hours_per_day
    if daily_capacity_km <= 0:
        raise ValueError("Daily driving capacity must be strictly positive.")

    # Ceiling division to reflect whole-day dispatch and delivery scheduling windows
    return max(1, math.ceil(road_distance_km / daily_capacity_km))


def build_distance_and_lead_time_matrix(
    origins: List[Dict[str, float]],
    destinations: List[Dict[str, float]],
    origin_id_key: str,
    dest_id_key: str,
    config: OperationalConfig = DEFAULT_OPERATIONAL_CONFIG,
) -> Dict[Tuple[str, str], Dict[str, float]]:
    """Compute pairwise road distances and lead times across origin and destination sets.

    Args:
        origins: Origin records containing latitude, longitude, and ID key.
        destinations: Destination records containing latitude, longitude, and ID key.
        origin_id_key: Dictionary key identifying origin nodes.
        dest_id_key: Dictionary key identifying destination nodes.
        config: Operational parameters.

    Returns:
        Dictionary mapping (origin_id, dest_id) to distance_km and lead_time_days.
    """
    matrix: Dict[Tuple[str, str], Dict[str, float]] = {}

    for orig in origins:
        orig_id = str(orig[origin_id_key])
        o_lat = float(orig["latitude"])
        o_lon = float(orig["longitude"])

        for dest in destinations:
            dest_id = str(dest[dest_id_key])
            d_lat = float(dest["latitude"])
            d_lon = float(dest["longitude"])

            road_km = estimate_road_distance_km(
                o_lat, o_lon, d_lat, d_lon, config.road_circuity_factor
            )
            lead_days = estimate_lead_time_days(road_km, config)

            matrix[(orig_id, dest_id)] = {
                "distance_km": round(road_km, 2),
                "lead_time_days": float(lead_days),
            }

    return matrix
