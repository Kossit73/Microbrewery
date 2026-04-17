import math

from finmodel import build_default_model
from finmodel.allocation import allocate_opex_by_drivers
from finmodel.opex_schemas import (
    OpexAllocationRule,
    OpexCostClassification,
    OpexCostPool,
    OpexDriverType,
    StepCapacityBand,
    StepFixedBand,
)


def test_imports_and_default_allocation_runs():
    model = build_default_model()
    report = model.allocate_opex()
    assert report.allocations
    assert report.summaries


def test_reconciliation_matches_pool_totals_by_year():
    model = build_default_model()
    report = model.allocate_opex()
    for s in report.summaries:
        assert math.isclose(s.total_pool_opex, s.total_allocated_opex, rel_tol=1e-9, abs_tol=1e-6)
        assert abs(s.reconciliation_gap) <= 1e-6
        assert math.isclose(sum(s.by_driver_type_totals.values()), s.total_pool_opex, rel_tol=1e-9, abs_tol=1e-6)


def test_active_and_inactive_sku_metrics():
    model = build_default_model()
    model.skus[0].include = False
    metrics = model.opex_metrics_by_sku_and_year()
    inactive = metrics[model.skus[0].sku_id]
    assert all(v["total_allocated_opex"] == 0.0 for v in inactive.values())

    active_id = model.skus[1].sku_id
    active = metrics[active_id]
    assert any(v["opex_per_unit"] >= 0.0 for v in active.values())
    assert any(v["opex_per_liter"] >= 0.0 for v in active.values())
    assert any(v["opex_per_case"] >= 0.0 for v in active.values())


def test_family_and_channel_scope_only_target_matching_rows():
    model = build_default_model()
    years = model.forecast_years()
    contexts = model.opex_contexts_by_sku_and_year()
    pool = OpexCostPool(
        name="Ales Marketing",
        category="Commercial",
        annual_amount_by_year={y: 1000.0 for y in years},
        driver_type=OpexDriverType.CHANNEL_REVENUE,
        product_family_scope=["Ales"],
        channel_scope=["Retail"],
    )

    report = allocate_opex_by_drivers(years, contexts, [pool])
    by_sku = {(a.sku_id, a.year): a.total_allocated_opex for a in report.allocations}
    for ctx in contexts:
        for y in years:
            allocated = by_sku[(ctx.sku_id, y)]
            if ctx.product_family == "Ales" and ctx.active:
                assert allocated >= 0.0
            else:
                assert allocated == 0.0


def test_blended_rule_weights_normalize_and_step_cost_logic():
    model = build_default_model()
    years = model.forecast_years()
    contexts = model.opex_contexts_by_sku_and_year()

    blended = OpexCostPool(
        name="Blended Pool",
        category="Ops",
        annual_amount_by_year={y: 2000.0 for y in years},
        driver_type=OpexDriverType.UNITS,
        rules=[
            OpexAllocationRule(driver=OpexDriverType.LITERS, weight=70),
            OpexAllocationRule(driver=OpexDriverType.UNITS, weight=20),
            OpexAllocationRule(driver=OpexDriverType.COMPLEXITY, weight=10),
        ],
    )
    step = OpexCostPool(
        name="Step Pool",
        category="Ops",
        annual_amount_by_year={y: 1000.0 for y in years},
        driver_type=OpexDriverType.STEP_CAPACITY,
        classification=OpexCostClassification.STEP_FIXED,
        rules=[
            OpexAllocationRule(
                driver=OpexDriverType.STEP_CAPACITY,
                weight=1.0,
                step_bands=[
                    StepCapacityBand(up_to=50_000, weight=1.0),
                    StepCapacityBand(up_to=200_000, weight=2.0),
                    StepCapacityBand(up_to=500_000, weight=3.0),
                ],
            )
        ],
        step_fixed_bands=[
            StepFixedBand(up_to_total_liters=500_000, annual_amount=1200.0),
            StepFixedBand(up_to_total_liters=2_000_000, annual_amount=1800.0),
        ],
    )
    report = allocate_opex_by_drivers(years, contexts, [blended, step])
    for s in report.summaries:
        assert math.isclose(s.total_pool_opex, s.total_allocated_opex, rel_tol=1e-9, abs_tol=1e-6)
        assert s.by_pool_totals["Step Pool"] in {1200.0, 1800.0}


def test_three_output_views_are_available():
    model = build_default_model()
    pool_view = model.opex_by_pool_view()
    driver_view = model.opex_by_driver_type_view()
    product_view = model.opex_by_product_view()

    assert pool_view
    assert driver_view
    assert product_view
