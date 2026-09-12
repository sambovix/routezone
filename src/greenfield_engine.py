"""Continuous facility location and Weiszfeld center of gravity discovery engine."""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from src.geo_engine import haversine_distance_km


@dataclass
class GreenfieldCentroidResult:
    optimal_latitude: float
    optimal_longitude: float
    weighted_average_distance_km: float
    total_network_demand: float
    iterations_converged: int
    nearest_region_id: str
    nearest_region_name: str
    distance_to_nearest_km: float


def compute_weiszfeld_centroid(
    regions: pd.DataFrame,
    max_iterations: int = 150,
    tolerance: float = 1e-6,
) -> GreenfieldCentroidResult:
    """Find continuous optimal spatial center of gravity using the Weiszfeld algorithm.

    Formulation:
        Min Total Ton-Kilometers = Sum(j) demand_j * distance((lat, lon), (lat_j, lon_j))

    Args:
        regions: Validated demand regions DataFrame.
        max_iterations: Maximum gradient steps for iterative convergence.
        tolerance: Coordinate displacement convergence threshold in degrees.

    Returns:
        GreenfieldCentroidResult dataclass with optimal coordinates.

    Raises:
        ValueError: If regions DataFrame is empty or demand is non-positive.
    """
    if regions.empty:
        raise ValueError("Regions DataFrame cannot be empty for centroid analysis.")

    lats = regions["latitude"].to_numpy(dtype=float)
    lons = regions["longitude"].to_numpy(dtype=float)
    weights = regions["demand_units_month"].to_numpy(dtype=float)
    total_weight = float(weights.sum())

    if total_weight <= 0.0:
        raise ValueError("Total demand volume must be strictly positive.")

    # Initial anchor: demand-weighted barycenter
    curr_lat = float((weights * lats).sum() / total_weight)
    curr_lon = float((weights * lons).sum() / total_weight)

    iterations_run = 0
    eps = 1e-5

    for iteration in range(1, max_iterations + 1):
        num_lat = 0.0
        num_lon = 0.0
        denom = 0.0

        for lat_j, lon_j, w_j in zip(lats, lons, weights):
            # Geodesic Euclidean approximation in planar local metric
            d = math.hypot(curr_lat - lat_j, curr_lon - lon_j)
            if d < eps:
                d = eps
            inv_d = w_j / d
            num_lat += inv_d * lat_j
            num_lon += inv_d * lon_j
            denom += inv_d

        if denom == 0.0:
            break

        next_lat = num_lat / denom
        next_lon = num_lon / denom

        shift = math.hypot(next_lat - curr_lat, next_lon - curr_lon)
        curr_lat = next_lat
        curr_lon = next_lon
        iterations_run = iteration

        if shift < tolerance:
            break

    # Calculate weighted average transport distance to customer markets
    weighted_dist_sum = sum(
        float(w) * haversine_distance_km(curr_lat, curr_lon, float(la), float(lo))
        for la, lo, w in zip(lats, lons, weights)
    )
    avg_dist = weighted_dist_sum / total_weight

    # Identify closest administrative market
    closest_r_id = ""
    closest_r_name = ""
    min_d = float("inf")

    for _, r in regions.iterrows():
        d = haversine_distance_km(curr_lat, curr_lon, float(r["latitude"]), float(r["longitude"]))
        if d < min_d:
            min_d = d
            closest_r_id = str(r["region_id"])
            closest_r_name = str(r["region_name"])

    return GreenfieldCentroidResult(
        optimal_latitude=round(curr_lat, 4),
        optimal_longitude=round(curr_lon, 4),
        weighted_average_distance_km=round(avg_dist, 2),
        total_network_demand=round(total_weight, 2),
        iterations_converged=iterations_run,
        nearest_region_id=closest_r_id,
        nearest_region_name=closest_r_name,
        distance_to_nearest_km=round(min_d, 2),
    )
