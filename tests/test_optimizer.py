"""Unit tests for the two-echelon MILP facility location optimizer."""

import pandas as pd
import pytest
from src.optimizer import solve_facility_location


@pytest.fixture
def small_network():
    regions = pd.DataFrame([
        {"region_id": "R1", "region_name": "Alger", "latitude": 36.75, "longitude": 3.05, "demand_units_month": 1000.0},
        {"region_id": "R2", "region_name": "Oran", "latitude": 35.73, "longitude": -0.63, "demand_units_month": 500.0},
    ])
    suppliers = pd.DataFrame([
        {"supplier_id": "S1", "supplier_name": "Port Alger", "latitude": 36.75, "longitude": 3.05, "capacity_units_month": 5000.0}
    ])
    facilities = pd.DataFrame([
        {
            "facility_id": "F1",
            "facility_name": "DC Alger",
            "latitude": 36.75,
            "longitude": 3.05,
            "fixed_cost_dzd_month": 50000.0,
            "variable_cost_dzd_per_unit": 2.0,
            "max_capacity_units": 3000.0,
            "is_existing": 1,
        },
        {
            "facility_id": "F2",
            "facility_name": "DC Oran",
            "latitude": 35.73,
            "longitude": -0.63,
            "fixed_cost_dzd_month": 100000.0,
            "variable_cost_dzd_per_unit": 3.0,
            "max_capacity_units": 2000.0,
            "is_existing": 0,
        },
    ])

    inbound_costs = {("S1", "F1"): 1.0, ("S1", "F2"): 20.0}
    outbound_costs = {
        ("F1", "R1"): 1.0,
        ("F1", "R2"): 25.0,
        ("F2", "R1"): 25.0,
        ("F2", "R2"): 2.0,
    }
    lead_times = {
        ("F1", "R1"): 1,
        ("F1", "R2"): 2,
        ("F2", "R1"): 2,
        ("F2", "R2"): 1,
    }

    return regions, suppliers, facilities, inbound_costs, outbound_costs, lead_times


def test_optimizer_solves_optimally(small_network):
    regions, suppliers, facilities, inbound, outbound, lead_times = small_network
    result = solve_facility_location(
        regions=regions,
        suppliers=suppliers,
        facilities=facilities,
        inbound_costs=inbound,
        outbound_costs=outbound,
        lead_times=lead_times,
    )

    assert result.is_feasible
    assert result.solver_status == "OPTIMAL"
    assert result.objective_value_dzd > 0.0
    assert len(result.assignments) == 2
    assert result.kpis.open_facility_count >= 1


def test_optimizer_respects_max_lead_time(small_network):
    regions, suppliers, facilities, inbound, outbound, lead_times = small_network
    # If max_lead_time_days is 1, F1 cannot serve R2 (lead time is 2 days), so F2 must open
    result = solve_facility_location(
        regions=regions,
        suppliers=suppliers,
        facilities=facilities,
        inbound_costs=inbound,
        outbound_costs=outbound,
        lead_times=lead_times,
        max_lead_time_days=1,
    )

    assert result.is_feasible
    open_fac_ids = [f.facility_id for f in result.facilities if f.is_open]
    assert "F2" in open_fac_ids


def test_optimizer_detects_infeasible_capacity(small_network):
    regions, suppliers, facilities, inbound, outbound, lead_times = small_network
    # Insufficient supplier capacity
    suppliers.loc[0, "capacity_units_month"] = 100.0  # total demand is 1500

    result = solve_facility_location(
        regions=regions,
        suppliers=suppliers,
        facilities=facilities,
        inbound_costs=inbound,
        outbound_costs=outbound,
        lead_times=lead_times,
    )

    assert not result.is_feasible
    assert result.solver_status == "INFEASIBLE"
