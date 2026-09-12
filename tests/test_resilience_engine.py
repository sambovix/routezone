"""Unit tests for the N-1 resilience disruption engine."""

import pandas as pd
import pytest
from src.optimizer import solve_facility_location
from src.resilience_engine import simulate_single_node_disruption


@pytest.fixture
def base_network():
    regions = pd.DataFrame([
        {"region_id": "R1", "region_name": "Alger", "latitude": 36.75, "longitude": 3.05, "demand_units_month": 1000.0},
        {"region_id": "R2", "region_name": "Oran", "latitude": 35.73, "longitude": -0.63, "demand_units_month": 500.0},
    ])
    suppliers = pd.DataFrame([
        {"supplier_id": "S1", "supplier_name": "Port Alger", "latitude": 36.75, "longitude": 3.05, "capacity_units_month": 3000.0},
        {"supplier_id": "S2", "supplier_name": "Port Bejaia", "latitude": 36.75, "longitude": 5.08, "capacity_units_month": 3000.0},
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
            "fixed_cost_dzd_month": 60000.0,
            "variable_cost_dzd_per_unit": 2.0,
            "max_capacity_units": 3000.0,
            "is_existing": 0,
        },
    ])
    inbound = {("S1", "F1"): 1.0, ("S1", "F2"): 20.0, ("S2", "F1"): 10.0, ("S2", "F2"): 25.0}
    outbound = {("F1", "R1"): 1.0, ("F1", "R2"): 25.0, ("F2", "R1"): 25.0, ("F2", "R2"): 1.0}
    lead_times = {("F1", "R1"): 1, ("F1", "R2"): 2, ("F2", "R1"): 2, ("F2", "R2"): 1}

    opt = solve_facility_location(regions, suppliers, facilities, inbound, outbound, lead_times)
    return regions, suppliers, facilities, inbound, outbound, lead_times, opt


def test_simulate_supplier_disruption(base_network):
    regions, suppliers, facilities, inbound, outbound, lead_times, opt = base_network
    # S1 failure: network must shift to S2
    result = simulate_single_node_disruption(
        node_id="S1",
        node_type="supplier",
        regions=regions,
        suppliers=suppliers,
        facilities=facilities,
        inbound_costs=inbound,
        outbound_costs=outbound,
        lead_times=lead_times,
        base_optimal_result=opt,
    )

    assert result.is_feasible_contingency
    assert result.disrupted_node_name == "Port Alger"
    assert result.contingency_cost_dzd >= result.baseline_cost_dzd
    assert 0.0 <= result.resilience_score <= 100.0


def test_simulate_facility_disruption(base_network):
    regions, suppliers, facilities, inbound, outbound, lead_times, opt = base_network
    # F1 failure: network must shift to F2
    result = simulate_single_node_disruption(
        node_id="F1",
        node_type="facility",
        regions=regions,
        suppliers=suppliers,
        facilities=facilities,
        inbound_costs=inbound,
        outbound_costs=outbound,
        lead_times=lead_times,
        base_optimal_result=opt,
    )

    assert result.is_feasible_contingency
    assert result.disrupted_node_name == "DC Alger"
    assert len(result.emergency_reassignments) > 0


def test_invalid_node_raises(base_network):
    regions, suppliers, facilities, inbound, outbound, lead_times, opt = base_network
    with pytest.raises(ValueError):
        simulate_single_node_disruption("UNKNOWN", "supplier", regions, suppliers, facilities, inbound, outbound, lead_times, opt)
