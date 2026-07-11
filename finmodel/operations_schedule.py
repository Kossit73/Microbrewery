from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd


@dataclass
class BreweryOperationsPlan:
    monthly_summary: pd.DataFrame
    sku_schedule: pd.DataFrame
    resource_schedule: pd.DataFrame
    shipment_units_by_sku: pd.DataFrame
    production_units_by_sku: pd.DataFrame


def _year_numbers(idx: pd.DatetimeIndex) -> np.ndarray:
    return (np.arange(len(idx)) // 12) + 1


def _safe_numeric(value: object, default: float = 0.0) -> float:
    if pd.isna(value):
        return float(default)
    return float(pd.to_numeric(value, errors="coerce"))


def _year_value(row: pd.Series, year_num: int, default: float = 0.0) -> float:
    return _safe_numeric(row.get(f"Year {year_num}", default), default)


def _normalized_sku_operations(
    skus: pd.DataFrame,
    sku_operations: pd.DataFrame | None,
) -> pd.DataFrame:
    defaults = pd.DataFrame(
        {
            "sku_id": skus["sku_id"],
            "opening_fg_liters": 0.0,
            "brew_batch_liters": 2_500.0,
            "brewhouse_yield_pct": 1.0,
            "cellar_yield_pct": 1.0,
            "packaging_yield_pct": 1.0,
            "fermentation_days": 1.0,
            "conditioning_days": 0.0,
            "target_fg_days": 0.0,
        }
    )
    if sku_operations is None or sku_operations.empty:
        ops = defaults
    else:
        ops = sku_operations.copy()
        ops["sku_id"] = pd.to_numeric(ops["sku_id"], errors="coerce")
        ops = defaults.merge(ops, on="sku_id", how="left", suffixes=("", "_override"))
        for col in defaults.columns:
            if col == "sku_id":
                continue
            override_col = f"{col}_override"
            if override_col in ops.columns:
                ops[col] = pd.to_numeric(ops[override_col], errors="coerce").fillna(ops[col])
                ops = ops.drop(columns=[override_col])
    numeric_cols = [c for c in ops.columns if c != "sku_id"]
    default_lookup = defaults.set_index("sku_id").reindex(ops["sku_id"])
    for col in numeric_cols:
        fallback = pd.Series(default_lookup[col].to_numpy(), index=ops.index)
        ops[col] = pd.to_numeric(ops[col], errors="coerce").fillna(fallback)
    return ops.set_index("sku_id").sort_index()


def _resource_capacity_from_schedule(
    schedule: pd.DataFrame | None,
    idx: pd.DatetimeIndex,
    required_series: pd.Series,
    compute_capacity,
) -> tuple[pd.Series, pd.DataFrame]:
    if schedule is None or schedule.empty:
        return required_series.copy(), pd.DataFrame(columns=["date", "resource", "capacity_liters", "required_liters", "used_liters", "utilization_pct"])

    rows: List[Dict[str, float | str | pd.Timestamp]] = []
    capacities = pd.Series(0.0, index=idx, dtype=float)
    year_nums = _year_numbers(idx)
    for _, row in schedule.iterrows():
        if pd.isna(row.iloc[0]):
            continue
        name = str(row.get("resource_name", row.get("line_name", row.get("asset_name", "Resource")))).strip() or "Resource"
        per_month = []
        for pos, date in enumerate(idx):
            year_num = int(year_nums[pos])
            capacity_value = max(compute_capacity(row, year_num, date), 0.0)
            per_month.append(capacity_value)
            rows.append(
                {
                    "date": date,
                    "resource": name,
                    "capacity_liters": capacity_value,
                }
            )
        capacities = capacities.add(pd.Series(per_month, index=idx), fill_value=0.0)

    detail = pd.DataFrame(rows)
    if detail.empty:
        return capacities, detail
    detail["required_liters"] = detail["date"].map(required_series.to_dict()).astype(float)
    detail["used_liters"] = np.minimum(detail["required_liters"], detail["capacity_liters"])
    detail["utilization_pct"] = np.where(
        detail["capacity_liters"] > 0.0,
        detail["used_liters"] / detail["capacity_liters"],
        0.0,
    )
    return capacities, detail


def plan_brewery_operations(
    idx: pd.DatetimeIndex,
    demand_units_wide: pd.DataFrame,
    skus: pd.DataFrame,
    liters_per_unit: pd.Series,
    sku_operations: pd.DataFrame | None = None,
    brewhouse_schedule: pd.DataFrame | None = None,
    cellar_schedule: pd.DataFrame | None = None,
    packaging_schedule: pd.DataFrame | None = None,
) -> BreweryOperationsPlan:
    sku_ids = list(skus["sku_id"])
    if demand_units_wide.empty:
        zero_df = pd.DataFrame(0.0, index=idx, columns=sku_ids)
        return BreweryOperationsPlan(
            monthly_summary=pd.DataFrame(index=idx),
            sku_schedule=pd.DataFrame(),
            resource_schedule=pd.DataFrame(),
            shipment_units_by_sku=zero_df,
            production_units_by_sku=zero_df.copy(),
        )

    demand_units_by_sku = (
        demand_units_wide.T.groupby(level=0).sum().T.reindex(idx).fillna(0.0).reindex(columns=sku_ids, fill_value=0.0)
    )
    liters_lookup = liters_per_unit.reindex(sku_ids).fillna(0.0)
    demand_liters_by_sku = demand_units_by_sku.mul(liters_lookup, axis=1)

    ops = _normalized_sku_operations(skus, sku_operations)
    total_yield = (
        ops["brewhouse_yield_pct"].clip(lower=1e-6, upper=1.0)
        * ops["cellar_yield_pct"].clip(lower=1e-6, upper=1.0)
        * ops["packaging_yield_pct"].clip(lower=1e-6, upper=1.0)
    )
    cycle_days = (ops["fermentation_days"] + ops["conditioning_days"]).clip(lower=1.0)
    batch_liters = ops["brew_batch_liters"].clip(lower=1.0)

    opening_fg = ops["opening_fg_liters"].reindex(sku_ids).fillna(0.0).astype(float)
    shipment_units = pd.DataFrame(0.0, index=idx, columns=sku_ids)
    production_units = pd.DataFrame(0.0, index=idx, columns=sku_ids)
    summary_rows: List[Dict[str, object]] = []
    sku_rows: List[Dict[str, object]] = []
    resource_rows: List[Dict[str, object]] = []

    year_nums = _year_numbers(idx)
    for pos, date in enumerate(idx):
        year_num = int(year_nums[pos])
        days_in_month = int(date.days_in_month)
        demand_liters = demand_liters_by_sku.loc[date].reindex(sku_ids).fillna(0.0)

        if pos + 1 < len(idx):
            next_date = idx[pos + 1]
            next_days = int(next_date.days_in_month)
            next_demand_liters = demand_liters_by_sku.loc[next_date].reindex(sku_ids).fillna(0.0)
            target_fg = next_demand_liters.mul(ops["target_fg_days"].reindex(sku_ids).fillna(0.0) / max(next_days, 1))
        else:
            target_fg = demand_liters.mul(ops["target_fg_days"].reindex(sku_ids).fillna(0.0) / max(days_in_month, 1))

        required_packaged = (demand_liters + target_fg - opening_fg).clip(lower=0.0)
        required_brew_input = required_packaged.div(total_yield.reindex(sku_ids).replace(0.0, np.nan)).fillna(0.0)
        required_batches = required_brew_input.div(batch_liters.reindex(sku_ids).replace(0.0, np.nan)).fillna(0.0)

        total_required_packaged = float(required_packaged.sum())
        total_required_brew = float(required_brew_input.sum())
        weighted_cycle_days = float(
            np.average(cycle_days.reindex(sku_ids), weights=required_brew_input.reindex(sku_ids))
        ) if total_required_brew > 0.0 else float(cycle_days.mean())

        brew_required = pd.Series(total_required_brew, index=pd.Index([date]))
        packaged_required = pd.Series(total_required_packaged, index=pd.Index([date]))
        cellar_required = pd.Series(total_required_brew, index=pd.Index([date]))

        brew_cap_series, brew_detail = _resource_capacity_from_schedule(
            brewhouse_schedule,
            pd.DatetimeIndex([date]),
            brew_required,
            lambda row, yr, _: (
                _year_value(row, yr, 1.0)
                * _safe_numeric(row.get("liters_per_batch"), 0.0)
                * _safe_numeric(row.get("batches_per_day"), 0.0)
                * _safe_numeric(row.get("brew_days_per_month"), 0.0)
                * _safe_numeric(row.get("utilization_pct"), 1.0)
                * (1.0 - _safe_numeric(row.get("downtime_pct"), 0.0))
                * (1.0 - _safe_numeric(row.get("changeover_loss_pct"), 0.0))
            ),
        )
        brew_capacity = float(brew_cap_series.iloc[0])

        tank_liter_days_series, cellar_detail = _resource_capacity_from_schedule(
            cellar_schedule,
            pd.DatetimeIndex([date]),
            cellar_required,
            lambda row, yr, dt: (
                _year_value(row, yr, 1.0)
                * _safe_numeric(row.get("tank_count"), 0.0)
                * _safe_numeric(row.get("liters_per_tank"), 0.0)
                * dt.days_in_month
                * _safe_numeric(row.get("utilization_pct"), 1.0)
                * (1.0 - _safe_numeric(row.get("downtime_pct"), 0.0))
            ),
        )
        cellar_capacity = float(tank_liter_days_series.iloc[0] / max(weighted_cycle_days, 1.0))
        if not cellar_detail.empty:
            cellar_detail["capacity_liters"] = cellar_capacity
            cellar_detail["required_liters"] = total_required_brew
            cellar_detail["used_liters"] = min(total_required_brew, cellar_capacity)
            cellar_detail["utilization_pct"] = 0.0 if cellar_capacity <= 0.0 else cellar_detail["used_liters"] / cellar_capacity

        packaging_cap_series, packaging_detail = _resource_capacity_from_schedule(
            packaging_schedule,
            pd.DatetimeIndex([date]),
            packaged_required,
            lambda row, yr, _: (
                _year_value(row, yr, 1.0)
                * _safe_numeric(row.get("liters_per_hour"), 0.0)
                * _safe_numeric(row.get("hours_per_day"), 0.0)
                * _safe_numeric(row.get("run_days_per_month"), 0.0)
                * _safe_numeric(row.get("utilization_pct"), 1.0)
                * (1.0 - _safe_numeric(row.get("downtime_pct"), 0.0))
                * (1.0 - _safe_numeric(row.get("changeover_loss_pct"), 0.0))
            ),
        )
        packaging_capacity = float(packaging_cap_series.iloc[0])

        scale_candidates = [1.0]
        if total_required_brew > 0.0:
            scale_candidates.extend(
                [
                    brew_capacity / total_required_brew if brew_capacity >= 0.0 else 1.0,
                    cellar_capacity / total_required_brew if cellar_capacity >= 0.0 else 1.0,
                ]
            )
        if total_required_packaged > 0.0:
            scale_candidates.append(packaging_capacity / total_required_packaged if packaging_capacity >= 0.0 else 1.0)
        capacity_scale = max(min(scale_candidates), 0.0)
        capacity_scale = min(capacity_scale, 1.0)

        actual_packaged = required_packaged * capacity_scale
        actual_brew_input = required_brew_input * capacity_scale
        actual_batches = required_batches * capacity_scale
        available_fg = opening_fg + actual_packaged
        shipped_liters = pd.concat([demand_liters, available_fg], axis=1).min(axis=1)
        ending_fg = (available_fg - shipped_liters).clip(lower=0.0)
        unmet_liters = (demand_liters - shipped_liters).clip(lower=0.0)

        shipment_units.loc[date] = shipped_liters.div(liters_lookup.replace(0.0, np.nan)).fillna(0.0)
        production_units.loc[date] = actual_packaged.div(liters_lookup.replace(0.0, np.nan)).fillna(0.0)

        resource_caps = {
            "brewhouse": brew_capacity,
            "cellar": cellar_capacity,
            "packaging": packaging_capacity,
        }
        constraint_ratios = {
            name: (cap / total_required_brew if name != "packaging" and total_required_brew > 0.0 else cap / total_required_packaged if total_required_packaged > 0.0 else 1.0)
            for name, cap in resource_caps.items()
        }
        bottleneck = min(constraint_ratios, key=constraint_ratios.get) if capacity_scale < 0.999999 else "none"

        summary_rows.append(
            {
                "date": date,
                "demand_liters": float(demand_liters.sum()),
                "required_packaged_liters": total_required_packaged,
                "actual_packaged_liters": float(actual_packaged.sum()),
                "actual_shipped_liters": float(shipped_liters.sum()),
                "ending_fg_liters": float(ending_fg.sum()),
                "unmet_demand_liters": float(unmet_liters.sum()),
                "required_brew_input_liters": total_required_brew,
                "actual_brew_input_liters": float(actual_brew_input.sum()),
                "required_batches": float(required_batches.sum()),
                "actual_batches": float(actual_batches.sum()),
                "brewhouse_capacity_liters": brew_capacity,
                "cellar_capacity_liters": cellar_capacity,
                "packaging_capacity_liters": packaging_capacity,
                "capacity_scale": capacity_scale,
                "bottleneck_resource": bottleneck,
                "target_fg_liters": float(target_fg.sum()),
                "fg_target_gap_liters": float((target_fg - ending_fg).clip(lower=0.0).sum()),
            }
        )

        for sku_id in sku_ids:
            sku_rows.append(
                {
                    "date": date,
                    "sku_id": sku_id,
                    "opening_fg_liters": float(opening_fg.get(sku_id, 0.0)),
                    "demand_liters": float(demand_liters.get(sku_id, 0.0)),
                    "target_fg_liters": float(target_fg.get(sku_id, 0.0)),
                    "required_packaged_liters": float(required_packaged.get(sku_id, 0.0)),
                    "actual_packaged_liters": float(actual_packaged.get(sku_id, 0.0)),
                    "required_brew_input_liters": float(required_brew_input.get(sku_id, 0.0)),
                    "actual_brew_input_liters": float(actual_brew_input.get(sku_id, 0.0)),
                    "batch_count": float(actual_batches.get(sku_id, 0.0)),
                    "shipped_liters": float(shipped_liters.get(sku_id, 0.0)),
                    "ending_fg_liters": float(ending_fg.get(sku_id, 0.0)),
                    "unmet_demand_liters": float(unmet_liters.get(sku_id, 0.0)),
                    "total_yield_pct": float(total_yield.get(sku_id, 0.0)),
                    "cycle_days": float(cycle_days.get(sku_id, 0.0)),
                }
            )

        for resource_name, detail in (
            ("brewhouse", brew_detail),
            ("cellar", cellar_detail),
            ("packaging", packaging_detail),
        ):
            if detail.empty:
                resource_rows.append(
                    {
                        "date": date,
                        "resource": resource_name,
                        "capacity_liters": resource_caps[resource_name],
                        "required_liters": total_required_packaged if resource_name == "packaging" else total_required_brew,
                        "used_liters": float(actual_packaged.sum()) if resource_name == "packaging" else float(actual_brew_input.sum()),
                        "utilization_pct": 0.0
                        if resource_caps[resource_name] <= 0.0
                        else (
                            float(actual_packaged.sum()) / resource_caps[resource_name]
                            if resource_name == "packaging"
                            else float(actual_brew_input.sum()) / resource_caps[resource_name]
                        ),
                    }
                )
            else:
                resource_rows.extend(detail.to_dict("records"))

        opening_fg = ending_fg

    monthly_summary = pd.DataFrame(summary_rows).set_index("date")
    sku_schedule = pd.DataFrame(sku_rows)
    resource_schedule = pd.DataFrame(resource_rows)
    return BreweryOperationsPlan(
        monthly_summary=monthly_summary,
        sku_schedule=sku_schedule,
        resource_schedule=resource_schedule,
        shipment_units_by_sku=shipment_units,
        production_units_by_sku=production_units,
    )
