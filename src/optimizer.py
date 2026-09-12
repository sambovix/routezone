"""Mixed-Integer Linear Programming solver for two-echelon facility location."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from ortools.linear_solver import pywraplp
import pandas as pd


@dataclass
class FacilityStatus:
    facility_id: str
    facility_name: str
    is_open: bool
    assigned_throughput: float
    max_capacity: float
    utilization_rate: float
    fixed_cost: float
    variable_cost: float
    latitude: float
    longitude: float


@dataclass
class AssignmentRecord:
    region_id: str
    region_name: str
    serving_facility_id: str
    serving_facility_name: str
    demand_served: float
    lead_time_days: int
    outbound_unit_cost: float
    outbound_total_cost: float
    region_latitude: float
    region_longitude: float
    facility_latitude: float
    facility_longitude: float


@dataclass
class InboundFlowRecord:
    supplier_id: str
    supplier_name: str
    facility_id: str
    facility_name: str
    volume_units: float
    unit_cost: float
    total_cost: float


@dataclass
class CostBreakdown:
    fixed_facility_cost: float
    variable_handling_cost: float
    inbound_freight_cost: float
    outbound_freight_cost: float
    total_landed_cost: float


@dataclass
class NetworkKPIs:
    total_demand: float
    open_facility_count: int
    weighted_average_lead_time_days: float
    landed_cost_per_unit: float
    average_facility_utilization: float


@dataclass
class OptimizationResult:
    solver_status: str
    is_feasible: bool
    objective_value_dzd: float
    facilities: List[FacilityStatus]
    assignments: List[AssignmentRecord]
    inbound_flows: List[InboundFlowRecord]
    cost_breakdown: CostBreakdown
    kpis: NetworkKPIs
    raw_status_code: int


def solve_facility_location(
    regions: pd.DataFrame,
    suppliers: pd.DataFrame,
    facilities: pd.DataFrame,
    inbound_costs: Dict[Tuple[str, str], float],
    outbound_costs: Dict[Tuple[str, str], float],
    lead_times: Dict[Tuple[str, str], int],
    max_lead_time_days: Optional[int] = None,
    enforce_existing_facilities: bool = False,
    demand_multiplier: float = 1.0,
    transport_cost_multiplier: float = 1.0,
    fixed_cost_multiplier: float = 1.0,
    solver_time_limit_seconds: int = 60,
) -> OptimizationResult:
    """Solve capacitated two-echelon facility location problem using OR-Tools MILP.

    Formulation:
        Min Total Cost = Fixed DC Overhead + Variable Handling + Inbound Freight + Outbound Freight
        Subject to:
            Single-sourcing per customer market
            Warehouse throughput capacity limits
            Upstream supplier output capacities
            Flow conservation across intermediate distribution nodes
            Optional maximum transit lead time limits

    Args:
        regions: Customer market demand DataFrame.
        suppliers: Gateway suppliers DataFrame.
        facilities: Candidate warehouse facilities DataFrame.
        inbound_costs: Unit cost mapping for (supplier_id, facility_id).
        outbound_costs: Unit cost mapping for (facility_id, region_id).
        lead_times: Transit lead time days mapping for (facility_id, region_id).
        max_lead_time_days: Maximum allowable delivery lead time.
        enforce_existing_facilities: If True, locks existing warehouses in active status.
        demand_multiplier: Scenario scalar for regional demand volatility.
        transport_cost_multiplier: Scenario scalar for freight rate index.
        fixed_cost_multiplier: Scenario scalar for leasing/facility overhead.
        solver_time_limit_seconds: Time ceiling for branch-and-cut execution.

    Returns:
        OptimizationResult dataclass containing allocations, flows, and financials.

    Raises:
        ValueError: If input datasets are structurally deficient or missing required keys.
    """
    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        # Fallback to standard CBC if SCIP binary is not packaged
        solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        raise RuntimeError("No suitable MILP solver engine available via OR-Tools.")

    solver.SetTimeLimit(solver_time_limit_seconds * 1000)

    reg_dict = regions.set_index("region_id").to_dict(orient="index")
    fac_dict = facilities.set_index("facility_id").to_dict(orient="index")
    sup_dict = suppliers.set_index("supplier_id").to_dict(orient="index")

    region_ids = list(reg_dict.keys())
    facility_ids = list(fac_dict.keys())
    supplier_ids = list(sup_dict.keys())

    # Adjusted demands
    demands: Dict[str, float] = {
        r_id: float(reg_dict[r_id]["demand_units_month"]) * demand_multiplier
        for r_id in region_ids
    }
    total_network_demand = sum(demands.values())

    # Binary facility activation variables: y[i]
    y: Dict[str, Any] = {
        f_id: solver.IntVar(0, 1, f"y_{f_id}") for f_id in facility_ids
    }

    # Binary single-sourcing customer allocation variables: x[i, j]
    x: Dict[Tuple[str, str], Any] = {
        (f_id, r_id): solver.IntVar(0, 1, f"x_{f_id}_{r_id}")
        for f_id in facility_ids
        for r_id in region_ids
    }

    # Continuous upstream replenishment flow variables: flow_in[s, i]
    flow_in: Dict[Tuple[str, str], Any] = {
        (s_id, f_id): solver.NumVar(0.0, solver.infinity(), f"flow_{s_id}_{f_id}")
        for s_id in supplier_ids
        for f_id in facility_ids
    }

    # Constraint 1: Single-sourcing per demand region
    for r_id in region_ids:
        solver.Add(sum(x[f_id, r_id] for f_id in facility_ids) == 1)

    # Constraint 2: Facility activation linking and capacity boundaries
    for f_id in facility_ids:
        cap = float(fac_dict[f_id]["max_capacity_units"])
        solver.Add(
            sum(demands[r_id] * x[f_id, r_id] for r_id in region_ids)
            <= cap * y[f_id]
        )
        for r_id in region_ids:
            solver.Add(x[f_id, r_id] <= y[f_id])

    # Constraint 3: Flow conservation at each distribution center (inbound == outbound)
    for f_id in facility_ids:
        inflow = sum(flow_in[s_id, f_id] for s_id in supplier_ids)
        outflow = sum(demands[r_id] * x[f_id, r_id] for r_id in region_ids)
        solver.Add(inflow == outflow)

    # Constraint 4: Supplier throughput capacity ceiling
    for s_id in supplier_ids:
        s_cap = float(sup_dict[s_id]["capacity_units_month"])
        solver.Add(
            sum(flow_in[s_id, f_id] for f_id in facility_ids) <= s_cap
        )

    # Constraint 5: Lead time SLA enforcement
    if max_lead_time_days is not None:
        for f_id in facility_ids:
            for r_id in region_ids:
                lt = lead_times.get((f_id, r_id), 1)
                if lt > max_lead_time_days:
                    solver.Add(x[f_id, r_id] == 0)

    # Constraint 6: Existing infrastructure locking
    if enforce_existing_facilities:
        for f_id in facility_ids:
            if int(fac_dict[f_id].get("is_existing", 0)) == 1:
                solver.Add(y[f_id] == 1)

    # Objective Function Formulation
    fixed_costs_expr = []
    for f_id in facility_ids:
        f_cost = float(fac_dict[f_id]["fixed_cost_dzd_month"]) * fixed_cost_multiplier
        fixed_costs_expr.append(f_cost * y[f_id])

    variable_handling_expr = []
    for f_id in facility_ids:
        v_cost = float(fac_dict[f_id]["variable_cost_dzd_per_unit"])
        for r_id in region_ids:
            variable_handling_expr.append(v_cost * demands[r_id] * x[f_id, r_id])

    inbound_freight_expr = []
    for s_id in supplier_ids:
        for f_id in facility_ids:
            unit_in_cost = inbound_costs.get((s_id, f_id), 0.0) * transport_cost_multiplier
            inbound_freight_expr.append(unit_in_cost * flow_in[s_id, f_id])

    outbound_freight_expr = []
    for f_id in facility_ids:
        for r_id in region_ids:
            unit_out_cost = outbound_costs.get((f_id, r_id), 0.0) * transport_cost_multiplier
            outbound_freight_expr.append(unit_out_cost * demands[r_id] * x[f_id, r_id])

    solver.Minimize(
        sum(fixed_costs_expr)
        + sum(variable_handling_expr)
        + sum(inbound_freight_expr)
        + sum(outbound_freight_expr)
    )

    status = solver.Solve()

    status_str_map = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL",
        pywraplp.Solver.NOT_SOLVED: "NOT_SOLVED",
    }
    status_label = status_str_map.get(status, "UNKNOWN")
    is_feasible = status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE)

    if not is_feasible:
        return OptimizationResult(
            solver_status=status_label,
            is_feasible=False,
            objective_value_dzd=0.0,
            facilities=[],
            assignments=[],
            inbound_flows=[],
            cost_breakdown=CostBreakdown(0.0, 0.0, 0.0, 0.0, 0.0),
            kpis=NetworkKPIs(total_network_demand, 0, 0.0, 0.0, 0.0),
            raw_status_code=status,
        )

    # Post-optimization extraction
    facilities_result: List[FacilityStatus] = []
    for f_id in facility_ids:
        is_open = bool(y[f_id].solution_value() > 0.5)
        f_cap = float(fac_dict[f_id]["max_capacity_units"])
        assigned_volume = sum(
            demands[r_id]
            for r_id in region_ids
            if x[f_id, r_id].solution_value() > 0.5
        )
        util_rate = round(assigned_volume / f_cap, 4) if f_cap > 0 else 0.0
        f_fixed = (
            float(fac_dict[f_id]["fixed_cost_dzd_month"]) * fixed_cost_multiplier
            if is_open
            else 0.0
        )
        f_var = assigned_volume * float(fac_dict[f_id]["variable_cost_dzd_per_unit"])

        facilities_result.append(
            FacilityStatus(
                facility_id=f_id,
                facility_name=str(fac_dict[f_id]["facility_name"]),
                is_open=is_open,
                assigned_throughput=round(assigned_volume, 2),
                max_capacity=f_cap,
                utilization_rate=util_rate,
                fixed_cost=round(f_fixed, 2),
                variable_cost=round(f_var, 2),
                latitude=float(fac_dict[f_id]["latitude"]),
                longitude=float(fac_dict[f_id]["longitude"]),
            )
        )

    assignments_result: List[AssignmentRecord] = []
    for r_id in region_ids:
        for f_id in facility_ids:
            if x[f_id, r_id].solution_value() > 0.5:
                vol = demands[r_id]
                unit_out = outbound_costs.get((f_id, r_id), 0.0) * transport_cost_multiplier
                tot_out = vol * unit_out
                lt = int(lead_times.get((f_id, r_id), 1))
                assignments_result.append(
                    AssignmentRecord(
                        region_id=r_id,
                        region_name=str(reg_dict[r_id]["region_name"]),
                        serving_facility_id=f_id,
                        serving_facility_name=str(fac_dict[f_id]["facility_name"]),
                        demand_served=round(vol, 2),
                        lead_time_days=lt,
                        outbound_unit_cost=round(unit_out, 2),
                        outbound_total_cost=round(tot_out, 2),
                        region_latitude=float(reg_dict[r_id]["latitude"]),
                        region_longitude=float(reg_dict[r_id]["longitude"]),
                        facility_latitude=float(fac_dict[f_id]["latitude"]),
                        facility_longitude=float(fac_dict[f_id]["longitude"]),
                    )
                )

    inbound_result: List[InboundFlowRecord] = []
    for s_id in supplier_ids:
        for f_id in facility_ids:
            vol_in = flow_in[s_id, f_id].solution_value()
            if vol_in > 1e-4:
                unit_in = inbound_costs.get((s_id, f_id), 0.0) * transport_cost_multiplier
                tot_in = vol_in * unit_in
                inbound_result.append(
                    InboundFlowRecord(
                        supplier_id=s_id,
                        supplier_name=str(sup_dict[s_id]["supplier_name"]),
                        facility_id=f_id,
                        facility_name=str(fac_dict[f_id]["facility_name"]),
                        volume_units=round(vol_in, 2),
                        unit_cost=round(unit_in, 2),
                        total_cost=round(tot_in, 2),
                    )
                )

    fixed_tot = sum(f.fixed_cost for f in facilities_result)
    var_tot = sum(f.variable_cost for f in facilities_result)
    in_tot = sum(flow.total_cost for flow in inbound_result)
    out_tot = sum(assign.outbound_total_cost for assign in assignments_result)
    grand_tot = fixed_tot + var_tot + in_tot + out_tot

    open_dcs = [f for f in facilities_result if f.is_open]
    open_count = len(open_dcs)

    # Lead time weighted by customer volume
    if total_network_demand > 0:
        weighted_lt = sum(
            a.lead_time_days * a.demand_served for a in assignments_result
        ) / total_network_demand
        unit_cost = grand_tot / total_network_demand
    else:
        weighted_lt = 0.0
        unit_cost = 0.0

    avg_util = (
        sum(f.utilization_rate for f in open_dcs) / open_count if open_count > 0 else 0.0
    )

    cost_breakdown = CostBreakdown(
        fixed_facility_cost=round(fixed_tot, 2),
        variable_handling_cost=round(var_tot, 2),
        inbound_freight_cost=round(in_tot, 2),
        outbound_freight_cost=round(out_tot, 2),
        total_landed_cost=round(grand_tot, 2),
    )

    kpis = NetworkKPIs(
        total_demand=round(total_network_demand, 2),
        open_facility_count=open_count,
        weighted_average_lead_time_days=round(weighted_lt, 2),
        landed_cost_per_unit=round(unit_cost, 2),
        average_facility_utilization=round(avg_util, 4),
    )

    return OptimizationResult(
        solver_status=status_label,
        is_feasible=True,
        objective_value_dzd=round(grand_tot, 2),
        facilities=facilities_result,
        assignments=assignments_result,
        inbound_flows=inbound_result,
        cost_breakdown=cost_breakdown,
        kpis=kpis,
        raw_status_code=status,
    )
