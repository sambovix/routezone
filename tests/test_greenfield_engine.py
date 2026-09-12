"""Unit tests for the Weiszfeld continuous center of gravity algorithm."""

import pandas as pd
import pytest
from src.greenfield_engine import compute_weiszfeld_centroid


def test_weiszfeld_symmetric_points():
    # Symmetric square: centroid must converge exactly to the center (0, 0)
    regions = pd.DataFrame([
        {"region_id": "R1", "region_name": "NE", "latitude": 10.0, "longitude": 10.0, "demand_units_month": 100.0},
        {"region_id": "R2", "region_name": "NW", "latitude": 10.0, "longitude": -10.0, "demand_units_month": 100.0},
        {"region_id": "R3", "region_name": "SE", "latitude": -10.0, "longitude": 10.0, "demand_units_month": 100.0},
        {"region_id": "R4", "region_name": "SW", "latitude": -10.0, "longitude": -10.0, "demand_units_month": 100.0},
    ])
    result = compute_weiszfeld_centroid(regions)
    assert result.optimal_latitude == pytest.approx(0.0, abs=1e-3)
    assert result.optimal_longitude == pytest.approx(0.0, abs=1e-3)


def test_weiszfeld_algeria_data():
    regions = pd.DataFrame([
        {"region_id": "R1", "region_name": "Alger", "latitude": 36.754, "longitude": 3.059, "demand_units_month": 50000.0},
        {"region_id": "R2", "region_name": "Oran", "latitude": 35.733, "longitude": -0.633, "demand_units_month": 30000.0},
        {"region_id": "R3", "region_name": "Constantine", "latitude": 36.365, "longitude": 6.614, "demand_units_month": 20000.0},
    ])
    result = compute_weiszfeld_centroid(regions)
    # Centroid should fall between Oran, Alger, and Constantine (approx lat 36.3-36.8, lon 1.0-4.0)
    assert 35.5 < result.optimal_latitude < 37.0
    assert 0.0 < result.optimal_longitude < 5.0
    assert result.nearest_region_name in ["Alger", "Constantine", "Oran"]


def test_weiszfeld_empty_raises():
    with pytest.raises(ValueError):
        compute_weiszfeld_centroid(pd.DataFrame())
