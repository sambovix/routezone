"""Network analytics, multi-currency conversion, and baseline comparison."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from config import DEFAULT_CURRENCY_CONFIG, CurrencyConfig
from src.optimizer import CostBreakdown, NetworkKPIs, OptimizationResult


@dataclass
class CurrencyConvertedBreakdown:
    currency: str
    symbol: str
    exchange_rate: float
    fixed_facility_cost: float
    variable_handling_cost: float
    inbound_freight_cost: float
    outbound_freight_cost: float
    total_landed_cost: float
    cost_per_unit: float


@dataclass
class BaselineComparison:
    baseline_total_cost: float
    optimized_total_cost: float
    absolute_savings: float
    percentage_savings: float
    baseline_lead_time_days: float
    optimized_lead_time_days: float
    lead_time_reduction_days: float
    currency: str
    symbol: str


def convert_costs_to_currency(
    breakdown: CostBreakdown,
    total_demand: float,
    target_currency: str = "DZD",
    custom_fx_rates: Optional[Dict[str, float]] = None,
    config: CurrencyConfig = DEFAULT_CURRENCY_CONFIG,
) -> CurrencyConvertedBreakdown:
    """Convert base DZD financials into target reporting currency.

    Args:
        breakdown: CostBreakdown in base DZD.
        total_demand: Aggregate volume in throughput units.
        target_currency: Target ISO currency code (DZD, USD, EUR).
        custom_fx_rates: Optional dictionary of DZD per 1 foreign currency unit.
        config: Currency configuration with default exchange rates.

    Returns:
        CurrencyConvertedBreakdown dataclass with converted values.
    """
    fx_dict = custom_fx_rates or config.default_fx_to_base
    rate_to_base = fx_dict.get(target_currency, 1.0)
    if rate_to_base <= 0:
        raise ValueError(f"Invalid FX rate for {target_currency}: {rate_to_base}")

    # Convert base currency (DZD) to target currency
    factor = 1.0 / rate_to_base
    sym = config.currency_symbols.get(target_currency, target_currency)

    converted_fixed = round(breakdown.fixed_facility_cost * factor, 2)
    converted_var = round(breakdown.variable_handling_cost * factor, 2)
    converted_in = round(breakdown.inbound_freight_cost * factor, 2)
    converted_out = round(breakdown.outbound_freight_cost * factor, 2)
    converted_tot = round(breakdown.total_landed_cost * factor, 2)

    unit_cost = round(converted_tot / total_demand, 4) if total_demand > 0 else 0.0

    return CurrencyConvertedBreakdown(
        currency=target_currency,
        symbol=sym,
        exchange_rate=rate_to_base,
        fixed_facility_cost=converted_fixed,
        variable_handling_cost=converted_var,
        inbound_freight_cost=converted_in,
        outbound_freight_cost=converted_out,
        total_landed_cost=converted_tot,
        cost_per_unit=unit_cost,
    )


def compute_baseline_status_quo(
    regions: pd.DataFrame,
    suppliers: pd.DataFrame,
    facilities: pd.DataFrame,
    inbound_costs: Dict,
    outbound_costs: Dict,
    lead_times: Dict,
    target_currency: str = "DZD",
    custom_fx_rates: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Compute status quo network cost operating exclusively from existing facilities.

    Assumes existing facilities serve all demand directly.
    """
    existing = facilities[facilities["is_existing"] == 1]
    if existing.empty:
        existing = facilities.iloc[[0]]

    primary_fac_id = str(existing.iloc[0]["facility_id"])
    fac_row = existing.iloc[0]

    primary_sup_id = str(suppliers.iloc[0]["supplier_id"])

    total_demand = float(regions["demand_units_month"].sum())
    fixed_cost = float(fac_row["fixed_cost_dzd_month"])
    var_cost = total_demand * float(fac_row["variable_cost_dzd_per_unit"])

    unit_in = inbound_costs.get((primary_sup_id, primary_fac_id), 0.0)
    inbound_cost = total_demand * unit_in

    outbound_cost = 0.0
    weighted_lt_sum = 0.0
    for _, r in regions.iterrows():
        r_id = str(r["region_id"])
        dem = float(r["demand_units_month"])
        unit_out = outbound_costs.get((primary_fac_id, r_id), 0.0)
        lt = lead_times.get((primary_fac_id, r_id), 1)
        outbound_cost += dem * unit_out
        weighted_lt_sum += dem * lt

    baseline_tot_dzd = fixed_cost + var_cost + inbound_cost + outbound_cost
    avg_lt = weighted_lt_sum / total_demand if total_demand > 0 else 0.0

    fx_dict = custom_fx_rates or DEFAULT_CURRENCY_CONFIG.default_fx_to_base
    rate = fx_dict.get(target_currency, 1.0)
    factor = 1.0 / rate

    return {
        "baseline_total_cost": round(baseline_tot_dzd * factor, 2),
        "baseline_total_cost_dzd": round(baseline_tot_dzd, 2),
        "baseline_avg_lead_time_days": round(avg_lt, 2),
        "primary_facility_id": primary_fac_id,
    }


def compare_with_baseline(
    result: OptimizationResult,
    baseline_stats: Dict[str, float],
    target_currency: str = "DZD",
    custom_fx_rates: Optional[Dict[str, float]] = None,
) -> BaselineComparison:
    """Calculate operational delta and financial savings against status quo baseline.

    Args:
        result: Solved network optimization output.
        baseline_stats: Metrics dictionary from compute_baseline_status_quo.
        target_currency: Target currency code.
        custom_fx_rates: Exchange rate mapping.

    Returns:
        BaselineComparison with absolute/relative savings and transit improvements.
    """
    fx_dict = custom_fx_rates or DEFAULT_CURRENCY_CONFIG.default_fx_to_base
    rate = fx_dict.get(target_currency, 1.0)
    factor = 1.0 / rate
    sym = DEFAULT_CURRENCY_CONFIG.currency_symbols.get(target_currency, target_currency)

    opt_cost_curr = round(result.objective_value_dzd * factor, 2)
    base_cost_curr = baseline_stats["baseline_total_cost"]

    savings_curr = round(base_cost_curr - opt_cost_curr, 2)
    pct_savings = (
        round((savings_curr / base_cost_curr) * 100.0, 2) if base_cost_curr > 0 else 0.0
    )

    base_lt = baseline_stats["baseline_avg_lead_time_days"]
    opt_lt = result.kpis.weighted_average_lead_time_days
    lt_reduction = round(base_lt - opt_lt, 2)

    return BaselineComparison(
        baseline_total_cost=base_cost_curr,
        optimized_total_cost=opt_cost_curr,
        absolute_savings=savings_curr,
        percentage_savings=pct_savings,
        baseline_lead_time_days=base_lt,
        optimized_lead_time_days=opt_lt,
        lead_time_reduction_days=lt_reduction,
        currency=target_currency,
        symbol=sym,
    )
