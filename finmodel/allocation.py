from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Iterable, List

from .opex_schemas import (
    OpexAllocationReport,
    OpexAllocationRule,
    OpexAllocationSummary,
    OpexCostClassification,
    OpexCostPool,
    OpexDriverType,
    SKUCostContext,
    SKUOpexAllocation,
)

DEFAULT_CHANNEL_WEIGHTS: Dict[str, float] = {
    "Wholesale": 0.25,
    "Retail": 0.45,
    "E-Commerce": 0.15,
    "On-Premise Sales": 0.05,
    "Export": 0.07,
    "Events & Festivals": 0.03,
}


def normalize_rule_weights(rules: List[OpexAllocationRule]) -> List[OpexAllocationRule]:
    if not rules:
        return []
    total = sum(max(rule.weight, 0.0) for rule in rules)
    if total <= 0.0:
        equal_weight = 1.0 / len(rules)
        return [OpexAllocationRule(driver=rule.driver, weight=equal_weight, channel=rule.channel, step_bands=rule.step_bands) for rule in rules]
    return [OpexAllocationRule(driver=rule.driver, weight=max(rule.weight, 0.0) / total, channel=rule.channel, step_bands=rule.step_bands) for rule in rules]


def _in_scope(pool: OpexCostPool, ctx: SKUCostContext) -> bool:
    if not ctx.active:
        return False
    if pool.explicit_sku_scope and ctx.sku_id not in pool.explicit_sku_scope:
        return False
    if pool.product_family_scope and ctx.product_family not in pool.product_family_scope:
        return False
    return True


def _step_capacity_weight(value: float, rule: OpexAllocationRule) -> float:
    if not rule.step_bands:
        return max(value, 0.0)
    sorted_bands = sorted(rule.step_bands, key=lambda b: b.up_to)
    for band in sorted_bands:
        if value <= band.up_to:
            return max(band.weight, 0.0)
    return max(sorted_bands[-1].weight, 0.0)


def _driver_value(ctx: SKUCostContext, year: str, pool: OpexCostPool, rule: OpexAllocationRule) -> float:
    if rule.driver == OpexDriverType.FIXED_EQUAL:
        return 1.0
    if rule.driver == OpexDriverType.ACTIVE_SKU:
        return 1.0 if ctx.active else 0.0
    if rule.driver == OpexDriverType.UNITS:
        return float(ctx.units_sold_by_year.get(year, 0.0))
    if rule.driver == OpexDriverType.LITERS:
        return float(ctx.liters_sold_by_year.get(year, 0.0))
    if rule.driver == OpexDriverType.REVENUE:
        return float(ctx.revenue_by_year.get(year, 0.0))
    if rule.driver == OpexDriverType.COMPLEXITY:
        return float(ctx.complexity_score)
    if rule.driver == OpexDriverType.CHANNEL_REVENUE:
        channels = pool.channel_scope or ([rule.channel] if rule.channel else [])
        data = ctx.revenue_by_channel_by_year.get(year, {})
        if channels:
            return float(sum(data.get(ch, 0.0) for ch in channels))
        return float(sum(data.values()))
    if rule.driver == OpexDriverType.CHANNEL_UNITS:
        channels = pool.channel_scope or ([rule.channel] if rule.channel else [])
        data = ctx.units_by_channel_by_year.get(year, {})
        if channels:
            return float(sum(data.get(ch, 0.0) for ch in channels))
        return float(sum(data.values()))
    if rule.driver == OpexDriverType.EXPLICIT_WEIGHT:
        return float(ctx.explicit_weights.get(pool.name, pool.allocation_basis_weights.get(str(ctx.sku_id), 0.0)))
    if rule.driver == OpexDriverType.STEP_CAPACITY:
        liters = float(ctx.liters_sold_by_year.get(year, 0.0))
        return _step_capacity_weight(liters, rule)
    return 0.0


def _pool_amount_for_year(pool: OpexCostPool, year: str, contexts: Iterable[SKUCostContext]) -> float:
    if year in pool.monthly_amount_by_year:
        return float(pool.monthly_amount_by_year[year] * 12.0)

    base_amount = float(pool.annual_amount_by_year.get(year, 0.0))
    if pool.classification != OpexCostClassification.STEP_FIXED or not pool.step_fixed_bands:
        return base_amount

    total_liters = sum(ctx.liters_sold_by_year.get(year, 0.0) for ctx in contexts)
    bands = sorted(pool.step_fixed_bands, key=lambda b: b.up_to_total_liters)
    for band in bands:
        if total_liters <= band.up_to_total_liters:
            return float(band.annual_amount)
    return float(bands[-1].annual_amount)


def allocate_opex_by_drivers(years: List[str], sku_contexts: List[SKUCostContext], pools: List[OpexCostPool]) -> OpexAllocationReport:
    # sku_id -> year -> pool -> amount
    alloc_map: Dict[int, Dict[str, Dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    summaries: List[OpexAllocationSummary] = []

    for year in years:
        by_pool_totals: Dict[str, float] = {}
        for pool in pools:
            eligible = [ctx for ctx in sku_contexts if _in_scope(pool, ctx)]
            if not eligible:
                by_pool_totals[pool.name] = 0.0
                continue

            rules = normalize_rule_weights(pool.rules or [OpexAllocationRule(driver=pool.driver_type, weight=1.0)])
            pool_amount = _pool_amount_for_year(pool, year, eligible)
            by_pool_totals[pool.name] = pool_amount

            for rule in rules:
                vectors = {ctx.sku_id: max(_driver_value(ctx, year, pool, rule), 0.0) for ctx in eligible}
                denom = sum(vectors.values())
                if denom <= 0.0:
                    equal = 1.0 / len(eligible)
                    for ctx in eligible:
                        alloc_map[ctx.sku_id][year][pool.name] = alloc_map[ctx.sku_id][year].get(pool.name, 0.0) + pool_amount * rule.weight * equal
                    continue
                for ctx in eligible:
                    share = vectors[ctx.sku_id] / denom
                    alloc_map[ctx.sku_id][year][pool.name] = alloc_map[ctx.sku_id][year].get(pool.name, 0.0) + pool_amount * rule.weight * share

        total_pool = sum(by_pool_totals.values())
        total_alloc = sum(sum(alloc_map[ctx.sku_id].get(year, {}).values()) for ctx in sku_contexts)
        summaries.append(
            OpexAllocationSummary(
                year=year,
                total_pool_opex=total_pool,
                total_allocated_opex=total_alloc,
                reconciliation_gap=total_pool - total_alloc,
                by_pool_totals=by_pool_totals,
            )
        )

    allocations: List[SKUOpexAllocation] = []
    for ctx in sku_contexts:
        for year in years:
            by_pool = alloc_map[ctx.sku_id].get(year, {})
            total = float(sum(by_pool.values()))
            units = float(ctx.units_sold_by_year.get(year, 0.0))
            liters = float(ctx.liters_sold_by_year.get(year, 0.0))
            opex_per_unit = total / units if units > 0 else 0.0
            opex_per_liter = total / liters if liters > 0 else 0.0
            allocations.append(
                SKUOpexAllocation(
                    year=year,
                    sku_id=ctx.sku_id,
                    sku_name=ctx.sku_name,
                    total_allocated_opex=total,
                    opex_per_unit=opex_per_unit,
                    opex_per_liter=opex_per_liter,
                    by_pool=by_pool,
                )
            )
    return OpexAllocationReport(allocations=allocations, summaries=summaries)


def allocation_report_to_dict(report: OpexAllocationReport) -> Dict[str, List[Dict[str, object]]]:
    return {
        "allocations": [asdict(row) for row in report.allocations],
        "summaries": [asdict(row) for row in report.summaries],
    }
