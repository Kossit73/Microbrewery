"""Streamlit UI skeleton for interacting with the valuation package."""
from __future__ import annotations

import streamlit as st

from .config import ModelConfig, ProductConfig
from .product import Product
from .valuation import ValuationEngine


def render_demo() -> None:
    st.title("Valuation Toolkit Demo")
    st.sidebar.header("Product inputs")
    peak_sales = st.sidebar.number_input("Peak sales", value=100_000.0, step=10_000.0)
    success_prob = st.sidebar.slider("Success probability", 0.0, 1.0, 0.8)
    discount_rate = st.sidebar.slider("Discount rate", 0.05, 0.3, 0.12)

    cfg = ModelConfig(discount_rate=discount_rate)
    product_cfg = ProductConfig(name="Demo", launch_year=0, peak_sales=peak_sales, success_prob=success_prob)
    product = Product(product_cfg)

    engine = ValuationEngine(cfg)
    result = engine.run_product(product)

    st.metric("rNPV", f"{result.present_value:,.0f}")
    st.line_chart(result.cashflows)


def main() -> None:
    render_demo()


if __name__ == "__main__":
    main()
