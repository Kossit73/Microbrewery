"""Product-level cash flow builder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from .config import ModelConfig, ProductConfig


@dataclass
class Product:
    """Represents a single product/program and its deterministic cash flows."""

    config: ProductConfig

    def build_cashflow_table(self, model_cfg: ModelConfig) -> pd.DataFrame:
        """Construct a yearly cash-flow table for the product.

        This uses a simple S-curve ramp to peak sales, then flat, optionally ending at patent expiry.
        Costs are modeled as ratios of revenue. Working capital ties up cash proportional to revenue.
        """

        years = np.arange(model_cfg.forecast_years)
        sales_curve = self._build_sales_curve(years)
        revenue = sales_curve * self.config.peak_sales

        cogs = revenue * self.config.cogs_ratio
        opex = revenue * self.config.opex_ratio
        ebitda = revenue - cogs - opex
        depreciation = np.zeros_like(ebitda)
        ebit = ebitda - depreciation

        tax = np.maximum(ebit, 0.0) * model_cfg.tax_rate
        nopat = ebit - tax

        working_cap = revenue * self.config.working_cap_ratio
        delta_wc = np.diff(np.r_[0.0, working_cap])

        free_cash_flow = nopat - delta_wc

        df = pd.DataFrame(
            {
                "revenue": revenue,
                "cogs": cogs,
                "opex": opex,
                "ebitda": ebitda,
                "ebit": ebit,
                "tax": tax,
                "nopat": nopat,
                "delta_wc": delta_wc,
                "free_cash_flow": free_cash_flow,
            },
            index=pd.Index(years, name="year"),
        )
        return df

    def _build_sales_curve(self, years: np.ndarray) -> np.ndarray:
        ramp = np.minimum(years / max(self.config.ramp_years, 1), 1.0)
        curve = ramp
        if self.config.patent_years is not None:
            cutoff = self.config.patent_years
            curve = np.where(years <= cutoff, curve, 0.0)
        return curve
