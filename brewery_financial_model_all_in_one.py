"""
All-in-one Python financial model for a microbrewery-style business.

Contains:
1) A transparent monthly financial model engine:
   - SKU x channel volumes
   - cost-plus pricing + channel price factors + inflation
   - direct costs + fixed OPEX + inflation
   - CAPEX + straight-line depreciation
   - working capital (DSO/DIO/DPO + % add-ons)
   - multi-facility debt schedule (linear / annuity / specified)
   - dividend policy (cash sweep or share-of-profits)
   - monthly + annual financial statements
   - DCF valuation (FCFF + EV/EBITDA terminal multiple)
   - investor IRR + MOIC

2) A runnable example (main) that:
   - creates sample assumptions
   - runs the model
   - exports an Excel output workbook

Dependencies:
- pandas
- numpy
- openpyxl (optional, only for Excel export)

Usage:
    python brewery_financial_model_all_in_one.py

Notes:
- This is an "engine" (model logic), not a cell-by-cell conversion of an Excel template.
- Replace the example assumptions with your own inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd
from finmodel.allocation import allocate_opex_by_drivers
from finmodel.opex_defaults import build_default_opex_cost_pools
from finmodel.opex_schemas import OpexCostPool, SKUCostContext


# =============================
# Utility functions
# =============================
RepaymentType = Literal["linear", "annuity", "interest_only_then_linear", "specified"]


def annual_to_monthly_rate(annual_rate: float) -> float:
    """Convert an effective annual rate to an effective monthly rate."""
    return (1.0 + float(annual_rate)) ** (1.0 / 12.0) - 1.0


def safe_div(n: float, d: float, default: float = 0.0) -> float:
    return float(n) / float(d) if float(d) != 0.0 else float(default)


def irr(cashflows: Iterable[float], guess: float = 0.1) -> float:
    """
    Internal rate of return (per period) via Newton method.
    Returns np.nan if it fails to converge.
    """
    cfs = np.array(list(cashflows), dtype=float)
    if np.allclose(cfs, 0.0):
        return np.nan

    def f(r: float) -> float:
        return np.sum(cfs / ((1.0 + r) ** np.arange(len(cfs))))

    def fprime(r: float) -> float:
        t = np.arange(len(cfs))
        return np.sum(-t * cfs / ((1.0 + r) ** (t + 1.0)))

    r = float(guess)
    for _ in range(200):
        fr = f(r)
        fpr = fprime(r)
        if abs(fpr) < 1e-12:
            break
        new_r = r - fr / fpr
        if abs(new_r - r) < 1e-10:
            return new_r
        r = new_r
    return np.nan


# =============================
# Data structures
# =============================
@dataclass(frozen=True)
class ModelConfig:
    start_date: str = "2025-01-01"
    months: int = 120  # 10 years monthly
    pricing_cost_basis_month: int = 24  # cost basis month to compute cost-plus base prices (0-indexed)
    price_inflation_annual: float = 0.015
    cost_inflation_annual: float = 0.015
    tax_rate: float = 0.25

    # Working capital assumptions
    days_receivables: float = 20.0
    days_inventory: float = 15.0
    days_payables: float = 30.0
    other_current_assets_pct_revenue: float = 0.05
    other_current_liabilities_pct_direct_costs: float = 0.05

    # Valuation
    wacc_annual: float = 0.122
    exit_month: Optional[int] = None  # if None -> last month
    exit_ev_ebitda_multiple: float = 8.0

    # Cash
    initial_cash: float = 0.0


@dataclass(frozen=True)
class DividendPolicy:
    enabled: bool = True
    model: Literal["cash_sweep", "share_of_profits"] = "cash_sweep"
    start_month: int = 60  # e.g., "Year 5" in a 0-indexed 10-year model
    minimum_cash_position: float = 1_500_000.0
    payout_ratio: float = 0.25  # only used for share_of_profits


@dataclass(frozen=True)
class DebtFacility:
    name: str
    principal: float
    annual_interest_rate: float
    draw_month: int = 0
    grace_months: int = 0
    term_months: int = 60
    repayment_type: RepaymentType = "linear"

    # Only used for repayment_type == "specified"
    specified_principal_payments: Optional[Dict[int, float]] = None  # month -> principal payment


@dataclass(frozen=True)
class CapexItem:
    name: str
    amount: float
    capex_month: int = 0
    depreciation_years: float = 0.0  # 0 => non-depreciable (e.g., land)


@dataclass
class ModelInputs:
    """
    Required inputs:
    - skus: DataFrame with at minimum:
        sku_id (unique), name, direct_cost_per_unit, markup_pct, relative_opex_weight (optional)
    - channels: DataFrame with at minimum:
        channel (unique), price_factor
    - sales_plan: DataFrame with columns:
        date (datetime), sku_id, channel, units

    Optional inputs:
    - opex_fixed_monthly: Series indexed by date (monthly) or scalar float
    - other_income_monthly: Series indexed by date or scalar float
    - capex_items: list of CapexItem
    - debt_facilities: list of DebtFacility
    - equity_injections: dict month -> amount (positive cash-in)
    """
    skus: pd.DataFrame
    channels: pd.DataFrame
    sales_plan: pd.DataFrame

    opex_fixed_monthly: float | pd.Series = 0.0
    other_income_monthly: float | pd.Series = 0.0

    capex_items: Optional[List[CapexItem]] = None
    debt_facilities: Optional[List[DebtFacility]] = None
    equity_injections: Optional[Dict[int, float]] = None


@dataclass
class ModelRunResult:
    monthly: pd.DataFrame
    annual: pd.DataFrame
    prices: pd.DataFrame
    debt_schedules: Dict[str, pd.DataFrame]
    valuation: Dict[str, float]
    opex_allocation_views: Dict[str, pd.DataFrame]


# =============================
# Core engine
# =============================
class MicrobreweryFinancialModel:
    def __init__(
        self,
        config: ModelConfig,
        dividend_policy: DividendPolicy,
        inputs: ModelInputs,
    ) -> None:
        self.cfg = config
        self.div = dividend_policy
        self.inputs = inputs

        self._validate_inputs()

    # ---------- validation ----------
    def _validate_inputs(self) -> None:
        skus = self.inputs.skus.copy()
        channels = self.inputs.channels.copy()
        sales = self.inputs.sales_plan.copy()

        required_sku_cols = {"sku_id", "name", "direct_cost_per_unit", "markup_pct"}
        missing = required_sku_cols - set(skus.columns)
        if missing:
            raise ValueError(f"skus is missing columns: {sorted(missing)}")

        if "relative_opex_weight" not in skus.columns:
            skus["relative_opex_weight"] = 1.0
        else:
            skus["relative_opex_weight"] = skus["relative_opex_weight"].replace("", np.nan).fillna(1.0)

        required_channel_cols = {"channel", "price_factor"}
        missing = required_channel_cols - set(channels.columns)
        if missing:
            raise ValueError(f"channels is missing columns: {sorted(missing)}")

        required_sales_cols = {"date", "sku_id", "channel", "units"}
        missing = required_sales_cols - set(sales.columns)
        if missing:
            raise ValueError(f"sales_plan is missing columns: {sorted(missing)}")

        # Normalize dtypes
        sales["date"] = pd.to_datetime(sales["date"])
        # Make sku_id type consistent
        sales["sku_id"] = sales["sku_id"].astype(skus["sku_id"].dtype, copy=False)
        sales["units"] = pd.to_numeric(sales["units"], errors="coerce")

        # Enforce numeric columns to avoid object-dtype arithmetic TypeErrors.
        sku_numeric_cols = ["direct_cost_per_unit", "markup_pct", "relative_opex_weight"]
        for col in sku_numeric_cols:
            skus[col] = pd.to_numeric(skus[col], errors="coerce")
        channels["price_factor"] = pd.to_numeric(channels["price_factor"], errors="coerce")

        if skus[sku_numeric_cols].isna().any().any():
            bad_rows = skus.loc[skus[sku_numeric_cols].isna().any(axis=1), ["sku_id", "name"]].to_dict("records")
            raise ValueError(
                "skus has non-numeric values in direct_cost_per_unit/markup_pct/relative_opex_weight "
                f"for rows: {bad_rows}"
            )
        if channels["price_factor"].isna().any():
            bad_channels = channels.loc[channels["price_factor"].isna(), "channel"].tolist()
            raise ValueError(f"channels has non-numeric price_factor for channels: {bad_channels}")
        if sales["units"].isna().any():
            bad_sales = sales.loc[sales["units"].isna(), ["date", "sku_id", "channel"]].to_dict("records")
            raise ValueError(f"sales_plan has non-numeric units for rows: {bad_sales}")

        # Keep normalized copies
        self.inputs.skus = skus
        self.inputs.channels = channels
        self.inputs.sales_plan = sales

        if self.inputs.capex_items is None:
            self.inputs.capex_items = []
        if self.inputs.debt_facilities is None:
            self.inputs.debt_facilities = []
        if self.inputs.equity_injections is None:
            self.inputs.equity_injections = {}

    # ---------- timeline ----------
    def _timeline(self) -> pd.DatetimeIndex:
        start = pd.to_datetime(self.cfg.start_date)
        return pd.date_range(start=start, periods=int(self.cfg.months), freq="MS")  # month start

    def _inflation_index(self, annual_rate: float, idx: pd.DatetimeIndex) -> pd.Series:
        m = annual_to_monthly_rate(annual_rate)
        factors = (1.0 + m) ** np.arange(len(idx))
        return pd.Series(factors, index=idx, name="inflation_index")

    # ---------- scalars/series helpers ----------
    def _as_monthly_series(self, x: float | pd.Series, idx: pd.DatetimeIndex, name: str) -> pd.Series:
        if isinstance(x, pd.Series):
            s = x.copy()
            s.index = pd.to_datetime(s.index)
            s = s.reindex(idx).ffill().fillna(0.0)
            s.name = name
            return s
        return pd.Series(float(x), index=idx, name=name)

    # ---------- sales ----------
    def _units_matrix(self, idx: pd.DatetimeIndex) -> pd.DataFrame:
        """
        Returns monthly units sold as a wide DataFrame with MultiIndex columns:
            (sku_id, channel)
        Missing combinations are filled with 0.
        """
        sales = self.inputs.sales_plan.copy()
        sales = sales[sales["date"].isin(idx)].copy()
        if sales.empty:
            return pd.DataFrame(index=idx)

        wide = (
            sales.pivot_table(
                index="date",
                columns=["sku_id", "channel"],
                values="units",
                aggfunc="sum",
                fill_value=0.0,
            )
            .reindex(idx)
            .fillna(0.0)
        )
        return wide.sort_index(axis=1)

    # ---------- pricing ----------
    @staticmethod
    def _liters_per_unit_from_name(sku_name: str) -> float:
        text = str(sku_name).lower()
        m_ml = re.search(r"(\\d+(?:\\.\\d+)?)\\s*ml", text)
        if m_ml:
            return float(m_ml.group(1)) / 1000.0
        m_l = re.search(r"(\\d+(?:\\.\\d+)?)\\s*l", text)
        if m_l:
            return float(m_l.group(1))
        if "keg" in text:
            return 20.0
        return 0.5

    def _allocate_basis_opex_by_pool(
        self,
        basis_date: pd.Timestamp,
        units_wide: pd.DataFrame,
        channels: pd.DataFrame,
        skus: pd.DataFrame,
        opex_basis: float,
    ) -> pd.Series:
        units_row = units_wide.loc[basis_date] if not units_wide.empty else pd.Series(dtype=float)
        channel_price_factor = channels.set_index("channel")["price_factor"].to_dict()

        contexts: List[SKUCostContext] = []
        for sku_id, row in skus.iterrows():
            channel_units = {}
            for ch in channels["channel"].tolist():
                channel_units[ch] = float(units_row.get((sku_id, ch), 0.0))
            total_units = float(sum(channel_units.values()))
            liters_per_unit = self._liters_per_unit_from_name(str(row.get("name", "")))
            estimated_base_unit_price = float(row["direct_cost_per_unit"]) * (1.0 + float(row["markup_pct"]))
            channel_revenue = {
                ch: channel_units[ch] * estimated_base_unit_price * float(channel_price_factor.get(ch, 1.0))
                for ch in channel_units
            }
            contexts.append(
                SKUCostContext(
                    sku_id=int(sku_id),
                    sku_name=str(row.get("name", f"SKU {sku_id}")),
                    product_family=str(row.get("product_family", "Core")),
                    package_type=str(row.get("package_type", "Standard")),
                    package_size=str(row.get("package_size", "Standard")),
                    active=total_units > 0.0,
                    units_sold_by_year={"Basis": total_units},
                    liters_sold_by_year={"Basis": total_units * liters_per_unit},
                    revenue_by_year={"Basis": float(sum(channel_revenue.values()))},
                    revenue_by_channel_by_year={"Basis": channel_revenue},
                    units_by_channel_by_year={"Basis": channel_units},
                    complexity_score=float(row.get("relative_opex_weight", 1.0)),
                    batch_count_by_year={"Basis": (total_units * liters_per_unit) / 500.0},
                    order_count_by_year={"Basis": total_units / 1000.0},
                    shipment_count_by_year={"Basis": total_units / 1200.0},
                )
            )

        pools = build_default_opex_cost_pools({"Basis": float(max(opex_basis, 0.0))})
        report = allocate_opex_by_drivers(["Basis"], contexts, pools)
        allocated = {a.sku_id: a.total_allocated_opex for a in report.allocations if a.year == "Basis"}
        return pd.Series(allocated, index=skus.index).fillna(0.0)

    def _base_cost_plus_price_by_sku(self, idx: pd.DatetimeIndex, units_wide: pd.DataFrame) -> pd.Series:
        """
        Compute a base (month-0) cost-plus price for each SKU using a cost basis month:

            base_price_sku =
                (direct_cost_per_unit_basis + allocated_opex_per_unit_basis) * (1 + markup_pct)

        Returns Series indexed by sku_id.
        """
        skus = self.inputs.skus.set_index("sku_id")
        cost_index = self._inflation_index(self.cfg.cost_inflation_annual, idx)

        basis_m = int(np.clip(self.cfg.pricing_cost_basis_month, 0, len(idx) - 1))
        basis_date = idx[basis_m]

        # total units per SKU at cost basis month
        if units_wide.empty:
            units_sku = pd.Series(0.0, index=skus.index)
        else:
            units_sku = units_wide.loc[basis_date].groupby(level=0).sum()
        units_sku = units_sku.reindex(skus.index).fillna(0.0)

        # OPEX cash in basis month
        opex_fixed = self._as_monthly_series(self.inputs.opex_fixed_monthly, idx, "opex_fixed")
        opex_basis = float(opex_fixed.loc[basis_date] * cost_index.loc[basis_date])

        # Allocate OPEX via cost-pool allocator (no lump-style weighted-smear).
        alloc = self._allocate_basis_opex_by_pool(
            basis_date=basis_date,
            units_wide=units_wide,
            channels=self.inputs.channels,
            skus=skus,
            opex_basis=opex_basis,
        )
        opex_per_unit = alloc / units_sku.replace(0.0, np.nan)
        opex_per_unit = opex_per_unit.fillna(0.0)

        direct_cost_basis = skus["direct_cost_per_unit"] * cost_index.loc[basis_date]
        total_cost_basis = direct_cost_basis + opex_per_unit
        base_price = total_cost_basis * (1.0 + skus["markup_pct"])

        # If a SKU has no volume in basis month, fall back to direct-cost-plus only
        fallback = direct_cost_basis * (1.0 + skus["markup_pct"])
        base_price = base_price.where(base_price > 0.0, fallback)

        return base_price.rename("base_price_per_unit")

    def _prices_matrix(self, idx: pd.DatetimeIndex, units_wide: pd.DataFrame) -> pd.DataFrame:
        """
        Returns a wide DataFrame of prices with MultiIndex columns (sku_id, channel).
        """
        channels = self.inputs.channels.set_index("channel")
        price_index = self._inflation_index(self.cfg.price_inflation_annual, idx)
        base_price = self._base_cost_plus_price_by_sku(idx, units_wide)

        cols: List[Tuple[int, str]] = []
        data: List[np.ndarray] = []
        for sku_id, base_p in base_price.items():
            for channel, row in channels.iterrows():
                cols.append((sku_id, channel))
                series = base_p * price_index.values * float(row["price_factor"])
                data.append(series)

        prices = pd.DataFrame(
            np.array(data).T,
            index=idx,
            columns=pd.MultiIndex.from_tuples(cols, names=["sku_id", "channel"]),
        )
        return prices.sort_index(axis=1)

    # ---------- CAPEX & depreciation ----------
    def _capex_series(self, idx: pd.DatetimeIndex) -> pd.Series:
        capex = pd.Series(0.0, index=idx, name="capex")
        for item in self.inputs.capex_items:
            m = int(item.capex_month)
            if 0 <= m < len(idx):
                capex.iloc[m] += float(item.amount)
        return capex

    def _depreciation_series(self, idx: pd.DatetimeIndex) -> pd.Series:
        dep = pd.Series(0.0, index=idx, name="depreciation")
        for item in self.inputs.capex_items:
            years = float(item.depreciation_years)
            if years <= 0.0:
                continue
            m0 = int(item.capex_month)
            n = int(round(years * 12))
            if n <= 0:
                continue
            monthly_dep = float(item.amount) / n
            for k in range(n):
                m = m0 + k
                if 0 <= m < len(idx):
                    dep.iloc[m] += monthly_dep
        return dep

    def _net_fixed_assets(self, capex: pd.Series, dep: pd.Series) -> pd.Series:
        gross = capex.cumsum()
        accum_dep = dep.cumsum()
        return (gross - accum_dep).rename("net_fixed_assets")

    # ---------- Working capital ----------
    def _nwc(self, idx: pd.DatetimeIndex, revenue: pd.Series, direct_costs: pd.Series) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Computes NWC components and change in NWC.
        """
        days_year = 365.0
        ar = revenue * (self.cfg.days_receivables / days_year)
        inv = direct_costs * (self.cfg.days_inventory / days_year)
        ap = direct_costs * (self.cfg.days_payables / days_year)

        oca = revenue * float(self.cfg.other_current_assets_pct_revenue)
        ocl = direct_costs * float(self.cfg.other_current_liabilities_pct_direct_costs)

        nwc = ar + inv + oca - ap - ocl
        chg = nwc.diff().fillna(nwc.iloc[0]).rename("change_in_nwc")

        comp = pd.DataFrame(
            {
                "receivables": ar,
                "inventory": inv,
                "other_current_assets": oca,
                "payables": ap,
                "other_current_liabilities": ocl,
                "net_working_capital": nwc,
            },
            index=idx,
        )
        return comp, chg

    # ---------- Debt ----------
    def _debt_schedule_one(self, idx: pd.DatetimeIndex, fac: DebtFacility) -> pd.DataFrame:
        """
        Build a month-by-month debt schedule for a single facility.
        Columns:
            beginning_balance, draw, interest, principal_payment, ending_balance
        """
        n = len(idx)
        m_draw = int(fac.draw_month)
        grace = int(fac.grace_months)
        term = int(fac.term_months)
        r_m = annual_to_monthly_rate(fac.annual_interest_rate)

        beg = np.zeros(n)
        draw = np.zeros(n)
        interest = np.zeros(n)
        principal = np.zeros(n)
        end = np.zeros(n)

        for t in range(n):
            beg[t] = end[t - 1] if t > 0 else 0.0

            if t == m_draw:
                draw[t] = float(fac.principal)
                beg[t] += draw[t]  # treat draw as immediately outstanding for interest calc

            # Interest on beginning balance (post-draw if draw this month)
            interest[t] = beg[t] * r_m

            repay_start = m_draw + grace
            repay_end = m_draw + term  # exclusive

            if fac.repayment_type == "specified":
                p = 0.0
                if fac.specified_principal_payments and t in fac.specified_principal_payments:
                    p = float(fac.specified_principal_payments[t])
                principal[t] = min(p, beg[t])

            elif t < repay_start or t >= repay_end:
                principal[t] = 0.0

            else:
                outstanding = beg[t]

                if fac.repayment_type == "linear":
                    amort_months = max(repay_end - repay_start, 1)
                    pmt_principal = float(fac.principal) / amort_months
                    principal[t] = min(pmt_principal, outstanding)

                elif fac.repayment_type == "annuity":
                    amort_months = max(repay_end - repay_start, 1)
                    P = float(fac.principal)
                    if abs(r_m) < 1e-12:
                        total_pmt = P / amort_months
                    else:
                        total_pmt = P * r_m / (1.0 - (1.0 + r_m) ** (-amort_months))
                    principal[t] = min(max(total_pmt - interest[t], 0.0), outstanding)

                elif fac.repayment_type == "interest_only_then_linear":
                    amort_months = max(repay_end - repay_start, 1)
                    pmt_principal = float(fac.principal) / amort_months
                    principal[t] = min(pmt_principal, outstanding)

                else:
                    principal[t] = 0.0

            end[t] = max(beg[t] - principal[t], 0.0)

        return pd.DataFrame(
            {
                "beginning_balance": beg,
                "draw": draw,
                "interest": interest,
                "principal_payment": principal,
                "ending_balance": end,
            },
            index=idx,
        )

    def _debt_schedules(self, idx: pd.DatetimeIndex) -> Dict[str, pd.DataFrame]:
        schedules: Dict[str, pd.DataFrame] = {}
        for fac in self.inputs.debt_facilities:
            schedules[fac.name] = self._debt_schedule_one(idx, fac)
        return schedules

    def _annual_opex_allocation_views(
        self,
        idx: pd.DatetimeIndex,
        units_wide: pd.DataFrame,
        revenue_wide: pd.DataFrame,
        opex_series: pd.Series,
    ) -> Dict[str, pd.DataFrame]:
        skus = self.inputs.skus.set_index("sku_id")
        channels = self.inputs.channels["channel"].tolist()
        year_labels = sorted(idx.year.unique())
        year_keys = {y: f"Year {i + 1}" for i, y in enumerate(year_labels)}

        annual_opex = {}
        for y in year_labels:
            annual_opex[year_keys[y]] = float(opex_series[idx.year == y].sum())

        contexts: List[SKUCostContext] = []
        for sku_id, row in skus.iterrows():
            units_by_year = {}
            liters_by_year = {}
            revenue_by_year = {}
            revenue_ch_by_year: Dict[str, Dict[str, float]] = {}
            units_ch_by_year: Dict[str, Dict[str, float]] = {}
            batch_by_year = {}
            order_by_year = {}
            ship_by_year = {}
            liters_per_unit = self._liters_per_unit_from_name(str(row.get("name", "")))
            for y in year_labels:
                key = year_keys[y]
                mask = idx.year == y
                units_year = units_wide.loc[mask] if not units_wide.empty else pd.DataFrame(index=idx[mask])
                rev_year = revenue_wide.loc[mask] if not revenue_wide.empty else pd.DataFrame(index=idx[mask])
                ch_units = {ch: float(units_year.get((sku_id, ch), pd.Series(dtype=float)).sum()) for ch in channels}
                ch_revenue = {ch: float(rev_year.get((sku_id, ch), pd.Series(dtype=float)).sum()) for ch in channels}
                total_units = float(sum(ch_units.values()))
                total_revenue = float(sum(ch_revenue.values()))
                units_by_year[key] = total_units
                liters_by_year[key] = total_units * liters_per_unit
                revenue_by_year[key] = total_revenue
                units_ch_by_year[key] = ch_units
                revenue_ch_by_year[key] = ch_revenue
                batch_by_year[key] = (total_units * liters_per_unit) / 500.0
                order_by_year[key] = total_units / 1000.0
                ship_by_year[key] = total_units / 1200.0

            contexts.append(
                SKUCostContext(
                    sku_id=int(sku_id),
                    sku_name=str(row.get("name", f"SKU {sku_id}")),
                    product_family=str(row.get("product_family", "Core")),
                    package_type=str(row.get("package_type", "Standard")),
                    package_size=str(row.get("package_size", "Standard")),
                    active=any(v > 0.0 for v in units_by_year.values()),
                    units_sold_by_year=units_by_year,
                    liters_sold_by_year=liters_by_year,
                    revenue_by_year=revenue_by_year,
                    revenue_by_channel_by_year=revenue_ch_by_year,
                    units_by_channel_by_year=units_ch_by_year,
                    complexity_score=float(row.get("relative_opex_weight", 1.0)),
                    batch_count_by_year=batch_by_year,
                    order_count_by_year=order_by_year,
                    shipment_count_by_year=ship_by_year,
                )
            )

        pools: List[OpexCostPool] = build_default_opex_cost_pools(annual_opex)
        report = allocate_opex_by_drivers(list(annual_opex.keys()), contexts, pools)
        pool_view = pd.DataFrame({s.year: s.by_pool_totals for s in report.summaries}).T
        driver_view = pd.DataFrame({s.year: s.by_driver_type_totals for s in report.summaries}).T
        rec_view = pd.DataFrame(
            {
                s.year: {
                    "total_pool_opex": s.total_pool_opex,
                    "total_allocated_opex": s.total_allocated_opex,
                    "reconciliation_gap": s.reconciliation_gap,
                }
                for s in report.summaries
            }
        ).T
        product_view = pd.DataFrame(
            [
                {
                    "year": a.year,
                    "sku_id": a.sku_id,
                    "sku_name": a.sku_name,
                    "total_allocated_opex": a.total_allocated_opex,
                    "opex_per_unit": a.opex_per_unit,
                    "opex_per_liter": a.opex_per_liter,
                    "opex_per_case": a.opex_per_case,
                }
                for a in report.allocations
            ]
        )
        return {
            "pool_view": pool_view,
            "driver_view": driver_view,
            "product_view": product_view,
            "reconciliation_view": rec_view,
        }

    # ---------- Run model ----------
    def run(self) -> ModelRunResult:
        idx = self._timeline()

        # Inflation indices
        cost_idx = self._inflation_index(self.cfg.cost_inflation_annual, idx)

        # Units, prices, revenue
        units_wide = self._units_matrix(idx)
        prices_wide = self._prices_matrix(idx, units_wide)

        revenue_wide = units_wide.mul(prices_wide, fill_value=0.0)
        revenue = revenue_wide.sum(axis=1).rename("revenue")

        other_income = self._as_monthly_series(self.inputs.other_income_monthly, idx, "other_income")
        other_income = (other_income * cost_idx).rename("other_income")  # default: inflate with costs
        total_revenue = (revenue + other_income).rename("total_revenue")

        # Direct costs
        skus = self.inputs.skus.set_index("sku_id")
        if units_wide.empty:
            direct_costs = pd.Series(0.0, index=idx, name="direct_costs")
        else:
            cost_cols = []
            cost_data = []
            for sku_id, row in skus.iterrows():
                for channel in self.inputs.channels["channel"].tolist():
                    cost_cols.append((sku_id, channel))
                    series = float(row["direct_cost_per_unit"]) * cost_idx.values
                    cost_data.append(series)
            costs_wide = pd.DataFrame(
                np.array(cost_data).T,
                index=idx,
                columns=pd.MultiIndex.from_tuples(cost_cols, names=["sku_id", "channel"]),
            ).sort_index(axis=1)

            direct_costs_wide = units_wide.mul(costs_wide, fill_value=0.0)
            direct_costs = direct_costs_wide.sum(axis=1).rename("direct_costs")

        gross_profit = (revenue - direct_costs).rename("gross_profit")

        # OPEX
        opex_fixed = self._as_monthly_series(self.inputs.opex_fixed_monthly, idx, "opex_fixed")
        opex = (opex_fixed * cost_idx).rename("opex")

        ebitda = (total_revenue - direct_costs - opex).rename("ebitda")

        # CAPEX + depreciation + net fixed assets
        capex = self._capex_series(idx)
        dep = self._depreciation_series(idx)
        net_fixed_assets = self._net_fixed_assets(capex, dep)

        ebit = (ebitda - dep).rename("ebit")

        # Working capital
        nwc_comp, change_nwc = self._nwc(idx, revenue=revenue, direct_costs=direct_costs)

        # Debt schedules
        debt_schedules = self._debt_schedules(idx)
        if debt_schedules:
            debt_interest = sum(df["interest"] for df in debt_schedules.values()).rename("interest_expense")
            debt_draw = sum(df["draw"] for df in debt_schedules.values()).rename("debt_draw")
            debt_principal = sum(df["principal_payment"] for df in debt_schedules.values()).rename("debt_principal_payment")
            debt_balance = sum(df["ending_balance"] for df in debt_schedules.values()).rename("debt_ending_balance")
        else:
            debt_interest = pd.Series(0.0, index=idx, name="interest_expense")
            debt_draw = pd.Series(0.0, index=idx, name="debt_draw")
            debt_principal = pd.Series(0.0, index=idx, name="debt_principal_payment")
            debt_balance = pd.Series(0.0, index=idx, name="debt_ending_balance")

        # Taxes
        ebt = (ebit - debt_interest).rename("ebt")
        taxes = (ebt.clip(lower=0.0) * float(self.cfg.tax_rate)).rename("taxes")
        net_income = (ebt - taxes).rename("net_income")

        # Equity injections
        equity_inj = pd.Series(0.0, index=idx, name="equity_injection")
        for m, amt in (self.inputs.equity_injections or {}).items():
            m = int(m)
            if 0 <= m < len(idx):
                equity_inj.iloc[m] += float(amt)

        # Cash flow building blocks
        cfo = (net_income + dep - change_nwc).rename("cash_flow_from_operations")
        cfi = (-capex).rename("cash_flow_from_investing")
        cff_pre_div = (equity_inj + debt_draw - debt_principal).rename("cash_flow_from_financing_pre_div")

        # Sequential cash and dividends
        dividends = pd.Series(0.0, index=idx, name="dividends")
        cash = pd.Series(0.0, index=idx, name="cash")
        cash_prev = float(self.cfg.initial_cash)

        for t, _date in enumerate(idx):
            cash_pre = cash_prev + float(cfo.iloc[t] + cfi.iloc[t] + cff_pre_div.iloc[t])

            div_t = 0.0
            if self.div.enabled and t >= int(self.div.start_month):
                if self.div.model == "cash_sweep":
                    div_t = max(cash_pre - float(self.div.minimum_cash_position), 0.0)
                else:
                    div_t = float(self.div.payout_ratio) * max(float(net_income.iloc[t]), 0.0)

            cash_end = cash_pre - div_t
            dividends.iloc[t] = div_t
            cash.iloc[t] = cash_end
            cash_prev = cash_end

        # FCFF and valuation
        nopat = (ebit * (1.0 - float(self.cfg.tax_rate))).rename("nopat")
        fcff = (nopat + dep - capex - change_nwc).rename("fcff")

        exit_m = self.cfg.exit_month if self.cfg.exit_month is not None else (len(idx) - 1)
        exit_m = int(np.clip(exit_m, 0, len(idx) - 1))
        terminal_value = max(float(ebitda.iloc[exit_m]), 0.0) * float(self.cfg.exit_ev_ebitda_multiple)

        wacc_m = annual_to_monthly_rate(self.cfg.wacc_annual)
        discount = (1.0 + wacc_m) ** np.arange(len(idx))

        enterprise_value = float((fcff.values / discount).sum() + terminal_value / discount[exit_m])

        debt_exit = float(debt_balance.iloc[exit_m])
        cash_exit = float(cash.iloc[exit_m])
        equity_value_exit = enterprise_value - debt_exit + cash_exit

        # Investor IRR and MOIC (equity injections are cash-in to company => negative to investor)
        equity_cashflows = (-equity_inj).copy()
        equity_cashflows += dividends
        equity_cashflows.iloc[exit_m] += float(equity_value_exit)

        irr_m = irr(equity_cashflows.values, guess=0.02)
        irr_annual = (1.0 + irr_m) ** 12 - 1.0 if np.isfinite(irr_m) else np.nan

        invested = float(equity_inj.sum())
        returned = float(dividends.sum() + max(equity_value_exit, 0.0))
        moic = safe_div(returned, invested, default=np.nan)

        valuation = {
            "wacc_annual": float(self.cfg.wacc_annual),
            "wacc_monthly": float(wacc_m),
            "exit_month_index": float(exit_m),
            "terminal_value": float(terminal_value),
            "enterprise_value_dcf": float(enterprise_value),
            "equity_value_exit": float(equity_value_exit),
            "equity_irr_monthly": float(irr_m) if np.isfinite(irr_m) else np.nan,
            "equity_irr_annual": float(irr_annual) if np.isfinite(irr_annual) else np.nan,
            "equity_moic": float(moic) if np.isfinite(moic) else np.nan,
        }

        # Statements
        monthly = pd.DataFrame(
            {
                "revenue": revenue,
                "other_income": other_income,
                "total_revenue": total_revenue,
                "direct_costs": direct_costs,
                "gross_profit": gross_profit,
                "opex": opex,
                "ebitda": ebitda,
                "depreciation": dep,
                "ebit": ebit,
                "interest_expense": debt_interest,
                "ebt": ebt,
                "taxes": taxes,
                "net_income": net_income,
                "capex": capex,
                "change_in_nwc": change_nwc,
                "debt_draw": debt_draw,
                "debt_principal_payment": debt_principal,
                "equity_injection": equity_inj,
                "dividends": dividends,
                "cash": cash,
                "debt_ending_balance": debt_balance,
                "net_fixed_assets": net_fixed_assets,
                "fcff": fcff,
            },
            index=idx,
        ).join(nwc_comp)

        annual = monthly.resample("YE").sum(numeric_only=True).rename_axis("year_end")

        opex_allocation_views = self._annual_opex_allocation_views(
            idx=idx,
            units_wide=units_wide,
            revenue_wide=revenue_wide,
            opex_series=opex,
        )

        return ModelRunResult(
            monthly=monthly,
            annual=annual,
            prices=prices_wide,
            debt_schedules=debt_schedules,
            valuation=valuation,
            opex_allocation_views=opex_allocation_views,
        )


# =============================
# Convenience helper
# =============================
def phase_growth_series(
    idx: pd.DatetimeIndex,
    start_month: int,
    start_units: float,
    monthly_growth: float,
    stop_month: Optional[int] = None,
    cap_units: Optional[float] = None,
) -> pd.Series:
    """
    Simple helper to generate a monthly series that starts at start_month and grows by monthly_growth.
    - If stop_month is None, it grows until the end of the index.
    - cap_units (optional) applies a ceiling.
    """
    n = len(idx)
    s = np.zeros(n, dtype=float)
    stop = stop_month if stop_month is not None else n
    stop = int(np.clip(stop, 0, n))

    u = float(start_units)
    for t in range(int(start_month), stop):
        s[t] = u
        u = u * (1.0 + float(monthly_growth))
        if cap_units is not None:
            u = min(u, float(cap_units))
    return pd.Series(s, index=idx)


# =============================
# Example runner
# =============================
def main() -> None:
    # ----------------------------
    # Model horizon (10 years monthly)
    # ----------------------------
    cfg = ModelConfig(
        start_date="2025-01-01",
        months=120,
        pricing_cost_basis_month=24,  # compute base cost-plus prices using month 25 as a cost basis
        price_inflation_annual=0.015,
        cost_inflation_annual=0.015,
        tax_rate=0.25,
        wacc_annual=0.122,
        exit_ev_ebitda_multiple=8.0,
        initial_cash=0.0,
    )

    div = DividendPolicy(
        enabled=True,
        model="cash_sweep",
        start_month=60,              # "Year 5" in a 0-indexed monthly model
        minimum_cash_position=1_500_000.0,
        payout_ratio=0.25,
    )

    idx = pd.date_range(cfg.start_date, periods=cfg.months, freq="MS")

    # ----------------------------
    # SKUs (replace with your own SKU list)
    # direct_cost_per_unit: USD/unit
    # markup_pct: e.g., 0.60 => 60% markup on cost-plus base
    # ----------------------------
    skus = pd.DataFrame(
        [
            {"sku_id": 1, "name": "Pale Ale 330ml", "direct_cost_per_unit": 2.10, "markup_pct": 0.65, "relative_opex_weight": 1.0},
            {"sku_id": 2, "name": "Pilsner 500ml", "direct_cost_per_unit": 2.60, "markup_pct": 0.60, "relative_opex_weight": 1.1},
        ]
    )

    # ----------------------------
    # Distribution channels and price factors
    # (factor multiplies the SKU base price)
    # ----------------------------
    channels = pd.DataFrame(
        [
            {"channel": "Wholesale", "price_factor": 1.40},
            {"channel": "Retail", "price_factor": 2.00},
            {"channel": "E-Commerce", "price_factor": 1.75},
            {"channel": "On-Premise", "price_factor": 1.00},
        ]
    )

    # ----------------------------
    # Sales plan (units per month, per SKU, per channel)
    # Replace this with your own monthly forecast.
    # ----------------------------
    u_sku1 = phase_growth_series(idx, start_month=3, start_units=8_000, monthly_growth=0.04, stop_month=None, cap_units=25_000)
    u_sku2 = phase_growth_series(idx, start_month=3, start_units=6_000, monthly_growth=0.04, stop_month=None, cap_units=20_000)

    channel_mix = {"Wholesale": 0.45, "Retail": 0.35, "E-Commerce": 0.15, "On-Premise": 0.05}

    rows = []
    for date in idx:
        for sku_id, series in [(1, u_sku1), (2, u_sku2)]:
            total_units = float(series.loc[date])
            for channel, share in channel_mix.items():
                rows.append({"date": date, "sku_id": sku_id, "channel": channel, "units": total_units * share})
    sales_plan = pd.DataFrame(rows)

    # ----------------------------
    # OPEX and other income (monthly)
    # ----------------------------
    opex_fixed_monthly = 110_000.0

    other_income_monthly = pd.Series(0.0, index=idx)
    other_income_monthly.iloc[12:] = 15_000.0  # from month 13 onward

    # ----------------------------
    # CAPEX schedule (simplified example)
    # ----------------------------
    capex_items = [
        CapexItem(name="Land (non-depreciable)", amount=875_000, capex_month=0, depreciation_years=0),
        CapexItem(name="Building", amount=1_750_000, capex_month=0, depreciation_years=25),
        CapexItem(name="Brewhouse equipment", amount=1_250_000, capex_month=1, depreciation_years=10),
        CapexItem(name="Expansion equipment", amount=900_000, capex_month=60, depreciation_years=10),
    ]

    # ----------------------------
    # Debt facilities (example terms)
    # ----------------------------
    debt_facilities = [
        DebtFacility(name="Mortgage", principal=750_000, annual_interest_rate=0.03, draw_month=0, grace_months=6, term_months=120, repayment_type="linear"),
        DebtFacility(name="Loan A", principal=450_000, annual_interest_rate=0.025, draw_month=5, grace_months=4, term_months=60, repayment_type="annuity"),
        DebtFacility(name="Loan B", principal=200_000, annual_interest_rate=0.015, draw_month=58, grace_months=0, term_months=36, repayment_type="linear"),
    ]

    equity_injections = {0: 5_500_000.0, 12: 1_000_000.0}

    inputs = ModelInputs(
        skus=skus,
        channels=channels,
        sales_plan=sales_plan,
        opex_fixed_monthly=opex_fixed_monthly,
        other_income_monthly=other_income_monthly,
        capex_items=capex_items,
        debt_facilities=debt_facilities,
        equity_injections=equity_injections,
    )

    model = MicrobreweryFinancialModel(cfg, div, inputs)
    result = model.run()

    print("\n=== Valuation summary ===")
    for k, v in result.valuation.items():
        if isinstance(v, float):
            print(f"{k:>28}: {v:,.6f}")
        else:
            print(f"{k:>28}: {v}")

    print("\n=== Annual Income Statement (selected lines) ===")
    annual = result.annual[["total_revenue", "direct_costs", "gross_profit", "opex", "ebitda", "net_income"]].copy()
    print(annual.tail(5).to_string())

    # Export outputs (optional)
    out_xlsx = "brewery_model_output.xlsx"
    try:
        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
            result.monthly.to_excel(writer, sheet_name="Monthly_Statements")
            result.annual.to_excel(writer, sheet_name="Annual_Summary")
            result.prices.to_excel(writer, sheet_name="Prices")
            for name, df in result.debt_schedules.items():
                df.to_excel(writer, sheet_name=f"Debt_{name[:25]}")
        print(f"\nWrote: {out_xlsx}")
    except Exception as e:
        print(f"\nExcel export skipped (openpyxl missing or other error): {e}")


if __name__ == "__main__":
    main()
