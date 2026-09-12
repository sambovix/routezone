"""Scope 3 transport carbon emissions and Greenhouse Gas accounting engine."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from src.geo_engine import estimate_road_distance_km
from src.optimizer import AssignmentRecord, InboundFlowRecord


@dataclass
class CarbonFootprintReport:
    inbound_ton_km: float
    outbound_ton_km: float
    total_ton_km: float
    inbound_co2_tonnes: float
    outbound_co2_tonnes: float
    total_co2_tonnes: float
    emission_factor_kg_per_tkm: float
    baseline_co2_tonnes: Optional[float] = None
    co2_savings_tonnes: Optional[float] = None
    co2_savings_percentage: Optional[float] = None


def calculate_transport_emissions(
    inbound_flows: List[InboundFlowRecord],
    assignments: List[AssignmentRecord],
    distances_km: Dict,
    unit_weight_kg: float = 10.0,
    emission_factor_kg_per_tkm: float = 0.070,
    baseline_stats: Optional[Dict] = None,
) -> CarbonFootprintReport:
    """Calculate Scope 3 freight greenhouse gas emissions in metric tonnes of CO2.

    Applies European Environment Agency and ADEME emission standards for heavy goods vehicles:
    Emissions (t CO2) = Ton-Kilometers * Emission Factor (kg CO2 / t.km) / 1000

    Args:
        inbound_flows: Solved supplier-to-facility allocation flows.
        assignments: Solved facility-to-market assignment records.
        distances_km: Pairwise distance mapping.
        unit_weight_kg: Nominal product weight in kilograms.
        emission_factor_kg_per_tkm: Freight emission index (default 0.070 kg/t.km).
        baseline_stats: Optional baseline metrics dictionary for relative reduction.

    Returns:
        CarbonFootprintReport dataclass.
    """
    if unit_weight_kg <= 0:
        raise ValueError("Unit weight must be strictly positive.")
    if emission_factor_kg_per_tkm <= 0:
        raise ValueError("Emission factor must be strictly positive.")

    weight_tonnes = unit_weight_kg / 1000.0

    inbound_tkm = 0.0
    for flow in inbound_flows:
        dist = distances_km.get((flow.supplier_id, flow.facility_id), 0.0)
        inbound_tkm += flow.volume_units * weight_tonnes * dist

    outbound_tkm = 0.0
    for assign in assignments:
        dist = distances_km.get((assign.serving_facility_id, assign.region_id))
        if dist is None or dist <= 0.0:
            dist = estimate_road_distance_km(
                assign.facility_latitude,
                assign.facility_longitude,
                assign.region_latitude,
                assign.region_longitude,
            )
        outbound_tkm += assign.demand_served * weight_tonnes * dist

    tot_tkm = inbound_tkm + outbound_tkm
    inbound_co2 = (inbound_tkm * emission_factor_kg_per_tkm) / 1000.0
    outbound_co2 = (outbound_tkm * emission_factor_kg_per_tkm) / 1000.0
    total_co2 = inbound_co2 + outbound_co2

    base_co2 = None
    co2_savings = None
    pct_savings = None

    if baseline_stats and "baseline_total_tkm" in baseline_stats:
        base_tkm = float(baseline_stats["baseline_total_tkm"])
        base_co2 = round((base_tkm * emission_factor_kg_per_tkm) / 1000.0, 3)
        co2_savings = round(base_co2 - total_co2, 3)
        pct_savings = round((co2_savings / base_co2) * 100.0, 1) if base_co2 > 0 else 0.0

    return CarbonFootprintReport(
        inbound_ton_km=round(inbound_tkm, 2),
        outbound_ton_km=round(outbound_tkm, 2),
        total_ton_km=round(tot_tkm, 2),
        inbound_co2_tonnes=round(inbound_co2, 3),
        outbound_co2_tonnes=round(outbound_co2, 3),
        total_co2_tonnes=round(total_co2, 3),
        emission_factor_kg_per_tkm=emission_factor_kg_per_tkm,
        baseline_co2_tonnes=base_co2,
        co2_savings_tonnes=co2_savings,
        co2_savings_percentage=pct_savings,
    )
