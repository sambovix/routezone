"""Inventory holding expenditure and safety stock centralization engine."""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class InventoryHoldingReport:
    open_facility_count: int
    centralized_safety_stock_units: float
    decentralized_safety_stock_units: float
    safety_stock_expansion_percentage: float
    monthly_holding_cost_dzd: float
    centralization_penalty_monthly_dzd: float
    annual_carrying_rate_percentage: float
    inventory_unit_value_dzd: float


def calculate_safety_stock_holding(
    open_facility_count: int,
    total_monthly_demand: float,
    safety_stock_coverage_days: float = 14.0,
    inventory_unit_value_dzd: float = 1200.0,
    annual_carrying_rate_pct: float = 18.0,
) -> InventoryHoldingReport:
    """Evaluate working capital requirements applying the Square Root Law of Inventory.

    Theoretical foundation (Eppen-Maister Law):
        Decentralized Safety Stock(N) = Centralized Safety Stock(1) * sqrt(N)
        Monthly Holding Cost = (Decentralized Safety Stock * Unit Value) * (Annual Rate / 12)

    Args:
        open_facility_count: Number of active distribution centers (N >= 1).
        total_monthly_demand: Total network volume in sales units per month.
        safety_stock_coverage_days: Buffer inventory target in operating days.
        inventory_unit_value_dzd: Average cost of goods sold per unit in DZD.
        annual_carrying_rate_pct: Cost of capital, obsolescence, and insurance percentage.

    Returns:
        InventoryHoldingReport dataclass.
    """
    if open_facility_count <= 0:
        return InventoryHoldingReport(
            open_facility_count=0,
            centralized_safety_stock_units=0.0,
            decentralized_safety_stock_units=0.0,
            safety_stock_expansion_percentage=0.0,
            monthly_holding_cost_dzd=0.0,
            centralization_penalty_monthly_dzd=0.0,
            annual_carrying_rate_percentage=annual_carrying_rate_pct,
            inventory_unit_value_dzd=inventory_unit_value_dzd,
        )

    daily_demand = total_monthly_demand / 30.0
    ss_centralized = daily_demand * safety_stock_coverage_days

    # Square Root Law scaling
    scaling_factor = math.sqrt(float(open_facility_count))
    ss_decentralized = ss_centralized * scaling_factor

    monthly_carrying_rate = (annual_carrying_rate_pct / 100.0) / 12.0
    monthly_holding_cost = ss_decentralized * inventory_unit_value_dzd * monthly_carrying_rate

    # Marginal working capital carrying cost compared to 1 central DC
    baseline_holding_cost = ss_centralized * inventory_unit_value_dzd * monthly_carrying_rate
    centralization_penalty = monthly_holding_cost - baseline_holding_cost

    expansion_pct = ((scaling_factor - 1.0) * 100.0) if scaling_factor >= 1.0 else 0.0

    return InventoryHoldingReport(
        open_facility_count=open_facility_count,
        centralized_safety_stock_units=round(ss_centralized, 1),
        decentralized_safety_stock_units=round(ss_decentralized, 1),
        safety_stock_expansion_percentage=round(expansion_pct, 1),
        monthly_holding_cost_dzd=round(monthly_holding_cost, 2),
        centralization_penalty_monthly_dzd=round(centralization_penalty, 2),
        annual_carrying_rate_percentage=annual_carrying_rate_pct,
        inventory_unit_value_dzd=inventory_unit_value_dzd,
    )
