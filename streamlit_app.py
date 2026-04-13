"""Streamlit UI for the microbrewery financial model.

This app wraps the existing `MicrobreweryFinancialModel` with the sample
assumptions from ``brewery_financial_model_all_in_one.py`` and lets users tweak
key valuation parameters before running the projection. The UI surfaces the
valuation summary and selected statement tables, plus an Excel download of the
full outputs.
"""

from __future__ import annotations

from dataclasses import replace
import io
from typing import Tuple

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

from brewery_financial_model_all_in_one import (
    CapexItem,
    DebtFacility,
    DividendPolicy,
    MicrobreweryFinancialModel,
    ModelConfig,
    ModelInputs,
    phase_growth_series,
)


def _build_sample_assumptions(
    cfg: ModelConfig,
    div: DividendPolicy,
) -> ModelInputs:
    idx = pd.date_range(cfg.start_date, periods=cfg.months, freq="MS")

    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Pale Ale 330ml",
                "direct_cost_per_unit": 2.10,
                "markup_pct": 0.65,
                "relative_opex_weight": 1.0,
            },
            {
                "sku_id": 2,
                "name": "Pilsner 500ml",
                "direct_cost_per_unit": 2.60,
                "markup_pct": 0.60,
                "relative_opex_weight": 1.1,
            },
            {
                "sku_id": 3,
                "name": "Hazy IPA 440ml",
                "direct_cost_per_unit": 2.85,
                "markup_pct": 0.72,
                "relative_opex_weight": 1.25,
            },
        ]
    )

    channels = pd.DataFrame(
        [
            {"channel": "Wholesale", "price_factor": 1.40},
            {"channel": "Retail", "price_factor": 2.00},
            {"channel": "E-Commerce", "price_factor": 1.75},
            {"channel": "On-Premise", "price_factor": 1.00},
            {"channel": "Export", "price_factor": 1.55},
        ]
    )

    u_sku1 = phase_growth_series(
        idx, start_month=3, start_units=8_000, monthly_growth=0.04, stop_month=None, cap_units=25_000
    )
    u_sku2 = phase_growth_series(
        idx, start_month=3, start_units=6_000, monthly_growth=0.04, stop_month=None, cap_units=20_000
    )
    u_sku3 = phase_growth_series(
        idx, start_month=6, start_units=3_000, monthly_growth=0.05, stop_month=None, cap_units=18_000
    )

    channel_mix = {"Wholesale": 0.40, "Retail": 0.30, "E-Commerce": 0.15, "On-Premise": 0.10, "Export": 0.05}
    rows = []
    for date in idx:
        for sku_id, series in [(1, u_sku1), (2, u_sku2), (3, u_sku3)]:
            total_units = float(series.loc[date])
            for channel, share in channel_mix.items():
                rows.append({"date": date, "sku_id": sku_id, "channel": channel, "units": total_units * share})
    sales_plan = pd.DataFrame(rows)

    opex_fixed_monthly = 110_000.0
    other_income_monthly = pd.Series(0.0, index=idx)
    other_income_monthly.iloc[12:] = 15_000.0
    other_income_monthly.iloc[48:] = 22_500.0

    capex_items = [
        CapexItem(name="Land (non-depreciable)", amount=875_000, capex_month=0, depreciation_years=0),
        CapexItem(name="Building", amount=1_750_000, capex_month=0, depreciation_years=25),
        CapexItem(name="Brewhouse equipment", amount=1_250_000, capex_month=1, depreciation_years=10),
        CapexItem(name="Expansion equipment", amount=900_000, capex_month=60, depreciation_years=10),
        CapexItem(name="Packaging line upgrade", amount=650_000, capex_month=36, depreciation_years=8),
    ]

    debt_facilities = [
        DebtFacility(
            name="Mortgage",
            principal=750_000,
            annual_interest_rate=0.03,
            draw_month=0,
            grace_months=6,
            term_months=120,
            repayment_type="linear",
        ),
        DebtFacility(
            name="Loan A",
            principal=450_000,
            annual_interest_rate=0.025,
            draw_month=5,
            grace_months=4,
            term_months=60,
            repayment_type="annuity",
        ),
        DebtFacility(
            name="Loan B",
            principal=200_000,
            annual_interest_rate=0.015,
            draw_month=58,
            grace_months=0,
            term_months=36,
            repayment_type="linear",
        ),
        DebtFacility(
            name="Working Capital Revolver",
            principal=300_000,
            annual_interest_rate=0.045,
            draw_month=24,
            grace_months=0,
            term_months=48,
            repayment_type="interest_only_then_linear",
        ),
    ]

    equity_injections = {0: 5_500_000.0, 12: 1_000_000.0, 36: 750_000.0}

    return ModelInputs(
        skus=skus,
        channels=channels,
        sales_plan=sales_plan,
        opex_fixed_monthly=opex_fixed_monthly,
        other_income_monthly=other_income_monthly,
        capex_items=capex_items,
        debt_facilities=debt_facilities,
        equity_injections=equity_injections,
    )


def _run_model(cfg: ModelConfig, div: DividendPolicy) -> Tuple[ModelInputs, MicrobreweryFinancialModel]:
    inputs = _build_sample_assumptions(cfg, div)
    model = MicrobreweryFinancialModel(cfg, div, inputs)
    return inputs, model


def _apply_yearly_increment(df: pd.DataFrame, increment_pct: float) -> pd.DataFrame:
    out = df.copy()
    year_cols = []
    for c in out.columns:
        if isinstance(c, str) and c.lower().startswith("year "):
            try:
                y = int(c.split()[-1])
                year_cols.append((c, y))
            except ValueError:
                continue
    if year_cols:
        for c, y in sorted(year_cols, key=lambda x: x[1]):
            factor = (1.0 + increment_pct) ** max(y - 1, 0)
            series = pd.to_numeric(out[c], errors="coerce")
            out[c] = series.where(series.isna(), series * factor)
    else:
        numeric_cols = out.select_dtypes(include=["number"]).columns
        for c in numeric_cols:
            out[c] = out[c] * (1.0 + increment_pct)
    return out


def _assumption_editor(title: str, key: str, df: pd.DataFrame) -> pd.DataFrame:
    st.markdown(f"### {title}")
    data_key = f"assump_data_{key}"
    edit_key = f"assump_edit_{key}"
    inc_key = f"assump_inc_{key}"
    if data_key not in st.session_state:
        st.session_state[data_key] = df.copy()
    if edit_key not in st.session_state:
        st.session_state[edit_key] = False
    if inc_key not in st.session_state:
        st.session_state[inc_key] = 0.0

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("Edit", key=f"btn_edit_{key}"):
        st.session_state[edit_key] = not st.session_state[edit_key]
    increment_pct = c2.number_input(
        "Yearly Increment Percentage",
        min_value=-1.0,
        max_value=2.0,
        value=float(st.session_state[inc_key]),
        step=0.01,
        key=f"input_inc_{key}",
        format="%.4f",
    )
    st.session_state[inc_key] = increment_pct
    if c3.button("Propagate Increment", key=f"btn_prop_{key}"):
        st.session_state[data_key] = _apply_yearly_increment(st.session_state[data_key], increment_pct)

    if st.session_state[edit_key]:
        st.session_state[data_key] = st.data_editor(st.session_state[data_key], use_container_width=True)
    else:
        st.dataframe(st.session_state[data_key], use_container_width=True)
    return st.session_state[data_key]


def _build_inputs_from_state(base_inputs: ModelInputs) -> ModelInputs:
    skus = st.session_state.get("assump_data_skus", base_inputs.skus).copy()
    channels = st.session_state.get("assump_data_channels", base_inputs.channels).copy()
    sales_plan = st.session_state.get("assump_data_sales_plan", base_inputs.sales_plan).copy()

    opex_src = st.session_state.get("assump_data_opex_fixed")
    if isinstance(opex_src, pd.DataFrame) and not opex_src.empty and "date" in opex_src.columns:
        if len(opex_src) == 1 and str(opex_src.iloc[0]["date"]) == "all_months":
            opex_fixed_monthly = float(opex_src.iloc[0]["opex_fixed_monthly"])
        else:
            s = pd.Series(opex_src["opex_fixed_monthly"].values, index=pd.to_datetime(opex_src["date"]))
            opex_fixed_monthly = s
    else:
        opex_fixed_monthly = base_inputs.opex_fixed_monthly

    oi_src = st.session_state.get("assump_data_other_income")
    if isinstance(oi_src, pd.DataFrame) and not oi_src.empty and "date" in oi_src.columns:
        if len(oi_src) == 1 and str(oi_src.iloc[0]["date"]) == "all_months":
            other_income_monthly = float(oi_src.iloc[0]["other_income_monthly"])
        else:
            s = pd.Series(oi_src["other_income_monthly"].values, index=pd.to_datetime(oi_src["date"]))
            other_income_monthly = s
    else:
        other_income_monthly = base_inputs.other_income_monthly

    capex_src = st.session_state.get("assump_data_capex")
    if isinstance(capex_src, pd.DataFrame):
        capex_items = [
            CapexItem(
                name=str(r["name"]),
                amount=float(r["amount"]),
                capex_month=int(r["capex_month"]),
                depreciation_years=float(r["depreciation_years"]),
            )
            for _, r in capex_src.iterrows()
        ]
    else:
        capex_items = base_inputs.capex_items

    debt_src = st.session_state.get("assump_data_debt")
    if isinstance(debt_src, pd.DataFrame):
        debt_facilities = [
            DebtFacility(
                name=str(r["name"]),
                principal=float(r["principal"]),
                annual_interest_rate=float(r["annual_interest_rate"]),
                draw_month=int(r["draw_month"]),
                grace_months=int(r["grace_months"]),
                term_months=int(r["term_months"]),
                repayment_type=str(r["repayment_type"]),
            )
            for _, r in debt_src.iterrows()
        ]
    else:
        debt_facilities = base_inputs.debt_facilities

    equity_src = st.session_state.get("assump_data_equity")
    if isinstance(equity_src, pd.DataFrame):
        equity_injections = {int(r["month"]): float(r["equity_injection"]) for _, r in equity_src.iterrows()}
    else:
        equity_injections = base_inputs.equity_injections

    return ModelInputs(
        skus=skus,
        channels=channels,
        sales_plan=sales_plan,
        opex_fixed_monthly=opex_fixed_monthly,
        other_income_monthly=other_income_monthly,
        capex_items=capex_items,
        debt_facilities=debt_facilities,
        equity_injections=equity_injections,
    )


def _valuation_section(result) -> None:
    st.subheader("Valuation summary")
    valuation_df = pd.DataFrame(result.valuation, index=["value"]).T
    valuation_df.index.name = "metric"
    st.dataframe(valuation_df.style.format("{:,.2f}"))


def _statement_section(result) -> None:
    st.subheader("Statements")
    st.markdown("**Annual summary (all rows)**")
    annual_cols = [
        "total_revenue",
        "direct_costs",
        "gross_profit",
        "opex",
        "ebitda",
        "net_income",
        "fcff",
    ]
    st.dataframe(result.annual.loc[:, annual_cols])

    st.markdown("**Latest 12 months (monthly)**")
    st.dataframe(
        result.monthly.tail(12)[
            [
                "total_revenue",
                "direct_costs",
                "gross_profit",
                "opex",
                "ebitda",
                "net_income",
                "cash",
                "debt_ending_balance",
            ]
        ]
    )

    with st.expander("Full monthly statements (all columns)"):
        st.dataframe(result.monthly)


def _charts_section(result) -> None:
    st.subheader("Graphs & plots")
    monthly = result.monthly.copy()

    def _plot_if_available(label: str, cols: list[str]) -> None:
        existing = [c for c in cols if c in monthly.columns]
        missing = sorted(set(cols) - set(existing))
        if not existing:
            st.warning(f"Skipped '{label}' chart because columns are missing: {', '.join(cols)}")
            return
        if missing:
            st.info(
                f"Showing '{label}' with available series only; missing columns: {', '.join(missing)}"
            )
        st.line_chart(monthly[existing])

    st.markdown("**Revenue, EBITDA, and Net Income**")
    _plot_if_available(
        "Revenue, EBITDA, and Net Income",
        ["total_revenue", "ebitda", "net_income"],
    )

    st.markdown("**Cash vs. Debt Ending Balance**")
    _plot_if_available("Cash vs. Debt Ending Balance", ["cash", "debt_ending_balance"])

    st.markdown("**Operating Cash Flow vs. FCFF**")
    _plot_if_available(
        "Operating Cash Flow vs. FCFF",
        ["cash_flow_from_operations", "fcff"],
    )


def _download_section(result) -> None:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        result.monthly.to_excel(writer, sheet_name="Monthly_Statements")
        result.annual.to_excel(writer, sheet_name="Annual_Summary")
        result.prices.to_excel(writer, sheet_name="Prices")
        for name, df in result.debt_schedules.items():
            df.to_excel(writer, sheet_name=f"Debt_{name[:25]}")
    buffer.seek(0)
    st.download_button(
        label="Download Excel outputs",
        data=buffer,
        file_name="brewery_model_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _schedules_section(result) -> None:
    st.subheader("Detailed schedules and tables")

    st.markdown("**Debt schedules (facility-level)**")
    for name, df in result.debt_schedules.items():
        with st.expander(f"Debt schedule – {name}"):
            st.dataframe(df)

    st.markdown("**Pricing matrix (all SKUs x channels)**")
    with st.expander("Show price table"):
        st.dataframe(result.prices)

    st.markdown("**Working capital components**")
    wc_cols = [
        "receivables",
        "inventory",
        "other_current_assets",
        "payables",
        "other_current_liabilities",
        "net_working_capital",
        "change_in_nwc",
    ]
    st.dataframe(result.monthly[wc_cols])

    st.markdown("**CAPEX, depreciation, and net fixed assets**")
    st.dataframe(result.monthly[["capex", "depreciation", "net_fixed_assets"]])

    st.markdown("**Financing and equity flows**")
    st.dataframe(
        result.monthly[
            [
                "debt_draw",
                "debt_principal_payment",
                "equity_injection",
                "dividends",
                "cash",
            ]
        ]
    )


def _key_analytics_section(result, inputs: ModelInputs) -> None:
    st.subheader("Key Analytics")
    annual = result.annual.copy()
    monthly = result.monthly.copy()

    # Sensitivity Analysis
    st.markdown("### Sensitivity Analysis")
    base_revenue = float(annual["total_revenue"].iloc[0]) if "total_revenue" in annual.columns else 0.0
    base_ebitda = float(annual["ebitda"].iloc[0]) if "ebitda" in annual.columns else 0.0
    sens_df = pd.DataFrame(
        [
            {"case": "Price -10%", "revenue": base_revenue * 0.90, "ebitda": base_ebitda * 0.75},
            {"case": "Base", "revenue": base_revenue, "ebitda": base_ebitda},
            {"case": "Price +10%", "revenue": base_revenue * 1.10, "ebitda": base_ebitda * 1.25},
            {"case": "Volume -10%", "revenue": base_revenue * 0.90, "ebitda": base_ebitda * 0.80},
            {"case": "Volume +10%", "revenue": base_revenue * 1.10, "ebitda": base_ebitda * 1.20},
        ]
    )
    st.dataframe(sens_df)
    st.bar_chart(sens_df.set_index("case")[["revenue", "ebitda"]])

    # Monte Carlo simulation
    st.markdown("### Monte Carlo simulation")
    sims = st.slider("Simulations", 100, 2000, 500, step=100, key="mc_sims")
    if base_ebitda > 0:
        draws = np.random.normal(loc=base_ebitda, scale=base_ebitda * 0.20, size=sims)
        mc_df = pd.DataFrame({"ebitda_sim": draws})
        st.line_chart(mc_df.sort_values("ebitda_sim").reset_index(drop=True))
        st.write(
            {
                "mean": float(mc_df["ebitda_sim"].mean()),
                "p05": float(mc_df["ebitda_sim"].quantile(0.05)),
                "p50": float(mc_df["ebitda_sim"].quantile(0.50)),
                "p95": float(mc_df["ebitda_sim"].quantile(0.95)),
            }
        )

    # What-ifs analysis
    st.markdown("### What ifs analysis")
    what_if_price = st.slider("What-if price change %", -30, 30, 0, step=1, key="whatif_price")
    what_if_volume = st.slider("What-if volume change %", -30, 30, 0, step=1, key="whatif_volume")
    what_if_cost = st.slider("What-if direct cost change %", -30, 30, 0, step=1, key="whatif_cost")
    what_if_revenue = base_revenue * (1 + what_if_price / 100.0) * (1 + what_if_volume / 100.0)
    base_direct = float(annual["direct_costs"].iloc[0]) if "direct_costs" in annual.columns else 0.0
    what_if_direct = base_direct * (1 + what_if_cost / 100.0)
    what_if_ebitda = what_if_revenue - what_if_direct - float(annual["opex"].iloc[0])
    st.write({"revenue": what_if_revenue, "direct_costs": what_if_direct, "ebitda": what_if_ebitda})
    st.bar_chart(
        pd.DataFrame(
            {
                "base": [base_revenue, base_direct, base_ebitda],
                "what_if": [what_if_revenue, what_if_direct, what_if_ebitda],
            },
            index=["revenue", "direct_costs", "ebitda"],
        )
    )

    # Break-even analysis by product
    st.markdown("### Break-even analysis by product")
    prices = result.prices
    channel_weights = {"Wholesale": 0.40, "Retail": 0.30, "E-Commerce": 0.15, "On-Premise": 0.10, "Export": 0.05}
    be_rows = []
    fixed_pool = float(annual["opex"].iloc[0]) if "opex" in annual.columns else 0.0
    for _, sku in inputs.skus.iterrows():
        sid = sku["sku_id"]
        weighted_price = 0.0
        for ch, w in channel_weights.items():
            if (sid, ch) in prices.columns:
                weighted_price += float(prices[(sid, ch)].iloc[0]) * w
        unit_margin = max(weighted_price - float(sku["direct_cost_per_unit"]), 1e-6)
        be_rows.append(
            {"sku_id": sid, "name": sku["name"], "unit_margin": unit_margin, "break_even_units": fixed_pool / unit_margin}
        )
    st.dataframe(pd.DataFrame(be_rows))
    be_df = pd.DataFrame(be_rows).set_index("name")
    st.bar_chart(be_df[["break_even_units"]])

    # Scenario planning
    st.markdown("### Scenario planning")
    scen_df = pd.DataFrame(
        [
            {"scenario": "Downside", "revenue": base_revenue * 0.85, "ebitda": base_ebitda * 0.70},
            {"scenario": "Base", "revenue": base_revenue, "ebitda": base_ebitda},
            {"scenario": "Upside", "revenue": base_revenue * 1.15, "ebitda": base_ebitda * 1.30},
        ]
    )
    st.dataframe(scen_df)
    st.line_chart(scen_df.set_index("scenario")[["revenue", "ebitda"]])

    # Goal seek
    st.markdown("### Goal seek")
    target_ebitda = st.number_input("Target EBITDA (Year 1)", min_value=0.0, value=max(base_ebitda, 1.0), key="goal_ebitda")
    margin_rate = max((base_ebitda / base_revenue) if base_revenue else 0.0, 1e-6)
    required_revenue = target_ebitda / margin_rate
    st.write({"required_revenue": required_revenue, "implied_revenue_uplift_pct": (required_revenue / base_revenue - 1) * 100 if base_revenue else 0.0})
    st.bar_chart(
        pd.DataFrame(
            {"value": [base_revenue, required_revenue]},
            index=["current_revenue", "required_revenue"],
        )
    )

    # Debt service coverage ratio
    st.markdown("### Debt service coverage ratio")
    if {"debt_principal_payment", "interest_expense", "ebitda"}.issubset(monthly.columns):
        ds = monthly["debt_principal_payment"] + monthly["interest_expense"]
        dscr = np.where(ds > 0, monthly["ebitda"] / ds, np.nan)
        st.line_chart(pd.DataFrame({"DSCR": dscr}, index=monthly.index))
    else:
        st.info("DSCR uses monthly debt principal, interest, and EBITDA columns when available.")

    # Predictive analytics
    st.markdown("### Predictive analytics")
    if "total_revenue" in annual.columns and len(annual) >= 3:
        y = annual["total_revenue"].values.astype(float)
        x = np.arange(len(y))
        coeff = np.polyfit(x, y, 1)
        pred = coeff[0] * (x + 1) + coeff[1]
        pred_df = pd.DataFrame({"actual_revenue": y, "next_step_prediction": pred}, index=annual.index)
        st.dataframe(pred_df)
        st.line_chart(pred_df)
    else:
        st.info("Need at least 3 annual revenue points for trend-based prediction.")

    # Return diagnostics
    st.markdown("### Return diagnostics")
    val = result.valuation
    keys = ["enterprise_value", "equity_value", "investor_irr_annual", "investor_moic"]
    st.write({k: val.get(k, None) for k in keys})
    diag_vals = {k: val.get(k, np.nan) for k in keys if isinstance(val.get(k, np.nan), (int, float))}
    if diag_vals:
        st.bar_chart(pd.DataFrame({"value": diag_vals}))

    # Coverage & resilience
    st.markdown("### Coverage & resilience")
    cov = {}
    if {"cash", "debt_ending_balance"}.issubset(monthly.columns):
        cov["cash_to_debt_ratio_last_month"] = float(
            monthly["cash"].iloc[-1] / max(monthly["debt_ending_balance"].iloc[-1], 1e-6)
        )
    if {"cash", "opex"}.issubset(monthly.columns):
        cov["months_of_opex_covered_last_month"] = float(
            monthly["cash"].iloc[-1] / max(monthly["opex"].iloc[-1], 1e-6)
        )
    st.write(cov if cov else {"note": "Coverage metrics require cash/debt/opex monthly columns."})
    if cov:
        st.bar_chart(pd.DataFrame({"value": cov}))


def main() -> None:
    st.title("Microbrewery Financial Model")
    st.write(
        "Run the sample microbrewery financial model, tweak key valuation "
        "assumptions, and download the resulting statements."
    )

    tab_assumptions, tab_results, tab_details, tab_key_analytics = st.tabs([
        "Assumptions",
        "Results",
        "Assumption tables",
        "Key Analytics",
    ])

    with tab_assumptions:
        st.subheader("Core assumptions")
        months = st.slider("Months in projection", min_value=36, max_value=180, value=120, step=12)
        wacc = st.slider("WACC (annual)", min_value=0.05, max_value=0.20, value=0.122, step=0.005)
        exit_multiple = st.slider(
            "Exit EV/EBITDA multiple", min_value=4.0, max_value=12.0, value=8.0, step=0.5
        )
        price_inflation = st.slider(
            "Price inflation (annual)", min_value=0.0, max_value=0.05, value=0.015, step=0.0025
        )
        cost_inflation = st.slider(
            "Cost inflation (annual)", min_value=0.0, max_value=0.05, value=0.015, step=0.0025
        )
        dividend_start = st.number_input(
            "Dividend start month", min_value=0, max_value=months - 1, value=60
        )
        min_cash = st.number_input(
            "Minimum cash for sweep", min_value=0.0, value=1_500_000.0, step=100_000.0, format="%f"
        )

    cfg = ModelConfig(
        start_date="2025-01-01",
        months=months,
        pricing_cost_basis_month=24,
        price_inflation_annual=price_inflation,
        cost_inflation_annual=cost_inflation,
        tax_rate=0.25,
        wacc_annual=wacc,
        exit_ev_ebitda_multiple=exit_multiple,
        initial_cash=0.0,
    )

    div = DividendPolicy(
        enabled=True,
        model="cash_sweep",
        start_month=int(dividend_start),
        minimum_cash_position=float(min_cash),
        payout_ratio=0.25,
    )

    config_table_state = st.session_state.get("assump_data_config")
    if isinstance(config_table_state, pd.DataFrame) and not config_table_state.empty:
        row = config_table_state.iloc[0]
        cfg = replace(
            cfg,
            start_date=str(row.get("start_date", cfg.start_date)),
            months=int(row.get("months", cfg.months)),
            price_inflation_annual=float(row.get("price_inflation_annual", cfg.price_inflation_annual)),
            cost_inflation_annual=float(row.get("cost_inflation_annual", cfg.cost_inflation_annual)),
            tax_rate=float(row.get("tax_rate", cfg.tax_rate)),
            wacc_annual=float(row.get("wacc_annual", cfg.wacc_annual)),
            exit_ev_ebitda_multiple=float(row.get("exit_ev_ebitda_multiple", cfg.exit_ev_ebitda_multiple)),
        )
    dividend_table_state = st.session_state.get("assump_data_dividend")
    if isinstance(dividend_table_state, pd.DataFrame) and not dividend_table_state.empty:
        row = dividend_table_state.iloc[0]
        div = replace(
            div,
            enabled=bool(row.get("enabled", div.enabled)),
            model=str(row.get("model", div.model)),
            start_month=int(row.get("start_month", div.start_month)),
            minimum_cash_position=float(row.get("minimum_cash_position", div.minimum_cash_position)),
            payout_ratio=float(row.get("payout_ratio", div.payout_ratio)),
        )

    base_inputs = _build_sample_assumptions(cfg, div)
    inputs = _build_inputs_from_state(base_inputs)
    model = MicrobreweryFinancialModel(cfg, div, inputs)
    result = model.run()

    with tab_results:
        _valuation_section(result)
        _statement_section(result)
        _charts_section(result)
        _schedules_section(result)
        _download_section(result)

        st.caption(
            "The sample assumptions mirror the CLI example in "
            "`brewery_financial_model_all_in_one.py`. Adjust the sliders to "
            "explore scenarios."
        )

    with tab_key_analytics:
        _key_analytics_section(result, inputs)

    with tab_details:
        capex_df = pd.DataFrame(
            [
                {
                    "name": item.name,
                    "amount": item.amount,
                    "capex_month": item.capex_month,
                    "depreciation_years": item.depreciation_years,
                }
                for item in inputs.capex_items
            ]
        )
        debt_df = pd.DataFrame(
            [
                {
                    "name": fac.name,
                    "principal": fac.principal,
                    "annual_interest_rate": fac.annual_interest_rate,
                    "draw_month": fac.draw_month,
                    "grace_months": fac.grace_months,
                    "term_months": fac.term_months,
                    "repayment_type": fac.repayment_type,
                }
                for fac in inputs.debt_facilities
            ]
        )
        equity_df = pd.DataFrame(
            [{"month": k, "equity_injection": v} for k, v in sorted(inputs.equity_injections.items())]
        )
        config_df = pd.DataFrame(
            [
                {
                    "start_date": cfg.start_date,
                    "months": cfg.months,
                    "price_inflation_annual": cfg.price_inflation_annual,
                    "cost_inflation_annual": cfg.cost_inflation_annual,
                    "tax_rate": cfg.tax_rate,
                    "wacc_annual": cfg.wacc_annual,
                    "exit_ev_ebitda_multiple": cfg.exit_ev_ebitda_multiple,
                }
            ]
        )
        dividend_df = pd.DataFrame(
            [
                {
                    "enabled": div.enabled,
                    "model": div.model,
                    "start_month": div.start_month,
                    "minimum_cash_position": div.minimum_cash_position,
                    "payout_ratio": div.payout_ratio,
                }
            ]
        )
        opex_df = pd.DataFrame(
            [{"date": d, "opex_fixed_monthly": v} for d, v in inputs.opex_fixed_monthly.items()]
            if isinstance(inputs.opex_fixed_monthly, pd.Series)
            else [{"date": "all_months", "opex_fixed_monthly": float(inputs.opex_fixed_monthly)}]
        )
        other_income_df = pd.DataFrame(
            [{"date": d, "other_income_monthly": v} for d, v in inputs.other_income_monthly.items()]
            if isinstance(inputs.other_income_monthly, pd.Series)
            else [{"date": "all_months", "other_income_monthly": float(inputs.other_income_monthly)}]
        )

        _assumption_editor("Model config assumptions", "config", config_df)
        _assumption_editor("Dividend assumptions", "dividend", dividend_df)
        _assumption_editor("SKUs", "skus", inputs.skus)
        _assumption_editor("Channels", "channels", inputs.channels)
        _assumption_editor("Sales plan", "sales_plan", inputs.sales_plan)
        _assumption_editor("OPEX fixed monthly", "opex_fixed", opex_df)
        _assumption_editor("Other income monthly", "other_income", other_income_df)
        _assumption_editor("CAPEX schedule", "capex", capex_df)
        _assumption_editor("Debt facilities", "debt", debt_df)
        _assumption_editor("Equity injections", "equity", equity_df)


if __name__ == "__main__":
    main()
