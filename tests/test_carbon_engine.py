"""Unit tests for carbon emissions calculations."""

import pytest
from src.carbon_engine import calculate_transport_emissions
from src.optimizer import AssignmentRecord, InboundFlowRecord


def test_calculate_transport_emissions():
    inbound = [
        InboundFlowRecord("S1", "Port", "F1", "DC", 10000.0, 1.0, 10000.0)
    ]
    assignments = [
        AssignmentRecord("R1", "Alger", "F1", "DC", 10000.0, 1, 1.0, 10000.0, 36.7, 3.0, 36.7, 3.0)
    ]
    distances = {("S1", "F1"): 100.0, ("F1", "R1"): 50.0}

    # 10,000 units * 10kg/1000 = 100 tonnes
    # inbound_tkm = 100 tonnes * 100 km = 10,000 t.km
    # outbound_tkm = 100 tonnes * 50 km = 5,000 t.km
    # total_tkm = 15,000 t.km
    # CO2 = 15,000 * 0.070 / 1000 = 1.05 tonnes
    report = calculate_transport_emissions(
        inbound_flows=inbound,
        assignments=assignments,
        distances_km=distances,
        unit_weight_kg=10.0,
        emission_factor_kg_per_tkm=0.070,
    )

    assert report.total_ton_km == pytest.approx(15000.0, abs=1.0)
    assert report.total_co2_tonnes == pytest.approx(1.05, abs=0.01)


def test_calculate_transport_emissions_invalid_inputs():
    with pytest.raises(ValueError):
        calculate_transport_emissions([], [], {}, unit_weight_kg=-5.0)
    with pytest.raises(ValueError):
        calculate_transport_emissions([], [], {}, emission_factor_kg_per_tkm=0.0)
