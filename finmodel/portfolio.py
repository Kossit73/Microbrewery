"""Portfolio aggregation utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

import pandas as pd

from .config import ModelConfig
from .product import Product


@dataclass
class Portfolio:
    """Collection of products with convenience consolidation helpers."""

    products: List[Product] = field(default_factory=list)

    def consolidated_table(self, model_cfg: ModelConfig) -> pd.DataFrame:
        tables = [p.build_cashflow_table(model_cfg) for p in self.products]
        if not tables:
            return pd.DataFrame()
        combined = sum(tables)
        combined.index.name = "year"
        return combined

    def add_product(self, product: Product) -> None:
        self.products.append(product)

    def __iter__(self) -> Iterable[Product]:
        return iter(self.products)
