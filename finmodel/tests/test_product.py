import pandas as pd

from finmodel.config import ModelConfig, ProductConfig
from finmodel.product import Product


def test_build_cashflow_table_basic():
    cfg = ModelConfig(forecast_years=3)
    prod_cfg = ProductConfig(name="A", launch_year=0, peak_sales=100, ramp_years=1)
    prod = Product(prod_cfg)

    table = prod.build_cashflow_table(cfg)
    assert list(table.columns) == [
        "revenue",
        "cogs",
        "opex",
        "ebitda",
        "ebit",
        "tax",
        "nopat",
        "delta_wc",
        "free_cash_flow",
    ]
    assert table.loc[0, "revenue"] == prod_cfg.peak_sales * 0
    assert table.loc[1, "revenue"] == prod_cfg.peak_sales
    assert table["free_cash_flow"].iloc[1] != 0
