"""Valuation and capital-structure utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Tuple

import numpy as np
import pandas as pd

from .config import ModelConfig, ProductConfig, VCInputs
from .portfolio import Portfolio
from .product import Product


class ValuationMethod(Protocol):
    def __call__(self, cashflows: pd.Series, discount_rate: float) -> float: ...


@dataclass
class ValuationResult:
    present_value: float
    terminal_value: float
    cashflows: pd.Series
    discount_rate: float
    success_prob: float
    option_adjustment: Optional[float] = None


def _discount_factors(rate: float, periods: int) -> np.ndarray:
    return 1.0 / (1.0 + rate) ** np.arange(1, periods + 1)


class ValuationEngine:
    """Runs rNPV and DCF calculations for products or portfolios."""

    def __init__(self, model_cfg: ModelConfig) -> None:
        self.cfg = model_cfg

    def _terminal_value(self, last_cashflow: float) -> float:
        g = self.cfg.terminal_growth_rate
        r = self.cfg.discount_rate
        if r <= g:
            g = r - 1e-4
        return last_cashflow * (1.0 + g) / (r - g)

    def run_product(self, product: Product) -> ValuationResult:
        table = product.build_cashflow_table(self.cfg)
        return self._run_cashflows(table["free_cash_flow"], success_prob=product.config.success_prob)

    def run_portfolio(self, portfolio: Portfolio) -> ValuationResult:
        table = portfolio.consolidated_table(self.cfg)
        cashflows = table.get("free_cash_flow", pd.Series(dtype=float))
        success_prob = np.prod([p.config.success_prob for p in portfolio]) if portfolio.products else 1.0
        return self._run_cashflows(cashflows, success_prob=success_prob)

    def _run_cashflows(self, cashflows: pd.Series, success_prob: float = 1.0) -> ValuationResult:
        discount = _discount_factors(self.cfg.discount_rate, len(cashflows))
        pv = float(np.dot(cashflows.values, discount))
        tv = self._terminal_value(float(cashflows.iloc[-1])) if len(cashflows) else 0.0
        pv_terminal = tv / (1.0 + self.cfg.discount_rate) ** len(cashflows)
        rnvp = (pv + pv_terminal) * success_prob * self.cfg.success_prob
        return ValuationResult(present_value=rnvp, terminal_value=tv, cashflows=cashflows, discount_rate=self.cfg.discount_rate, success_prob=success_prob)


@dataclass
class RealOptionRule:
    option_type: str  # expand|abandon|defer
    trigger_value: float
    scale_factor: float = 1.0
    cost: float = 0.0
    max_deferral_years: int = 0


class RealOptionsEngine:
    """Applies simple decision rules to option-adjust a valuation."""

    def __init__(self, rules: List[RealOptionRule]):
        self.rules = rules

    def adjust(self, valuation: ValuationResult, discount_rate: Optional[float] = None) -> ValuationResult:
        rate = discount_rate or valuation.discount_rate
        adjusted_pv = valuation.present_value
        for rule in self.rules:
            if rule.option_type == "expand":
                payoff = max(valuation.present_value * (rule.scale_factor - 1.0) - rule.cost, 0.0)
                adjusted_pv += payoff / (1.0 + rate)
            elif rule.option_type == "abandon" and valuation.present_value < rule.trigger_value:
                adjusted_pv = max(adjusted_pv, -rule.cost)
            elif rule.option_type == "defer":
                delay = min(rule.max_deferral_years, len(valuation.cashflows))
                adjusted_pv = adjusted_pv / (1.0 + rate) ** delay
                adjusted_pv -= rule.cost / (1.0 + rate) ** delay
        return ValuationResult(
            present_value=adjusted_pv,
            terminal_value=valuation.terminal_value,
            cashflows=valuation.cashflows,
            discount_rate=rate,
            success_prob=valuation.success_prob,
            option_adjustment=adjusted_pv - valuation.present_value,
        )


@dataclass
class FundingRound:
    name: str
    pre_money: float
    amount: float
    option_pool_pct: float = 0.0
    share_price: Optional[float] = None


@dataclass
class CapTable:
    rounds: List[FundingRound] = field(default_factory=list)
    shares_outstanding: float = 1_000_000.0

    def add_round(self, round_: FundingRound) -> None:
        self.rounds.append(round_)

    def simulate(self) -> pd.DataFrame:
        rows = []
        shares = self.shares_outstanding
        for rnd in self.rounds:
            price = rnd.share_price or self._implied_price(rnd.pre_money, shares)
            new_shares = rnd.amount / price
            pool_shares = shares * rnd.option_pool_pct
            post = rnd.pre_money + rnd.amount
            ownership = new_shares / (shares + new_shares + pool_shares)
            shares = shares + new_shares + pool_shares
            rows.append(
                {
                    "round": rnd.name,
                    "pre_money": rnd.pre_money,
                    "amount": rnd.amount,
                    "post_money": post,
                    "share_price": price,
                    "new_shares": new_shares,
                    "option_pool_shares": pool_shares,
                    "ownership": ownership,
                    "shares_outstanding": shares,
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _implied_price(pre_money: float, shares: float) -> float:
        return pre_money / max(shares, 1e-6)


class VCValuator:
    """Venture-style valuation with optional ML-driven exit multiples."""

    def __init__(self, vc_inputs: VCInputs, cap_table: Optional[CapTable] = None, multiples_model: Optional[Callable[[float], float]] = None):
        self.vc_inputs = vc_inputs
        self.cap_table = cap_table or CapTable()
        self.multiples_model = multiples_model

    def value(self, revenue_forecast: float) -> Dict[str, float]:
        exit_multiple = self._exit_multiple(revenue_forecast)
        exit_value = revenue_forecast * exit_multiple
        post_money = exit_value / (1.0 + self.vc_inputs.target_irr) ** self.vc_inputs.exit_year
        ownership = self.vc_inputs.ownership
        if self.cap_table.rounds:
            cap_df = self.cap_table.simulate()
            ownership = float(cap_df["ownership"].iloc[-1])
        investor_value = post_money * ownership
        return {
            "exit_multiple": exit_multiple,
            "exit_value": exit_value,
            "present_value": post_money,
            "investor_value": investor_value,
        }

    def _exit_multiple(self, revenue_forecast: float) -> float:
        if self.multiples_model is None:
            return self.vc_inputs.exit_multiple
        predicted = self.multiples_model(revenue_forecast)
        try:
            return float(predicted)
        except Exception:
            return self.vc_inputs.exit_multiple
