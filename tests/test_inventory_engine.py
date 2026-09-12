"""Unit tests for safety stock and working capital calculations."""

import pytest
from src.inventory_engine import calculate_safety_stock_holding


def test_square_root_law_scaling():
    # 30,000 units/month -> 1,000 units/day -> 14,000 units base SS
    # With 1 DC: SS = 14,000
    report_1 = calculate_safety_stock_holding(
        open_facility_count=1,
        total_monthly_demand=30000.0,
        safety_stock_coverage_days=14.0,
    )
    assert report_1.centralized_safety_stock_units == pytest.approx(14000.0, abs=1.0)
    assert report_1.decentralized_safety_stock_units == pytest.approx(14000.0, abs=1.0)
    assert report_1.centralization_penalty_monthly_dzd == pytest.approx(0.0, abs=1e-2)

    # With 4 DCs: SS = 14,000 * sqrt(4) = 28,000 units (+100% expansion)
    report_4 = calculate_safety_stock_holding(
        open_facility_count=4,
        total_monthly_demand=30000.0,
        safety_stock_coverage_days=14.0,
    )
    assert report_4.decentralized_safety_stock_units == pytest.approx(28000.0, abs=1.0)
    assert report_4.safety_stock_expansion_percentage == pytest.approx(100.0, abs=0.1)
    assert report_4.centralization_penalty_monthly_dzd > 0.0


def test_zero_facilities():
    report_0 = calculate_safety_stock_holding(open_facility_count=0, total_monthly_demand=10000.0)
    assert report_0.monthly_holding_cost_dzd == 0.0
