from finmodel.config import ModelConfig, ProductConfig
from finmodel.portfolio import Portfolio
from finmodel.product import Product


def test_consolidated_table_adds_products():
    cfg = ModelConfig(forecast_years=2)
    p1 = Product(ProductConfig(name="A", launch_year=0, peak_sales=100, ramp_years=1))
    p2 = Product(ProductConfig(name="B", launch_year=0, peak_sales=200, ramp_years=1))
    portfolio = Portfolio([p1, p2])

    table = portfolio.consolidated_table(cfg)
    assert not table.empty
    assert table.loc[1, "revenue"] == 300
