"""Configuration objects for the valuation toolkit."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ModelConfig:
    """Global modelling parameters used across valuation components."""

    discount_rate: float = 0.12
    terminal_growth_rate: float = 0.02
    forecast_years: int = 10
    tax_rate: float = 0.25
    success_prob: float = 1.0


@dataclass
class ProductConfig:
    """Inputs needed to describe a single product's economics."""

    name: str
    launch_year: int
    peak_sales: float
    ramp_years: int = 5
    cogs_ratio: float = 0.35
    opex_ratio: float = 0.25
    working_cap_ratio: float = 0.1
    patent_years: Optional[int] = None
    success_prob: float = 1.0


@dataclass
class VCInputs:
    """Venture-style valuation inputs for exit-based approaches."""

    target_irr: float = 0.4
    exit_multiple: float = 8.0
    exit_year: int = 7
    ownership: float = 0.2
    exit_revenue: Optional[float] = None


@dataclass
class MacroESGAssumptions:
    """Assumptions that can be used in macro/ESG scenarios."""

    inflation_rate: float = 0.02
    fx_rate: float = 1.0
    carbon_price: float = 0.0
    esg_capex: float = 0.0
    esg_opex: float = 0.0


@dataclass
class ScenarioAssumptions:
    """Container for scenario levers applied by ScenarioEngine."""

    revenue_multiplier: float = 1.0
    cost_multiplier: float = 1.0
    discount_rate_shift: float = 0.0
    success_prob_multiplier: float = 1.0
    macro_esg: MacroESGAssumptions = field(default_factory=MacroESGAssumptions)
