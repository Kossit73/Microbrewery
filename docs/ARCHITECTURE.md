# Valuation Toolkit Architecture

This package provides an extensible financial modelling toolkit for biotech/agro-style programs. It covers deterministic valuation (DCF/rNPV), scenarios, Monte Carlo, ML-based multiples, and UI surfaces.

## Core classes
- **ModelConfig**: global modelling switches (discount rate, terminal growth, success probability).
- **ProductConfig**: per-product economics (peak sales, costs, ramp, patent life).
- **Product**: builds yearly cash flow tables from a `ProductConfig` and `ModelConfig`.
- **Portfolio**: aggregates multiple `Product` cash flows.
- **ValuationEngine**: computes rNPV/DCF values and terminal value.
- **RealOptionsEngine**: applies simple expansion, abandonment, and deferral options on a valuation result.
- **VCValuator**: venture-style exit valuation, optionally driven by ML multiples and cap tables.
- **ScenarioEngine**: applies macro/ESG/revenue/cost levers and produces `ScenarioReport` deltas.
- **ForecastEngine**: tries naïve, ARIMA, and Prophet models with backtests to pick the best forecast.
- **ForecastScenarioBridge**: converts Prophet outputs into scenarios, including a severe-stress variant.
- **MonteCarloEngine**: simulates valuation distributions and computes VaR/CVaR.
- **AnalyticsEngine**: optional sklearn regression/classification helpers plus `MultiplesModel` for EV/EBITDA.

## Common workflows
### Single-product valuation
```python
from finmodel import ModelConfig, ProductConfig, Product, ValuationEngine
cfg = ModelConfig(discount_rate=0.12, forecast_years=10)
product = Product(ProductConfig(name="Alpha", launch_year=0, peak_sales=250_000))
valuation = ValuationEngine(cfg).run_product(product)
```

### Multi-scenario stress test
```python
from finmodel import Scenario, ScenarioAssumptions, ScenarioEngine, ValuationEngine
base = valuation  # ValuationResult from above
engine = ScenarioEngine(ValuationEngine(cfg))
scenarios = [Scenario("downside", ScenarioAssumptions(revenue_multiplier=0.8))]
results = engine.run_scenarios(base, scenarios)
```

### Prophet-driven severe stress
```python
from finmodel import ForecastScenarioBridge
bridge = ForecastScenarioBridge(cfg)
scenario, comparison = bridge.build_severe_stress_scenario_from_prophet(prophet_forecast_df)
```

### Monte Carlo VaR
```python
from finmodel import MonteCarloEngine
mc = MonteCarloEngine(ValuationEngine(cfg), simulations=500)
distribution = mc.simulate(product)
metrics = mc.var_cvar(distribution, alpha=0.95)
```

### Extending the toolkit
- Add a new forecast model by implementing a new method in `ForecastEngine` and registering it in `forecast()`.
- Add a new scenario type by extending `ScenarioAssumptions` and adjusting `ScenarioEngine` logic.
- Add a new valuation method by subclassing or wrapping `ValuationEngine` and reusing `ValuationResult`.
