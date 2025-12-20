from finmodel.config import ModelConfig, ProductConfig
from finmodel.monte_carlo import MonteCarloEngine
from finmodel.product import Product
from finmodel.valuation import ValuationEngine


def test_monte_carlo_outputs_distribution():
    cfg = ModelConfig(discount_rate=0.1, forecast_years=3)
    prod = Product(ProductConfig(name="A", launch_year=0, peak_sales=100, ramp_years=1))
    ve = ValuationEngine(cfg)
    mc = MonteCarloEngine(ve, simulations=50, seed=1)
    draws = mc.simulate(prod)
    assert len(draws) == 50
    risk = mc.var_cvar(draws, alpha=0.9)
    assert "var" in risk and "cvar" in risk
