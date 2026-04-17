from pathlib import Path
import sys

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))

from brewery_financial_model_all_in_one import CostPoolInput, DividendPolicy, ModelConfig, ModelInputs, MicrobreweryFinancialModel


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
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            cost_pools=[
                CostPoolInput(name="Malt", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=0.5),
                CostPoolInput(name="Admin", cost_type="indirect", fixed_monthly_cost=1000.0, behavior="fixed", allocation_driver="units"),
            ],
        ),
    )

    result = model.run()
    assert not result.prices.empty
    assert float(result.prices.iloc[0, 0]) > 0.0
    assert "pool_view" in result.opex_allocation_views
    assert "driver_view" in result.opex_allocation_views
    assert "product_view" in result.opex_allocation_views
    assert "reconciliation_view" in result.opex_allocation_views
    assert float(result.monthly["direct_costs"].sum()) > 0.0


def test_all_in_one_supports_quarterly_sales_plan_frequency():
    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Test SKU",
                "direct_cost_per_unit": 2.10,
                "markup_pct": 0.65,
                "relative_opex_weight": 1.0,
            }
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 300.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=3, pricing_cost_basis_month=0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            sales_plan_frequency="quarterly",
            cost_pools=[
                CostPoolInput(name="Malt", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=0.5),
            ],
        ),
    )

    idx = model._timeline()
    monthly_units = model._units_matrix(idx).xs((1, "Retail"), axis=1)
    assert monthly_units.tolist() == [100.0, 100.0, 100.0]


def test_all_in_one_supports_yearly_sales_plan_frequency():
    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Test SKU",
                "direct_cost_per_unit": 2.10,
                "markup_pct": 0.65,
                "relative_opex_weight": 1.0,
            }
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 1200.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=12, pricing_cost_basis_month=0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            sales_plan_frequency="yearly",
            cost_pools=[
                CostPoolInput(name="Malt", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=0.5),
            ],
        ),
    )

    idx = model._timeline()
    monthly_units = model._units_matrix(idx).xs((1, "Retail"), axis=1)
    assert monthly_units.tolist() == [100.0] * 12
