"""Monte Carlo simulation utilities."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .valuation import ValuationEngine, ValuationResult
from .product import Product
from .portfolio import Portfolio


class MonteCarloEngine:
    """Simulates valuation distributions and risk metrics."""

    def __init__(self, valuation_engine: ValuationEngine, simulations: int = 1000, seed: int = 0):
        self.ve = valuation_engine
        self.simulations = simulations
        self.rng = np.random.default_rng(seed)

    def simulate(self, product: Product) -> pd.Series:
        base_table = product.build_cashflow_table(self.ve.cfg)
        base_cf = base_table["free_cash_flow"].values
        draws = []
        for _ in range(self.simulations):
            shocks = self.rng.normal(loc=1.0, scale=0.1, size=len(base_cf))
            cf = base_cf * shocks
            val = self.ve._run_cashflows(pd.Series(cf), success_prob=product.config.success_prob)
            draws.append(val.present_value)
        return pd.Series(draws, name="rnpv_draws")

    @staticmethod
    def var_cvar(distribution: pd.Series, alpha: float = 0.95) -> dict:
        sorted_vals = distribution.sort_values()
        var_idx = int((1 - alpha) * len(sorted_vals))
        var = float(sorted_vals.iloc[var_idx])
        cvar = float(sorted_vals.iloc[: var_idx + 1].mean())
        return {"var": var, "cvar": cvar}
