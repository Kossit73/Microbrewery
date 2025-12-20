import numpy as np

from finmodel.config import ModelConfig, ProductConfig
from finmodel.product import Product
from finmodel.valuation import RealOptionRule, RealOptionsEngine, ValuationEngine


def test_valuation_rnpv_positive():
    cfg = ModelConfig(discount_rate=0.1, forecast_years=3)
    prod = Product(ProductConfig(name="A", launch_year=0, peak_sales=100, ramp_years=1, success_prob=1.0))
    ve = ValuationEngine(cfg)
    res = ve.run_product(prod)
    assert res.present_value > 0
    assert np.isfinite(res.present_value)


def test_real_option_adjustment_expansion():
    cfg = ModelConfig(discount_rate=0.1, forecast_years=3)
    prod = Product(ProductConfig(name="A", launch_year=0, peak_sales=100, ramp_years=1))
    ve = ValuationEngine(cfg)
    base = ve.run_product(prod)
    roe = RealOptionsEngine([RealOptionRule(option_type="expand", trigger_value=0, scale_factor=1.2, cost=10)])
    adj = roe.adjust(base)
    assert adj.present_value >= base.present_value
