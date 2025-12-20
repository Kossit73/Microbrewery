"""Streamlit UI for the microbrewery financial model.

This app wraps the existing `MicrobreweryFinancialModel` with the sample
assumptions from ``brewery_financial_model_all_in_one.py`` and lets users tweak
key valuation parameters before running the projection. The UI surfaces the
valuation summary and selected statement tables, plus an Excel download of the
full outputs.
"""

from __future__ import annotations

import io
from typing import Tuple

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
        ]
    )

    channels = pd.DataFrame(
        [
            {"channel": "Wholesale", "price_factor": 1.40},
            {"channel": "Retail", "price_factor": 2.00},
            {"channel": "E-Commerce", "price_factor": 1.75},
            {"channel": "On-Premise", "price_factor": 1.00},
        ]
    )

    u_sku1 = phase_growth_series(
        idx, start_month=3, start_units=8_000, monthly_growth=0.04, stop_month=None, cap_units=25_000
    )
    u_sku2 = phase_growth_series(
        idx, start_month=3, start_units=6_000, monthly_growth=0.04, stop_month=None, cap_units=20_000
    )

    channel_mix = {"Wholesale": 0.45, "Retail": 0.35, "E-Commerce": 0.15, "On-Premise": 0.05}
    rows = []
    for date in idx:
        for sku_id, series in [(1, u_sku1), (2, u_sku2)]:
            total_units = float(series.loc[date])
            for channel, share in channel_mix.items():
                rows.append({"date": date, "sku_id": sku_id, "channel": channel, "units": total_units * share})
    sales_plan = pd.DataFrame(rows)

    opex_fixed_monthly = 110_000.0
    other_income_monthly = pd.Series(0.0, index=idx)
    other_income_monthly.iloc[12:] = 15_000.0

    capex_items = [
        CapexItem(name="Land (non-depreciable)", amount=875_000, capex_month=0, depreciation_years=0),
        CapexItem(name="Building", amount=1_750_000, capex_month=0, depreciation_years=25),
        CapexItem(name="Brewhouse equipment", amount=1_250_000, capex_month=1, depreciation_years=10),
        CapexItem(name="Expansion equipment", amount=900_000, capex_month=60, depreciation_years=10),
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
    ]

    equity_injections = {0: 5_500_000.0, 12: 1_000_000.0}

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


def main() -> None:
    st.title("Microbrewery Financial Model")
    st.write(
        "Run the sample microbrewery financial model, tweak key valuation "
        "assumptions, and download the resulting statements."
    )

    tab_assumptions, tab_results, tab_details = st.tabs([
        "Assumptions",
        "Results",
        "Assumption tables",
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

    inputs, model = _run_model(cfg, div)
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

    with tab_details:
        st.markdown("### SKUs")
        st.dataframe(inputs.skus)

        st.markdown("### Channels")
        st.dataframe(inputs.channels)

        st.markdown("### CAPEX schedule")
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
        st.dataframe(capex_df)

        st.markdown("### Debt facilities")
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
        st.dataframe(debt_df)


if __name__ == "__main__":
    main()
