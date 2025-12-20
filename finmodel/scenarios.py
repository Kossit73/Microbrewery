"""Scenario modelling utilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .config import MacroESGAssumptions, ModelConfig, ScenarioAssumptions
from .valuation import ValuationEngine, ValuationResult


@dataclass
class Scenario:
    name: str
    assumptions: ScenarioAssumptions


class ScenarioEngine:
    """Applies scenario levers to valuation inputs and returns deltas."""

    def __init__(self, valuation_engine: ValuationEngine):
        self.ve = valuation_engine

    def run_scenarios(self, base_result: ValuationResult, scenarios: List[Scenario]) -> Dict[str, ValuationResult]:
        results: Dict[str, ValuationResult] = {}
        for sc in scenarios:
            shifted_rate = self.ve.cfg.discount_rate + sc.assumptions.discount_rate_shift
            adjusted_cf = base_result.cashflows * sc.assumptions.revenue_multiplier
            adjusted_cf = adjusted_cf - (base_result.cashflows - adjusted_cf) * (sc.assumptions.cost_multiplier - 1.0)
            modified_cfg = ModelConfig(
                discount_rate=shifted_rate,
                terminal_growth_rate=self.ve.cfg.terminal_growth_rate,
                forecast_years=self.ve.cfg.forecast_years,
                tax_rate=self.ve.cfg.tax_rate,
                success_prob=self.ve.cfg.success_prob * sc.assumptions.success_prob_multiplier,
            )
            ve = ValuationEngine(modified_cfg)
            results[sc.name] = ve._run_cashflows(adjusted_cf, success_prob=base_result.success_prob)
        return results


class ScenarioReport:
    """Generates summary deltas for scenario runs."""

    @staticmethod
    def summarize(base: ValuationResult, scenarios: Dict[str, ValuationResult]) -> pd.DataFrame:
        rows = []
        for name, res in scenarios.items():
            rows.append(
                {
                    "scenario": name,
                    "rnpv_delta": res.present_value - base.present_value,
                    "ebitda_delta": res.cashflows.add(base.cashflows, fill_value=0.0).iloc[0] - base.cashflows.iloc[0],
                }
            )
        return pd.DataFrame(rows)


class ForecastScenarioBridge:
    """Converts forecast outputs into scenario objects."""

    def __init__(self, base_cfg: ModelConfig):
        self.cfg = base_cfg

    def build_price_scenarios_from_prophet(self, forecast_df: pd.DataFrame, base_col: str = "yhat") -> List[Scenario]:
        up = forecast_df[base_col] * 1.1
        down = forecast_df[base_col] * 0.9
        return [
            Scenario("prophet_upside", ScenarioAssumptions(revenue_multiplier=float(up.mean() / forecast_df[base_col].mean()))),
            Scenario("prophet_downside", ScenarioAssumptions(revenue_multiplier=float(down.mean() / forecast_df[base_col].mean()))),
        ]

    def build_severe_stress_scenario_from_prophet(self, forecast_df: pd.DataFrame, base_col: str = "yhat") -> Tuple[Scenario, pd.DataFrame]:
        base = forecast_df[base_col]
        severe = forecast_df.get("yhat_lower", base * 0.8)
        severe_multiplier = float(np.maximum(severe.mean() / base.mean(), 0.01))
        revenue_hit = 1.0 - severe_multiplier
        cost_multiplier = 1.0 + revenue_hit * 0.5
        discount_shift = revenue_hit * 0.02
        scenario = Scenario(
            name="severe_stress",
            assumptions=ScenarioAssumptions(
                revenue_multiplier=severe_multiplier,
                cost_multiplier=cost_multiplier,
                discount_rate_shift=discount_shift,
            ),
        )
        comparison = pd.DataFrame(
            {
                "base_rnpv": [base.mean()],
                "severe_rnpv": [severe.mean()],
                "revenue_multiplier": [severe_multiplier],
            }
        )
        return scenario, comparison
