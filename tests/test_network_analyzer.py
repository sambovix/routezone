"""Unit tests for currency conversion and baseline analytics."""

import pytest
from src.network_analyzer import (
    compare_with_baseline,
    convert_costs_to_currency,
)
from src.optimizer import CostBreakdown, NetworkKPIs, OptimizationResult


@pytest.fixture
def mock_optimization_result():
    breakdown = CostBreakdown(
        fixed_facility_cost=500000.0,
        variable_handling_cost=200000.0,
        inbound_freight_cost=300000.0,
        outbound_freight_cost=400000.0,
        total_landed_cost=1400000.0,
    )
    kpis = NetworkKPIs(
        total_demand=10000.0,
        open_facility_count=2,
        weighted_average_lead_time_days=2.1,
        landed_cost_per_unit=140.0,
        average_facility_utilization=0.85,
    )
    return OptimizationResult(
        solver_status="OPTIMAL",
        is_feasible=True,
        objective_value_dzd=1400000.0,
        facilities=[],
        assignments=[],
        inbound_flows=[],
        cost_breakdown=breakdown,
        kpis=kpis,
        raw_status_code=1,
    )


def test_convert_costs_to_usd(mock_optimization_result):
    custom_fx = {"DZD": 1.0, "USD": 140.0, "EUR": 150.0}
    converted = convert_costs_to_currency(
        breakdown=mock_optimization_result.cost_breakdown,
        total_demand=10000.0,
        target_currency="USD",
        custom_fx_rates=custom_fx,
    )

    assert converted.currency == "USD"
    assert converted.symbol == "$"
    # 1,400,000 DZD / 140 = 10,000 USD
    assert converted.total_landed_cost == pytest.approx(10000.0, abs=1.0)
    assert converted.cost_per_unit == pytest.approx(1.0, abs=0.01)


def test_compare_with_baseline(mock_optimization_result):
    baseline_stats = {
        "baseline_total_cost": 2000000.0,
        "baseline_total_cost_dzd": 2000000.0,
        "baseline_avg_lead_time_days": 4.5,
        "primary_facility_id": "F1",
    }
    comparison = compare_with_baseline(
        result=mock_optimization_result,
        baseline_stats=baseline_stats,
        target_currency="DZD",
    )

    # 2,000,000 baseline - 1,400,000 opt = 600,000 savings (30%)
    assert comparison.absolute_savings == pytest.approx(600000.0, abs=1.0)
    assert comparison.percentage_savings == pytest.approx(30.0, abs=0.1)
    assert comparison.lead_time_reduction_days == pytest.approx(2.4, abs=0.1)
