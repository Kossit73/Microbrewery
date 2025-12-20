import pandas as pd

from finmodel.config import ModelConfig, ProductConfig, ScenarioAssumptions
from finmodel.product import Product
from finmodel.scenarios import ForecastScenarioBridge, Scenario, ScenarioEngine
from finmodel.valuation import ValuationEngine


def test_scenario_engine_applies_multipliers():
    cfg = ModelConfig(discount_rate=0.1, forecast_years=3)
    prod = Product(ProductConfig(name="A", launch_year=0, peak_sales=100, ramp_years=1))
    ve = ValuationEngine(cfg)
    base = ve.run_product(prod)

    se = ScenarioEngine(ve)
    scenarios = [Scenario(name="downside", assumptions=ScenarioAssumptions(revenue_multiplier=0.5))]
    results = se.run_scenarios(base, scenarios)
    assert "downside" in results
    assert results["downside"].present_value < base.present_value


def test_severe_stress_bridge():
    cfg = ModelConfig(discount_rate=0.1)
    bridge = ForecastScenarioBridge(cfg)
    dates = pd.date_range("2020-01-01", periods=5, freq="A")
    df = pd.DataFrame({"ds": dates, "yhat": [1, 2, 3, 4, 5]}).set_index("ds")
    scenario, comparison = bridge.build_severe_stress_scenario_from_prophet(df, base_col="yhat")
    assert scenario.assumptions.revenue_multiplier < 1.0
    assert not comparison.empty
