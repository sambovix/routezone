"""System configuration and operational defaults."""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class OperationalConfig:
    road_circuity_factor: float = 1.25
    average_truck_speed_kmh: float = 60.0
    max_driving_hours_per_day: float = 8.0
    default_cost_per_unit_km_dzd: float = 0.12
    default_max_lead_time_days: int = 5
    solver_time_limit_seconds: int = 60


@dataclass(frozen=True)
class CurrencyConfig:
    base_currency: str = "DZD"
    supported_currencies: Tuple[str, ...] = ("DZD", "USD", "EUR")
    currency_symbols: Dict[str, str] = field(
        default_factory=lambda: {"DZD": "DZD", "USD": "$", "EUR": "€"}
    )
    # Conversion rate: number of DZD per 1 foreign currency unit
    default_fx_to_base: Dict[str, float] = field(
        default_factory=lambda: {"DZD": 1.0, "USD": 134.0, "EUR": 145.0}
    )


DEFAULT_OPERATIONAL_CONFIG = OperationalConfig()
DEFAULT_CURRENCY_CONFIG = CurrencyConfig()
