from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from brewery_financial_model_all_in_one import DividendPolicy, ModelConfig, ModelInputs, MicrobreweryFinancialModel


def test_all_in_one_coerces_numeric_sku_and_channel_inputs():
    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Test SKU",
                "direct_cost_per_unit": "2.10",
                "markup_pct": "0.65",
                "relative_opex_weight": "1.0",
            }
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": "1.0"}])
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": "100"}])

    model = MicrobreweryFinancialModel(
        ModelConfig(months=3, pricing_cost_basis_month=0),
        DividendPolicy(enabled=False),
        ModelInputs(skus=skus, channels=channels, sales_plan=sales, opex_fixed_monthly=1000.0),
    )

    result = model.run()
    assert not result.prices.empty
    assert float(result.prices.iloc[0, 0]) > 0.0
    assert "pool_view" in result.opex_allocation_views
    assert "driver_view" in result.opex_allocation_views
    assert "product_view" in result.opex_allocation_views
    assert "reconciliation_view" in result.opex_allocation_views
