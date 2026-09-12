"""Data loading, Pydantic validation, and transport cost synthesis."""

from io import StringIO
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
from pydantic import BaseModel, Field, field_validator

from config import DEFAULT_OPERATIONAL_CONFIG, OperationalConfig
from src.geo_engine import (
    estimate_lead_time_days,
    estimate_road_distance_km,
)


class RegionSchema(BaseModel):
    region_id: str = Field(..., min_length=1)
    region_name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    demand_units_month: float = Field(..., gt=0.0)


class SupplierSchema(BaseModel):
    supplier_id: str = Field(..., min_length=1)
    supplier_name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    capacity_units_month: float = Field(..., gt=0.0)


class FacilitySchema(BaseModel):
    facility_id: str = Field(..., min_length=1)
    facility_name: str = Field(..., min_length=1)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    fixed_cost_dzd_month: float = Field(..., ge=0.0)
    variable_cost_dzd_per_unit: float = Field(..., ge=0.0)
    max_capacity_units: float = Field(..., gt=0.0)
    is_existing: int = Field(default=0)

    @field_validator("is_existing")
    @classmethod
    def validate_binary_flag(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("is_existing must be either 0 or 1.")
        return v


def _read_to_dataframe(source: Union[str, StringIO, Any]) -> pd.DataFrame:
    """Read CSV from file path, StringIO, or Streamlit UploadedFile buffer."""
    if isinstance(source, str):
        return pd.read_csv(source)
    if hasattr(source, "read"):
        return pd.read_csv(source)
    raise TypeError(f"Unsupported file source type: {type(source)}")


def load_regions(source: Union[str, StringIO, Any]) -> pd.DataFrame:
    """Load and validate customer demand regions dataset."""
    df = _read_to_dataframe(source)
    required = {"region_id", "region_name", "latitude", "longitude", "demand_units_month"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Regions CSV missing required columns: {sorted(list(missing))}")

    validated_rows = []
    for idx, row in df.iterrows():
        try:
            record = RegionSchema(
                region_id=str(row["region_id"]).strip(),
                region_name=str(row["region_name"]).strip(),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                demand_units_month=float(row["demand_units_month"]),
            )
            validated_rows.append(record.model_dump())
        except Exception as err:
            raise ValueError(f"Validation error in regions row {idx}: {err}") from err

    return pd.DataFrame(validated_rows)


def load_suppliers(source: Union[str, StringIO, Any]) -> pd.DataFrame:
    """Load and validate supply gateway nodes dataset."""
    df = _read_to_dataframe(source)
    required = {"supplier_id", "supplier_name", "latitude", "longitude", "capacity_units_month"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Suppliers CSV missing required columns: {sorted(list(missing))}")

    validated_rows = []
    for idx, row in df.iterrows():
        try:
            record = SupplierSchema(
                supplier_id=str(row["supplier_id"]).strip(),
                supplier_name=str(row["supplier_name"]).strip(),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                capacity_units_month=float(row["capacity_units_month"]),
            )
            validated_rows.append(record.model_dump())
        except Exception as err:
            raise ValueError(f"Validation error in suppliers row {idx}: {err}") from err

    return pd.DataFrame(validated_rows)


def load_facilities(source: Union[str, StringIO, Any]) -> pd.DataFrame:
    """Load and validate candidate warehouse facilities dataset."""
    df = _read_to_dataframe(source)
    required = {
        "facility_id",
        "facility_name",
        "latitude",
        "longitude",
        "fixed_cost_dzd_month",
        "variable_cost_dzd_per_unit",
        "max_capacity_units",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Facilities CSV missing required columns: {sorted(list(missing))}")

    validated_rows = []
    for idx, row in df.iterrows():
        try:
            record = FacilitySchema(
                facility_id=str(row["facility_id"]).strip(),
                facility_name=str(row["facility_name"]).strip(),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                fixed_cost_dzd_month=float(row["fixed_cost_dzd_month"]),
                variable_cost_dzd_per_unit=float(row["variable_cost_dzd_per_unit"]),
                max_capacity_units=float(row["max_capacity_units"]),
                is_existing=int(row.get("is_existing", 0)),
            )
            validated_rows.append(record.model_dump())
        except Exception as err:
            raise ValueError(f"Validation error in facilities row {idx}: {err}") from err

    return pd.DataFrame(validated_rows)


def synthesize_transport_matrices(
    regions: pd.DataFrame,
    suppliers: pd.DataFrame,
    facilities: pd.DataFrame,
    custom_transport_df: Optional[pd.DataFrame] = None,
    config: OperationalConfig = DEFAULT_OPERATIONAL_CONFIG,
) -> Tuple[
    Dict[Tuple[str, str], float],
    Dict[Tuple[str, str], float],
    Dict[Tuple[str, str], int],
    Dict[Tuple[str, str], float],
]:
    """Generate or parse freight costs, road distances, and transit lead times.

    If custom_transport_df is not supplied, geodesic distances are computed with
    terrain circuity multipliers and linear unit rates.

    Args:
        regions: Validated regions DataFrame.
        suppliers: Validated suppliers DataFrame.
        facilities: Validated facilities DataFrame.
        custom_transport_df: Optional uploaded transport matrix.
        config: Operational parameters.

    Returns:
        Tuple of (inbound_costs, outbound_costs, lead_times, distances_km).
    """
    inbound_costs: Dict[Tuple[str, str], float] = {}
    outbound_costs: Dict[Tuple[str, str], float] = {}
    lead_times: Dict[Tuple[str, str], int] = {}
    distances_km: Dict[Tuple[str, str], float] = {}

    if custom_transport_df is not None and not custom_transport_df.empty:
        for _, row in custom_transport_df.iterrows():
            f_node = str(row["from_node_id"]).strip()
            t_node = str(row["to_node_id"]).strip()
            n_type = str(row.get("node_type", "")).strip().lower()
            dist = float(row.get("distance_km", 0.0))
            cost = float(row.get("transport_cost_dzd_per_unit", 0.0))
            lt = int(row.get("lead_time_days", 1))

            distances_km[(f_node, t_node)] = dist
            if n_type == "inbound":
                inbound_costs[(f_node, t_node)] = cost
            elif n_type == "outbound":
                outbound_costs[(f_node, t_node)] = cost
                lead_times[(f_node, t_node)] = lt

    # Compute missing links via geodetic engine
    s_records = suppliers.to_dict(orient="records")
    f_records = facilities.to_dict(orient="records")
    r_records = regions.to_dict(orient="records")

    for s in s_records:
        s_id = str(s["supplier_id"])
        s_lat = float(s["latitude"])
        s_lon = float(s["longitude"])
        for f in f_records:
            f_id = str(f["facility_id"])
            f_lat = float(f["latitude"])
            f_lon = float(f["longitude"])

            if (s_id, f_id) not in inbound_costs:
                dist_km = estimate_road_distance_km(
                    s_lat, s_lon, f_lat, f_lon, config.road_circuity_factor
                )
                unit_cost = dist_km * config.default_cost_per_unit_km_dzd
                inbound_costs[(s_id, f_id)] = round(unit_cost, 2)
                distances_km[(s_id, f_id)] = round(dist_km, 2)

    for f in f_records:
        f_id = str(f["facility_id"])
        f_lat = float(f["latitude"])
        f_lon = float(f["longitude"])
        for r in r_records:
            r_id = str(r["region_id"])
            r_lat = float(r["latitude"])
            r_lon = float(r["longitude"])

            dist_km = estimate_road_distance_km(
                f_lat, f_lon, r_lat, r_lon, config.road_circuity_factor
            )
            distances_km[(f_id, r_id)] = round(dist_km, 2)

            if (f_id, r_id) not in outbound_costs:
                unit_cost = dist_km * config.default_cost_per_unit_km_dzd
                outbound_costs[(f_id, r_id)] = round(unit_cost, 2)

            if (f_id, r_id) not in lead_times:
                lt_days = estimate_lead_time_days(dist_km, config)
                lead_times[(f_id, r_id)] = lt_days

    return inbound_costs, outbound_costs, lead_times, distances_km
