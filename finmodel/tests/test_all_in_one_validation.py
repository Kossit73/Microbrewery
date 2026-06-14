from io import BytesIO
from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

from brewery_financial_model_all_in_one import (
    CostPoolInput,
    DividendPolicy,
    ModelConfig,
    ModelInputs,
    MicrobreweryFinancialModel,
    OtherIncomeItem,
    write_comprehensive_excel_report,
)


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


def test_all_in_one_aggregates_other_income_items():
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
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 100.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=2, pricing_cost_basis_month=0, cost_inflation_annual=0.0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            other_income_items=[
                OtherIncomeItem(other_income_name="Sponsorships", amount=100.0, active=True),
                OtherIncomeItem(other_income_name="Other Income 2", amount=50.0, active=True),
                OtherIncomeItem(other_income_name="Other Income 3", amount=999.0, active=False),
            ],
            cost_pools=[
                CostPoolInput(name="Malt", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=0.5),
            ],
        ),
    )

    result = model.run()
    assert result.monthly["other_income"].tolist() == [150.0, 150.0]


def test_all_in_one_handles_empty_sales_plan_without_alignment_error():
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
    empty_sales = pd.DataFrame(columns=["date", "sku_id", "channel", "units"])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=2, pricing_cost_basis_month=0, cost_inflation_annual=0.0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=empty_sales,
            cost_pools=[
                CostPoolInput(name="Admin", cost_type="indirect", behavior="fixed", allocation_driver="units", fixed_monthly_cost=0.0),
            ],
        ),
    )

    result = model.run()
    assert result.monthly["revenue"].tolist() == [0.0, 0.0]


def test_all_in_one_handles_out_of_horizon_quarterly_sales_without_keyerror():
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
    # Deliberately outside model horizon (model starts in 2025).
    sales = pd.DataFrame([{"date": "2030-01-01", "sku_id": 1, "channel": "Retail", "units": 1200.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=12, pricing_cost_basis_month=0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            sales_plan_frequency="quarterly",
        ),
    )

    result = model.run()
    assert result.monthly["revenue"].sum() == 0.0


def test_all_in_one_handles_missing_sku_and_channel_columns_in_driver_xs_paths():
    skus = pd.DataFrame(
        [
            {"sku_id": 1, "name": "SKU 1 500ml", "direct_cost_per_unit": 2.10, "markup_pct": 0.65, "relative_opex_weight": 1.0},
            {"sku_id": 2, "name": "SKU 2 330ml", "direct_cost_per_unit": 2.30, "markup_pct": 0.60, "relative_opex_weight": 1.2},
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}, {"channel": "Wholesale", "price_factor": 0.8}])
    # Only sku_id=1 / Retail appears in sales.
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 100.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=2, pricing_cost_basis_month=0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            cost_pools=[
                CostPoolInput(name="Liters Pool", cost_type="indirect", behavior="variable", allocation_driver="liters", unit_variable_cost=0.1),
                CostPoolInput(name="Complexity Pool", cost_type="indirect", behavior="variable", allocation_driver="complexity", unit_variable_cost=0.2),
                CostPoolInput(name="Missing Channel Pool", cost_type="indirect", behavior="variable", allocation_driver="channel_units", channel="E-Commerce", unit_variable_cost=0.3),
            ],
        ),
    )

    result = model.run()
    assert "opex" in result.monthly.columns


def test_all_in_one_derives_direct_cost_per_unit_from_direct_pools():
    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Test SKU",
                "markup_pct": 0.65,
                "relative_opex_weight": 1.0,
            }
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 100.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=1, pricing_cost_basis_month=0, cost_inflation_annual=0.0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            cost_pools=[
                CostPoolInput(name="Direct Variable Pool", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=2.0),
            ],
        ),
    )

    result = model.run()
    assert result.monthly["direct_costs"].tolist() == [200.0]


def test_all_in_one_allows_direct_cost_override():
    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Test SKU",
                "markup_pct": 0.65,
                "relative_opex_weight": 1.0,
                "direct_cost_per_unit_override": 3.0,
            }
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 100.0}])

    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=1, pricing_cost_basis_month=0, cost_inflation_annual=0.0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            cost_pools=[
                CostPoolInput(name="Direct Variable Pool", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=2.0),
            ],
        ),
    )

    result = model.run()
    assert result.monthly["direct_costs"].tolist() == [300.0]


def test_all_in_one_sales_frequency_totals_are_consistent():
    skus = pd.DataFrame(
        [
            {
                "sku_id": 1,
                "name": "Test SKU",
                "markup_pct": 0.50,
                "relative_opex_weight": 1.0,
            }
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    direct_pool = [CostPoolInput(name="Direct Variable Pool", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=1.0)]

    monthly_sales = pd.DataFrame([{"date": f"2025-{m:02d}-01", "sku_id": 1, "channel": "Retail", "units": 100.0} for m in range(1, 13)])
    quarterly_sales = pd.DataFrame(
        [
            {"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 300.0},
            {"date": "2025-04-01", "sku_id": 1, "channel": "Retail", "units": 300.0},
            {"date": "2025-07-01", "sku_id": 1, "channel": "Retail", "units": 300.0},
            {"date": "2025-10-01", "sku_id": 1, "channel": "Retail", "units": 300.0},
        ]
    )
    yearly_sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 1200.0}])

    def run_model(sales_plan: pd.DataFrame, freq: str):
        model = MicrobreweryFinancialModel(
            ModelConfig(start_date="2025-01-01", months=12, pricing_cost_basis_month=0, cost_inflation_annual=0.0, price_inflation_annual=0.0),
            DividendPolicy(enabled=False),
            ModelInputs(
                skus=skus.copy(),
                channels=channels.copy(),
                sales_plan=sales_plan,
                sales_plan_frequency=freq,  # type: ignore[arg-type]
                cost_pools=direct_pool,
            ),
        )
        return model.run()

    monthly_result = run_model(monthly_sales, "monthly")
    quarterly_result = run_model(quarterly_sales, "quarterly")
    yearly_result = run_model(yearly_sales, "yearly")

    assert monthly_result.monthly["revenue"].sum() == quarterly_result.monthly["revenue"].sum() == yearly_result.monthly["revenue"].sum()


def test_comprehensive_excel_report_contains_requested_sections():
    skus = pd.DataFrame(
        [
            {"sku_id": 1, "name": "Test SKU", "markup_pct": 0.50, "relative_opex_weight": 1.0},
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    sales = pd.DataFrame([{"date": "2025-01-01", "sku_id": 1, "channel": "Retail", "units": 100.0}])
    model = MicrobreweryFinancialModel(
        ModelConfig(start_date="2025-01-01", months=12, pricing_cost_basis_month=0),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            cost_pools=[CostPoolInput(name="Direct Variable Pool", cost_type="direct", behavior="variable", allocation_driver="units", unit_variable_cost=1.0)],
        ),
    )
    result = model.run()

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        write_comprehensive_excel_report(result, writer)
    output.seek(0)
    workbook = pd.ExcelFile(output, engine="openpyxl")
    sheets = set(workbook.sheet_names)

    expected = {
        "Annual_Performance_IS",
        "Annual_Position_BS",
        "Annual_Cash_Flow",
        "Graphs_and_Plots",
        "Cash_vs_Debt_EndBal",
        "Driver_OPEX_Views",
        "Key_Analytics",
        "13_direct_labor_detail",
        "13_indirect_labor_detail",
        "13_inventory_detail",
        "13_payables_detail",
        "13_receivables_detail",
    }
    assert expected.issubset(sheets)


def test_all_in_one_schedule_driven_components_flow_through_outputs():
    skus = pd.DataFrame(
        [
            {"sku_id": 1, "name": "Test SKU 500ml", "markup_pct": 0.50, "relative_opex_weight": 1.0},
        ]
    )
    channels = pd.DataFrame([{"channel": "Retail", "price_factor": 1.0}])
    sales = pd.DataFrame(
        [{"date": f"2025-{month:02d}-01", "sku_id": 1, "channel": "Retail", "units": 100.0} for month in range(1, 13)]
    )

    model = MicrobreweryFinancialModel(
        ModelConfig(
            start_date="2025-01-01",
            months=12,
            pricing_cost_basis_month=0,
            cost_inflation_annual=0.0,
            price_inflation_annual=0.0,
            tax_rate=0.0,
            initial_cash=10_000.0,
            revolver_limit=0.0,
            revolver_target_cash=0.0,
            other_current_assets_pct_revenue=0.0,
            other_current_liabilities_pct_direct_costs=0.0,
            temporary_labor_premium_pct=0.0,
        ),
        DividendPolicy(enabled=False),
        ModelInputs(
            skus=skus,
            channels=channels,
            sales_plan=sales,
            cost_pools=[
                CostPoolInput(
                    name="Direct Variable Pool",
                    cost_type="direct",
                    behavior="variable",
                    allocation_driver="units",
                    unit_variable_cost=2.0,
                ),
            ],
            direct_labor_schedule=pd.DataFrame(
                [
                    {
                        "role": "Brewers",
                        "allocation_driver": "units",
                        "scope": "global",
                        "target_sku_id": pd.NA,
                        "monthly_cost_per_fte": 1_000.0,
                        "annual_raise_pct": 0.0,
                        "benefits_pct": 0.0,
                        "payroll_tax_pct": 0.0,
                        "overtime_pct": 0.0,
                        "capacity_liters_per_fte_month": 100.0,
                        "Year 1": 1.0,
                    }
                ]
            ),
            indirect_labor_schedule=pd.DataFrame(
                [
                    {
                        "role": "Back Office",
                        "allocation_driver": "fixed",
                        "scope": "global",
                        "target_sku_id": pd.NA,
                        "monthly_cost_per_fte": 500.0,
                        "annual_raise_pct": 0.0,
                        "benefits_pct": 0.0,
                        "payroll_tax_pct": 0.0,
                        "overtime_pct": 0.0,
                        "capacity_liters_per_fte_month": 0.0,
                        "Year 1": 1.0,
                    }
                ]
            ),
            receivables_schedule=pd.DataFrame(
                [
                    {
                        "channel": "Retail",
                        "trade_spend_pct": 0.10,
                        "returns_pct": 0.05,
                        "bad_debt_pct": 0.02,
                        "Year 1": 30.0,
                    }
                ]
            ),
            inventory_schedule=pd.DataFrame(
                [
                    {
                        "stage": "FG",
                        "cost_share_pct": 1.0,
                        "writeoff_pct": 0.02,
                        "reserve_pct": 0.10,
                        "Year 1": 20.0,
                    }
                ]
            ),
            payables_schedule=pd.DataFrame(
                [
                    {
                        "supplier_category": "Raw Materials",
                        "cost_share_pct": 1.0,
                        "early_pay_discount_pct": 0.02,
                        "discount_capture_pct": 0.50,
                        "Year 1": 25.0,
                    }
                ]
            ),
        ),
    )

    result = model.run()
    month_one = result.monthly.iloc[0]
    annual = result.annual.iloc[0]

    assert month_one["direct_labor_cost"] == pytest.approx(1_000.0)
    assert month_one["indirect_labor_cost"] == pytest.approx(500.0)
    assert month_one["gross_revenue"] == pytest.approx(1_800.0)
    assert month_one["net_revenue"] == pytest.approx(1_530.0)
    assert month_one["bad_debt_expense"] == pytest.approx(30.6)
    assert month_one["inventory_writeoff"] == pytest.approx(4.0)
    assert month_one["payable_discount_benefit"] == pytest.approx(2.0)
    assert month_one["direct_costs"] == pytest.approx(1_202.0)
    assert month_one["receivables"] == pytest.approx(1_530.0 * 30.0 / 365.0)
    assert month_one["inventory"] == pytest.approx((200.0 * 20.0 / 365.0) * 0.90)
    assert month_one["inventory_reserve"] == pytest.approx((200.0 * 20.0 / 365.0) * 0.10)
    assert month_one["payables"] == pytest.approx(200.0 * 25.0 / 365.0)
    assert month_one["total_debt_ending_balance"] == pytest.approx(0.0)
    assert annual["receivables"] == pytest.approx(month_one["receivables"])
    assert annual["inventory"] == pytest.approx(month_one["inventory"])
    assert annual["payables"] == pytest.approx(month_one["payables"])
    assert annual["total_debt_ending_balance"] == pytest.approx(0.0)
    assert {
        "receivables_detail",
        "inventory_detail",
        "payables_detail",
        "direct_labor_detail",
        "indirect_labor_detail",
    }.issubset(result.supporting_schedules.keys())
