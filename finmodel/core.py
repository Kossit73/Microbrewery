from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .constants import DAYS_PER_YEAR, FORECAST_YEARS, WORKSHEETS, YEAR_LABELS
from .data.pdf_pages import RAW_PDF_PAGES
from .schemas import (
    CapexItem,
    DebtFacility,
    EmployeeRole,
    EventTourLine,
    ExpansionEvent,
    FinancialResults,
    GeneralSettings,
    InvestorRound,
    MarketVolumeAssumption,
    OpexLine,
    OtherIncomeLine,
    PackagingSize,
    SKU,
    StartupExpense,
    TaxAssumptions,
    WACCConfig,
    WorkingCapitalAssumptions,
)


class MicrobreweryFinancialModel:
    def __init__(
        self,
        general: GeneralSettings,
        packaging_sizes: Dict[str, PackagingSize],
        expansions: List[ExpansionEvent],
        working_capital: WorkingCapitalAssumptions,
        taxes: TaxAssumptions,
        wacc: WACCConfig,
        skus: List[SKU],
        market_volume_assumptions: Optional[List[MarketVolumeAssumption]],
        startup_expenses: List[StartupExpense],
        employee_roles: List[EmployeeRole],
        opex_lines: List[OpexLine],
        capex_items: List[CapexItem],
        debt_facilities: List[DebtFacility],
        event_lines: List[EventTourLine],
        other_income_lines: List[OtherIncomeLine],
        investor_rounds: List[InvestorRound],
        minimum_cash_balance: float = 1_500_000.0,
        property_lease_value_yearly: float = 120_000.0,
        property_value_without_inflation: float = 1_500_000.0,
        dividend_payout_ratio: float = 0.25,
        dividend_start_year: int = 5,
    ):
        self.general = general
        self.packaging_sizes = packaging_sizes
        self.expansions = expansions
        self.working_capital = working_capital
        self.taxes = taxes
        self.wacc = wacc
        self.skus = skus
        self.market_volume_assumptions = market_volume_assumptions or []
        self.startup_expenses = startup_expenses
        self.employee_roles = employee_roles
        self.opex_lines = opex_lines
        self.capex_items = capex_items
        self.debt_facilities = debt_facilities
        self.event_lines = event_lines
        self.other_income_lines = other_income_lines
        self.investor_rounds = investor_rounds
        self.minimum_cash_balance = minimum_cash_balance
        self.property_lease_value_yearly = property_lease_value_yearly
        self.property_value_without_inflation = property_value_without_inflation
        self.dividend_payout_ratio = dividend_payout_ratio
        self.dividend_start_year = dividend_start_year
        self.raw_pdf_pages = RAW_PDF_PAGES

    @staticmethod
    def year_to_index(year_label: str) -> int:
        return int(year_label.split()[-1])

    def forecast_years(self) -> List[str]:
        return FORECAST_YEARS.copy()

    def total_units_by_year(self) -> Dict[str, float]:
        totals = {year: 0.0 for year in self.forecast_years()}
        for sku in self.skus:
            if sku.include:
                for year, units in sku.annual_units.items():
                    totals[year] += units
        return totals

    def revenue_by_sku_and_year(self) -> Dict[str, Dict[str, float]]:
        out: Dict[str, Dict[str, float]] = {}
        for sku in self.skus:
            if not sku.include:
                continue
            out[sku.name] = {}
            for year in self.forecast_years():
                inflation_factor = (1.0 + self.general.price_inflation) ** (self.year_to_index(year) - 1)
                out[sku.name][year] = sku.annual_units[year] * sku.base_price_year1() * inflation_factor
        return out

    def direct_costs_by_year(self) -> Dict[str, float]:
        totals = {year: 0.0 for year in self.forecast_years()}
        for sku in self.skus:
            if sku.include:
                for year in self.forecast_years():
                    infl = (1.0 + self.general.cost_inflation) ** (self.year_to_index(year) - 1)
                    totals[year] += sku.annual_units[year] * sku.direct_cost_year1_per_sku * infl
        return totals

    def annualize_monthly_lines(self, lines: List[object], attr: str = "monthly_values") -> Dict[str, float]:
        totals = {year: 0.0 for year in self.forecast_years()}
        for line in lines:
            monthly_values = getattr(line, attr)
            for year in self.forecast_years():
                totals[year] += monthly_values.get(year, 0.0) * 12.0
        return totals

    def startup_expenses_by_year(self) -> Dict[str, float]:
        totals = {year: 0.0 for year in YEAR_LABELS}
        for item in self.startup_expenses:
            for year, value in item.year_values.items():
                totals[year] += value
        return totals

    def salary_costs_by_year(self) -> Dict[str, float]:
        totals = {year: 0.0 for year in self.forecast_years()}
        for role in self.employee_roles:
            for year in self.forecast_years():
                totals[year] += role.monthly_costs.get(year, 0.0) * role.headcount.get(year, 0.0) * 13.0
        return totals

    def opex_by_year(self) -> Dict[str, float]:
        line_items = self.annualize_monthly_lines(self.opex_lines)
        salaries = self.salary_costs_by_year()
        return {year: line_items.get(year, 0.0) + salaries.get(year, 0.0) for year in self.forecast_years()}

    def capex_by_year(self) -> Dict[str, float]:
        totals = {year: 0.0 for year in YEAR_LABELS}
        for item in self.capex_items:
            for year, value in item.yearly_capex_schedule().items():
                totals[year] += value
        return totals

    def depreciation_by_year(self) -> Dict[str, float]:
        totals = {year: 0.0 for year in self.forecast_years()}
        for item in self.capex_items:
            for spend_year, amount in item.yearly_capex_schedule().items():
                start_idx = self.year_to_index(spend_year)
                annual_dep = amount / max(item.depreciation_years, 1.0)
                for y in self.forecast_years():
                    yi = self.year_to_index(y)
                    if yi > start_idx and yi <= start_idx + math.ceil(item.depreciation_years):
                        totals[y] += annual_dep
        return totals

    def debt_schedule(self) -> Dict[str, Dict[str, float]]:
        years = YEAR_LABELS
        beginning = {year: 0.0 for year in years}
        drawdown = {year: 0.0 for year in years}
        interest = {year: 0.0 for year in years}
        repayment = {year: 0.0 for year in years}
        ending = {year: 0.0 for year in years}
        facility_balances: List[Tuple[DebtFacility, Dict[str, float]]] = []

        for facility in self.debt_facilities:
            facility_years = {year: 0.0 for year in years}
            drawdown[facility.draw_year_label] += facility.debt_amount
            facility_balances.append((facility, facility_years))

        for year in years:
            yi = self.year_to_index(year)
            for facility, balances in facility_balances:
                draw_i = self.year_to_index(facility.draw_year_label)
                if yi < draw_i:
                    continue
                prev_year = f"Year {yi-1}" if yi > 0 else None
                bal = balances.get(prev_year, 0.0) if prev_year else 0.0
                if year == facility.draw_year_label:
                    bal += facility.debt_amount
                beginning[year] += bal
                interest[year] += bal * facility.interest_rate
                repayment_start_year = draw_i + math.ceil(facility.grace_period_months / 12.0)
                repay = 0.0
                if facility.repayment_years > 0 and yi >= repayment_start_year:
                    annual_repayment = facility.debt_amount / facility.repayment_years
                    repay = min(annual_repayment, bal)
                repayment[year] += repay
                end_bal = max(bal - repay, 0.0)
                balances[year] = end_bal
                ending[year] += end_bal

        return {
            "beginning_debt_balance": beginning,
            "debt_drawdown": drawdown,
            "interest_expense": interest,
            "debt_repayment": repayment,
            "ending_financial_debt": ending,
        }

    def projected_income_statement(self) -> Dict[str, Dict[str, float]]:
        beer_revenue = {year: sum(rows.get(year, 0.0) for rows in self.revenue_by_sku_and_year().values()) for year in self.forecast_years()}
        events = self.annualize_monthly_lines(self.event_lines)
        other_income = self.annualize_monthly_lines(self.other_income_lines)
        direct_costs = self.direct_costs_by_year()
        startup = self.startup_expenses_by_year()
        opex = self.opex_by_year()
        depreciation = self.depreciation_by_year()
        debt = self.debt_schedule()
        out: Dict[str, Dict[str, float]] = {}
        for year in self.forecast_years():
            revenue = beer_revenue[year] + events.get(year, 0.0) + other_income.get(year, 0.0)
            gross_profit = revenue - direct_costs[year]
            ebitda = gross_profit - opex[year] - startup.get(year, 0.0)
            ebit = ebitda - depreciation[year]
            pre_tax = ebit - debt["interest_expense"].get(year, 0.0)
            tax = max(pre_tax, 0.0) * self.taxes.total_income_tax
            out[year] = {
                "revenue": revenue,
                "direct_costs": direct_costs[year],
                "gross_profit": gross_profit,
                "startup_expenses": startup.get(year, 0.0),
                "opex": opex[year],
                "ebitda": ebitda,
                "depreciation": depreciation[year],
                "ebit": ebit,
                "interest_expense": debt["interest_expense"].get(year, 0.0),
                "income_taxes": tax,
                "net_income": pre_tax - tax,
            }
        return out

    def working_capital_by_year(self, income_statement: Optional[Dict[str, Dict[str, float]]] = None) -> Dict[str, float]:
        ismt = income_statement or self.projected_income_statement()
        wc = {}
        for year in self.forecast_years():
            revenue = ismt[year]["revenue"]
            direct_costs = ismt[year]["direct_costs"]
            receivables = revenue * self.working_capital.receivables_days / DAYS_PER_YEAR
            inventory = direct_costs * self.working_capital.inventory_days / DAYS_PER_YEAR
            payables = direct_costs * self.working_capital.payables_days / DAYS_PER_YEAR
            other_assets = revenue * self.working_capital.other_current_assets_pct_revenue
            other_liabilities = direct_costs * self.working_capital.other_current_liabilities_pct_direct_costs
            wc[year] = receivables + inventory + other_assets - payables - other_liabilities
        return wc


    def free_cash_flow_forecast(self) -> Dict[str, Dict[str, float]]:
        ismt = self.projected_income_statement()
        wc = self.working_capital_by_year(ismt)
        capex = self.capex_by_year()
        out: Dict[str, Dict[str, float]] = {}
        prev_wc = 0.0
        for year in YEAR_LABELS:
            if year == "Year 0":
                out[year] = {
                    "cash_flow_from_operations": 0.0,
                    "change_in_working_capital": 0.0,
                    "capex": -capex.get(year, 0.0),
                    "unlevered_free_cash_flow": -capex.get(year, 0.0),
                }
                continue
            delta_wc = wc[year] - prev_wc
            prev_wc = wc[year]
            cfo = ismt[year]["net_income"] + ismt[year]["depreciation"] - delta_wc
            out[year] = {
                "cash_flow_from_operations": cfo,
                "change_in_working_capital": delta_wc,
                "capex": -capex.get(year, 0.0),
                "unlevered_free_cash_flow": cfo - capex.get(year, 0.0),
            }
        return out

    def valuation(self) -> Dict[str, Dict[str, float]]:
        ismt = self.projected_income_statement()
        debt = self.debt_schedule()
        values: Dict[str, Dict[str, float]] = {}
        for year in self.forecast_years():
            ebitda = ismt[year]["ebitda"]
            enterprise_value = ebitda * self.wacc.exit_ev_ebitda_multiple
            equity_value = enterprise_value - debt["ending_financial_debt"].get(year, 0.0) + self.minimum_cash_balance
            values[year] = {
                "ebitda": ebitda,
                "enterprise_value": enterprise_value,
                "equity_value": equity_value,
            }
        return values

    def run_full_model(self) -> FinancialResults:
        return FinancialResults(
            yearly={
                "income_statement": self.projected_income_statement(),
                "free_cash_flow": self.free_cash_flow_forecast(),
                "valuation": self.valuation(),
            }
        )

    def preserved_source(self) -> Dict[str, object]:
        return {"worksheets": WORKSHEETS, "raw_pdf_pages": RAW_PDF_PAGES}
