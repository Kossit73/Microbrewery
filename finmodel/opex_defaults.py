from __future__ import annotations

from typing import Dict, List

from .opex_schemas import (
    OpexAllocationRule,
    OpexCostClassification,
    OpexCostPool,
    OpexDriverType,
    StepCapacityBand,
    StepFixedBand,
)


DEFAULT_POOL_SHARES: Dict[str, float] = {
    "Indirect Labor": 0.20,
    "Utilities": 0.11,
    "Supplies": 0.06,
    "Marketing & Advertising": 0.11,
    "Events & Promotion": 0.05,
    "Insurance": 0.04,
    "Permits & License": 0.03,
    "Local Fees": 0.02,
    "Transport": 0.10,
    "Administrative Expense": 0.12,
    "Quality Control": 0.06,
    "Certificates": 0.02,
    "Professional Services": 0.04,
    "Other Expense": 0.02,
    "Contingencies": 0.02,
}


def build_default_opex_cost_pools(yearly_opex: Dict[str, float]) -> List[OpexCostPool]:
    pool_amounts = {
        name: {year: total * share for year, total in yearly_opex.items()}
        for name, share in DEFAULT_POOL_SHARES.items()
    }

    return [
        OpexCostPool(
            name="Indirect Labor",
            category="Operations",
            annual_amount_by_year=pool_amounts["Indirect Labor"],
            driver_type=OpexDriverType.STEP_CAPACITY,
            classification=OpexCostClassification.STEP_FIXED,
            rules=[
                OpexAllocationRule(
                    driver=OpexDriverType.STEP_CAPACITY,
                    weight=0.9,
                    step_bands=[
                        StepCapacityBand(up_to=50_000, weight=1.0),
                        StepCapacityBand(up_to=150_000, weight=1.5),
                        StepCapacityBand(up_to=500_000, weight=2.2),
                        StepCapacityBand(up_to=1_500_000, weight=3.0),
                    ],
                ),
                OpexAllocationRule(driver=OpexDriverType.COMPLEXITY, weight=0.1),
            ],
            step_fixed_bands=[
                StepFixedBand(
                    up_to_total_liters=500_000,
                    annual_amount=min(pool_amounts["Indirect Labor"].values()) * 0.85,
                ),
                StepFixedBand(
                    up_to_total_liters=1_000_000,
                    annual_amount=min(pool_amounts["Indirect Labor"].values()),
                ),
                StepFixedBand(
                    up_to_total_liters=2_000_000,
                    annual_amount=max(pool_amounts["Indirect Labor"].values()) * 1.05,
                ),
            ],
            notes="Step-fixed labor overhead with complexity overlay.",
        ),
        OpexCostPool("Utilities", "Production", pool_amounts["Utilities"], driver_type=OpexDriverType.LITERS, classification=OpexCostClassification.VARIABLE),
        OpexCostPool("Supplies", "Production", pool_amounts["Supplies"], driver_type=OpexDriverType.LITERS, classification=OpexCostClassification.VARIABLE),
        OpexCostPool("Marketing & Advertising", "Commercial", pool_amounts["Marketing & Advertising"], driver_type=OpexDriverType.CHANNEL_REVENUE, classification=OpexCostClassification.VARIABLE),
        OpexCostPool("Events & Promotion", "Commercial", pool_amounts["Events & Promotion"], driver_type=OpexDriverType.CHANNEL_UNITS, classification=OpexCostClassification.VARIABLE, channel_scope=["Events & Festivals", "On-Premise Sales"]),
        OpexCostPool("Insurance", "G&A", pool_amounts["Insurance"], driver_type=OpexDriverType.FIXED_EQUAL),
        OpexCostPool("Permits & License", "Regulatory", pool_amounts["Permits & License"], driver_type=OpexDriverType.ACTIVE_SKU, rules=[OpexAllocationRule(driver=OpexDriverType.FIXED_EQUAL, weight=0.4), OpexAllocationRule(driver=OpexDriverType.ACTIVE_SKU, weight=0.6)]),
        OpexCostPool("Local Fees", "Regulatory", pool_amounts["Local Fees"], driver_type=OpexDriverType.FIXED_EQUAL),
        OpexCostPool("Transport", "Logistics", pool_amounts["Transport"], driver_type=OpexDriverType.CHANNEL_UNITS),
        OpexCostPool("Administrative Expense", "G&A", pool_amounts["Administrative Expense"], driver_type=OpexDriverType.FIXED_EQUAL, rules=[OpexAllocationRule(driver=OpexDriverType.FIXED_EQUAL, weight=0.7), OpexAllocationRule(driver=OpexDriverType.ACTIVE_SKU, weight=0.3)]),
        OpexCostPool("Quality Control", "Quality", pool_amounts["Quality Control"], driver_type=OpexDriverType.LITERS, rules=[OpexAllocationRule(driver=OpexDriverType.LITERS, weight=0.8), OpexAllocationRule(driver=OpexDriverType.ACTIVE_SKU, weight=0.2)]),
        OpexCostPool("Certificates", "Regulatory", pool_amounts["Certificates"], driver_type=OpexDriverType.ACTIVE_SKU),
        OpexCostPool("Professional Services", "G&A", pool_amounts["Professional Services"], driver_type=OpexDriverType.FIXED_EQUAL),
        OpexCostPool("Other Expense", "G&A", pool_amounts["Other Expense"], driver_type=OpexDriverType.FIXED_EQUAL),
        OpexCostPool("Contingencies", "Reserve", pool_amounts["Contingencies"], driver_type=OpexDriverType.REVENUE),
    ]
