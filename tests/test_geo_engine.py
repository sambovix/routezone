"""Unit tests for geodetic distance and transit time calculations."""

import pytest
from src.geo_engine import (
    estimate_lead_time_days,
    estimate_road_distance_km,
    haversine_distance_km,
)


def test_haversine_distance_known_coordinates():
    # Alger (36.7538, 3.0588) to Oran (35.7333, -0.6333) is approximately 350-370 km direct
    dist = haversine_distance_km(36.7538, 3.0588, 35.7333, -0.6333)
    assert 340.0 < dist < 380.0


def test_haversine_same_point_is_zero():
    dist = haversine_distance_km(36.7538, 3.0588, 36.7538, 3.0588)
    assert dist == pytest.approx(0.0, abs=1e-4)


def test_road_distance_applies_circuity():
    direct = haversine_distance_km(36.7538, 3.0588, 35.7333, -0.6333)
    road = estimate_road_distance_km(36.7538, 3.0588, 35.7333, -0.6333, circuity_factor=1.25)
    assert road == pytest.approx(direct * 1.25, rel=1e-4)


def test_estimate_lead_time_days():
    # 480 km at 60 km/h and 8h/day is 480 km/day -> exactly 1 day
    assert estimate_lead_time_days(480.0) == 1
    # 500 km exceeds 1 day driving limit -> 2 days
    assert estimate_lead_time_days(500.0) == 2
    # Short distances should always be at least 1 day
    assert estimate_lead_time_days(10.0) == 1


def test_estimate_lead_time_invalid_capacity():
    from config import OperationalConfig
    invalid_config = OperationalConfig(average_truck_speed_kmh=0.0)
    with pytest.raises(ValueError):
        estimate_lead_time_days(100.0, invalid_config)
