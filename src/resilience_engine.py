"""Supply chain stress-testing and N-1 disruption contingency simulation."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from src.optimizer import OptimizationResult, solve_facility_location


@dataclass
class DisruptionScenarioResult:
    disrupted_node_id: str
    disrupted_node_name: str
    node_type: str
    is_feasible_contingency: bool
    contingency_status: str
    baseline_cost_dzd: float
    contingency_cost_dzd: float
    cost_surge_dzd: float
    cost_surge_percentage: float
    contingency_lead_time_days: float
    lead_time_delta_days: float
    resilience_score: float
    emergency_reassignments: List[Dict[str, str]]


def simulate_single_node_disruption(
    node_id: str,
    node_type: str,
    regions: pd.DataFrame,
    suppliers: pd.DataFrame,
    facilities: pd.DataFrame,
    inbound_costs: Dict,
    outbound_costs: Dict,
    lead_times: Dict,
    base_optimal_result: OptimizationResult,
) -> DisruptionScenarioResult:
    """Evaluate network resilience under N-1 disruption of a supply port or distribution center.

    Simulates catastrophic failure (zero capacity) at a designated node and computes
    emergency re-routing, financial cost spikes, and delivery SLA degradation.

    Args:
        node_id: Identifier of the disabled node.
        node_type: "supplier" or "facility".
        regions: Validated regions DataFrame.
        suppliers: Validated suppliers DataFrame.
        facilities: Validated facilities DataFrame.
        inbound_costs: Pairwise freight cost mapping.
        outbound_costs: Pairwise outbound freight cost mapping.
        lead_times: Pairwise transit days mapping.
        base_optimal_result: Unperturbed optimal network solution.

    Returns:
        DisruptionScenarioResult dataclass.
    """
    node_type_clean = node_type.strip().lower()
    sup_copy = suppliers.copy()
    fac_copy = facilities.copy()

    node_name = node_id

    if node_type_clean == "supplier":
        mask = sup_copy["supplier_id"] == node_id
        if not mask.any():
            raise ValueError(f"Supplier node {node_id} not found.")
        node_name = str(sup_copy.loc[mask, "supplier_name"].iloc[0])
        sup_copy.loc[mask, "capacity_units_month"] = 0.0

    elif node_type_clean == "facility":
        mask = fac_copy["facility_id"] == node_id
        if not mask.any():
            raise ValueError(f"Facility node {node_id} not found.")
        node_name = str(fac_copy.loc[mask, "facility_name"].iloc[0])
        fac_copy.loc[mask, "max_capacity_units"] = 0.0
        fac_copy.loc[mask, "is_existing"] = 0

    else:
        raise ValueError(f"Invalid node_type: {node_type}. Must be 'supplier' or 'facility'.")

    # Re-solve under contingency constraints
    contingency_result = solve_facility_location(
        regions=regions,
        suppliers=sup_copy,
        facilities=fac_copy,
        inbound_costs=inbound_costs,
        outbound_costs=outbound_costs,
        lead_times=lead_times,
        enforce_existing_facilities=False,
    )

    base_cost = base_optimal_result.objective_value_dzd
    base_lt = base_optimal_result.kpis.weighted_average_lead_time_days

    if not contingency_result.is_feasible:
        return DisruptionScenarioResult(
            disrupted_node_id=node_id,
            disrupted_node_name=node_name,
            node_type=node_type_clean,
            is_feasible_contingency=False,
            contingency_status=contingency_result.solver_status,
            baseline_cost_dzd=base_cost,
            contingency_cost_dzd=0.0,
            cost_surge_dzd=0.0,
            cost_surge_percentage=0.0,
            contingency_lead_time_days=0.0,
            lead_time_delta_days=0.0,
            resilience_score=0.0,
            emergency_reassignments=[],
        )

    cont_cost = contingency_result.objective_value_dzd
    surge_dzd = max(0.0, cont_cost - base_cost)
    surge_pct = (surge_dzd / base_cost * 100.0) if base_cost > 0 else 0.0

    cont_lt = contingency_result.kpis.weighted_average_lead_time_days
    lt_delta = cont_lt - base_lt

    # Resilience metric: 100 - weighted impact of cost surge and delay
    # Cost surge of +30% reduces score by 30 points, lead time increase reduces proportionally
    score = max(0.0, min(100.0, 100.0 - (surge_pct * 0.75) - (max(0.0, lt_delta) * 10.0)))

    # Track shifted assignments
    base_assign_map = {
        a.region_id: a.serving_facility_name for a in base_optimal_result.assignments
    }
    emergency_reassignments = []

    for a in contingency_result.assignments:
        orig_dc = base_assign_map.get(a.region_id, "")
        if orig_dc != a.serving_facility_name:
            emergency_reassignments.append({
                "region_id": a.region_id,
                "region_name": a.region_name,
                "normal_dc": orig_dc,
                "fallback_dc": a.serving_facility_name,
                "contingency_lead_time": str(a.lead_time_days),
            })

    return DisruptionScenarioResult(
        disrupted_node_id=node_id,
        disrupted_node_name=node_name,
        node_type=node_type_clean,
        is_feasible_contingency=True,
        contingency_status="FEASIBLE_FALLBACK",
        baseline_cost_dzd=round(base_cost, 2),
        contingency_cost_dzd=round(cont_cost, 2),
        cost_surge_dzd=round(surge_dzd, 2),
        cost_surge_percentage=round(surge_pct, 1),
        contingency_lead_time_days=round(cont_lt, 2),
        lead_time_delta_days=round(lt_delta, 2),
        resilience_score=round(score, 1),
        emergency_reassignments=emergency_reassignments,
    )
