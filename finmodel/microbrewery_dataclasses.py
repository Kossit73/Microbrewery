"""Microbrewery-specific schedule dataclasses for detailed planning models."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PackagingSize:
    name: str
    singular: str
    plural: str
    shortform: str
    volume_unit: str
    units_per_sku: float
    liters_per_sku: float


@dataclass
class ExpansionEvent:
    label: str
    year_number: int
    forecast_month: int
    capacity_addition_liters_per_month: float


@dataclass
class GeneralSettings:
    project_name: str = "Microbrewery Business"
    location: str = ""
    main_product: str = "Beer"
    model_version: str = "5.30"
    currency: str = "USD"
    forecast_start_date: str = "2026-01-01"
    first_production_year: int = 1
    first_production_month_number: int = 3
    price_inflation: float = 0.015
    cost_inflation: float = 0.015


@dataclass
class WorkingCapitalAssumptions:
    receivables_days: float = 20.0
    inventory_days: float = 15.0
    payables_days: float = 30.0
    other_current_assets_pct_revenue: float = 0.05
    other_current_liabilities_pct_direct_costs: float = 0.05


@dataclass
class TaxAssumptions:
    federal_income_tax: float = 0.18
    state_income_tax: float = 0.05
    local_income_tax: float = 0.02

    @property
    def total_income_tax(self) -> float:
        return self.federal_income_tax + self.state_income_tax + self.local_income_tax


@dataclass
class WACCConfig:
    equity_weight: float = 0.60
    debt_weight: float = 0.40
    risk_free_rate: float = 0.04
    beta_unlevered: float = 1.1
    beta_levered: float = 1.8
    equity_risk_premium: float = 0.06
    other_premium: float = 0.015
    debt_risk_premium: float = 0.035
    income_tax_rate: float = 0.25
    exit_ev_ebitda_multiple: float = 8.0
    gross_cap_rate: float = 0.08

    @property
    def cost_of_equity(self) -> float:
        return self.risk_free_rate + self.beta_levered * self.equity_risk_premium + self.other_premium

    @property
    def interest_rate(self) -> float:
        return self.risk_free_rate + self.debt_risk_premium

    @property
    def after_tax_cost_of_debt(self) -> float:
        return self.interest_rate * (1.0 - self.income_tax_rate)

    @property
    def wacc(self) -> float:
        return self.equity_weight * self.cost_of_equity + self.debt_weight * self.after_tax_cost_of_debt


@dataclass
class SKU:
    sku_id: int
    name: str
    product_type: str
    packaging_size: str
    volume_unit: str
    liters_per_sku: float
    include: bool
    annual_units: Dict[str, float]
    direct_cost_year1_per_sku: float
    opex_year1_per_sku: float = 0.73
    cost_plus_markup: float = 0.20
    channel_prices_year1: Dict[str, float] = field(default_factory=dict)

    def base_price_year1(self) -> float:
        if not self.channel_prices_year1:
            return 0.0
        weights = {
            "Wholesale": 0.25,
            "Retail": 0.45,
            "E-Commerce": 0.15,
            "On-Premise Sales": 0.05,
            "Export": 0.07,
            "Events & Festivals": 0.03,
        }
        return sum(self.channel_prices_year1.get(k, 0.0) * weights.get(k, 0.0) for k in weights)


@dataclass
class MarketVolumeAssumption:
    market_segment: str
    sku_name: str
    product_type: str
    distribution_channel: str
    include: bool
    packaging_size: str
    volume_unit: str
    volume_per_sku: float
    start_phase_1_month: int
    start_phase_2_month: int
    duration_phase_1: int
    duration_phase_2: Optional[int]
    phase_1_start_units: float
    phase_2_start_units: float
    phase_1_growth: float
    phase_2_growth: float

    def monthly_units(self, months: int = 120) -> List[float]:
        out: List[float] = []
        for m in range(1, months + 1):
            if not self.include:
                out.append(0.0)
                continue
            if m < self.start_phase_1_month:
                out.append(0.0)
            elif m < self.start_phase_2_month:
                offset = m - self.start_phase_1_month
                out.append(self.phase_1_start_units * ((1 + self.phase_1_growth) ** offset))
            else:
                offset = m - self.start_phase_2_month
                out.append(self.phase_2_start_units * ((1 + self.phase_2_growth) ** offset))
        return out


@dataclass
class DirectCostComponent:
    name: str
    year_values: Dict[str, float]


@dataclass
class StartupExpense:
    name: str
    year_values: Dict[str, float]


@dataclass
class EmployeeRole:
    name: str
    category: str
    monthly_costs: Dict[str, float]
    headcount: Dict[str, float]


@dataclass
class OpexLine:
    name: str
    monthly_values: Dict[str, float]


@dataclass
class CapexItem:
    name: str
    initial_capacity: float
    expansion_1: float
    expansion_2: float
    expansion_3: float
    expansion_4: float
    maintenance_rate: float
    depreciation_years: float

    def yearly_capex_schedule(self) -> Dict[str, float]:
        return {
            "Year 0": self.initial_capacity,
            "Year 1": self.expansion_1,
            "Year 2": self.expansion_2,
            "Year 4": self.expansion_3,
            "Year 6": self.expansion_4,
        }


@dataclass
class DebtFacility:
    name: str
    debt_amount: float
    interest_rate: float
    draw_year_label: str
    draw_month_number: int
    grace_period_months: int
    repayment_years: int
    repayment_model: str = "Linear"


@dataclass
class OtherIncomeLine:
    name: str
    monthly_values: Dict[str, float]


@dataclass
class EventTourLine:
    name: str
    monthly_values: Dict[str, float]


@dataclass
class InvestorRound:
    name: str
    active: bool
    new_equity_capital: float
    forecast_month: int
    forecast_year_label: str
    participant_shares: Dict[str, float]


@dataclass
class FinancialResults:
    yearly: Dict[str, Dict[str, float]]

    def to_json(self) -> str:
        return json.dumps(self.yearly, indent=2)
