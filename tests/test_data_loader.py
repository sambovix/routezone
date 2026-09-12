"""Unit tests for CSV loading and Pydantic validation."""

from io import StringIO
import pytest
from src.data_loader import (
    load_facilities,
    load_regions,
    load_suppliers,
    synthesize_transport_matrices,
)


def test_load_regions_valid():
    csv_data = StringIO(
        "region_id,region_name,latitude,longitude,demand_units_month\n"
        "R1,Alger,36.75,3.05,50000\n"
    )
    df = load_regions(csv_data)
    assert len(df) == 1
    assert df.iloc[0]["region_id"] == "R1"
    assert df.iloc[0]["demand_units_month"] == 50000.0


def test_load_regions_missing_column():
    csv_data = StringIO("region_id,region_name,latitude\nR1,Alger,36.75\n")
    with pytest.raises(ValueError, match="missing required columns"):
        load_regions(csv_data)


def test_load_regions_invalid_latitude():
    csv_data = StringIO(
        "region_id,region_name,latitude,longitude,demand_units_month\n"
        "R1,Alger,120.0,3.05,50000\n"
    )
    with pytest.raises(ValueError, match="Validation error in regions"):
        load_regions(csv_data)


def test_synthesize_matrices():
    regions = load_regions(StringIO("region_id,region_name,latitude,longitude,demand_units_month\nR1,Alger,36.75,3.05,1000\n"))
    suppliers = load_suppliers(StringIO("supplier_id,supplier_name,latitude,longitude,capacity_units_month\nS1,Port,36.75,3.05,2000\n"))
    facilities = load_facilities(StringIO(
        "facility_id,facility_name,latitude,longitude,fixed_cost_dzd_month,variable_cost_dzd_per_unit,max_capacity_units,is_existing\n"
        "F1,DC,36.75,3.05,10000,1.0,5000,1\n"
    ))

    inbound, outbound, lead_times, distances = synthesize_transport_matrices(
        regions, suppliers, facilities
    )
    assert ("S1", "F1") in inbound
    assert ("F1", "R1") in outbound
    assert ("F1", "R1") in lead_times
