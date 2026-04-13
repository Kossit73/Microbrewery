# Detailed Schedule Roadmap for the Microbrewery Model

This document reviews the current model and provides a practical blueprint for extending it into a more detailed, schedule-driven operating and valuation model.

## 1) Current-state review (what already exists)

The current engine already includes several foundational schedules:

- Revenue/volume by SKU and channel (with inflation-aware pricing).
- Direct costs, fixed OPEX, CAPEX, and straight-line depreciation.
- Working capital via DSO/DIO/DPO-style assumptions.
- Debt facilities (linear, annuity, interest-only-then-linear, and specified repayment patterns).
- Dividend logic, monthly and annual statements, plus DCF outputs.

These are strong building blocks, but many assumptions are still encoded as scalar ratios, which limits operational realism and explainability.

## 2) Recommended target model architecture

Use a **schedule-first** design where each major business area is its own module with:

1. `inputs` (auditable assumptions),
2. `calc` (deterministic roll-forward logic),
3. `outputs` (tables consumed by statements and dashboards),
4. `checks` (balance / integrity constraints).

Suggested data contract for every schedule:

- `base_case`: canonical assumptions.
- `scenario_overrides`: sparse overrides by case (downside/upside/stress).
- `driver_granularity`: monthly by default, optionally weekly for demand and production.
- `id_fields`: SKU, channel, facility, supplier, and region.

## 3) Priority schedule stack (recommended build order)

### Phase 1: Commercial and gross margin schedules (highest ROI)

1. **Net Revenue Bridge Schedule**
   - Build: gross list price -> trade spend -> promo discount -> returns/spoilage -> net revenue.
   - Grain: SKU x channel x month.
   - Why first: immediately improves forecast quality and margin diagnostics.

2. **BOM + Packaging COGS Schedule**
   - Build: ingredient and packaging BOM by SKU, with yield-loss and inflation by supplier.
   - Add: utility drivers (kWh, steam, CO2, water) per hl or batch.
   - Why first: turns COGS from blended percentages into traceable cost drivers.

### Phase 2: Operating engine schedules

3. **Payroll and Headcount Roll-forward**
   - Build: opening HC + hires - exits by function, with salary bands, benefits, payroll tax, and bonuses.
   - Output: cash payroll, accrued payroll, and fully loaded labor per unit.

4. **Logistics and Fulfillment Schedule**
   - Build: warehouse, 3PL, freight, and last-mile costs by channel/geography.
   - Output: delivery cost per unit and service-level cost trade-offs.

5. **Capacity and Production Plan Schedule**
   - Build: tank / line capacity, utilization, changeover losses, downtime, and maintenance windows.
   - Output: available volume, bottlenecks, outsourcing needs, and capex triggers.

### Phase 3: Balance-sheet and financing schedules

6. **Inventory Aging Schedule (RM / WIP / FG)**
   - Build: receipts, consumption, production completion, sales depletion, and write-offs.
   - Output: quantity and value by stage plus spoilage exposure.

7. **AR/AP Aging Schedules**
   - Build: invoices, collections, bad-debt assumptions, payables terms, and discount capture.
   - Output: effective DSO/DPO, overdue buckets, and cash-conversion insights.

8. **Debt + Revolver + Covenant Schedule**
   - Build: existing debt logic plus revolver sweeps and covenant tests (DSCR, leverage, coverage).
   - Output: covenant headroom and automatic breach flags.

9. **Tax Schedule (excise + VAT/GST + income tax)**
   - Build: product/channel-specific indirect taxes, deferred tax, and carryforwards.
   - Output: tax bridge from gross sales to cash taxes.

### Phase 4: Decision and risk schedules

10. **Scenario Driver Schedule**
    - Build: centralized scenario overlays for price, demand, commodity, FX, labor, and regulatory shifts.
    - Output: one-click downside/base/upside/stress cases.

11. **Valuation Bridge Schedule**
    - Build: EBITDA -> EBIT -> FCFF -> PV -> terminal value with explicit sensitivity tables.
    - Output: investor-ready reconciliation and confidence intervals.

## 4) Minimal table design for each schedule

To keep maintenance manageable, standardize a long-format table schema:

- Keys: `date`, `schedule`, `entity_id`, `entity_type`, `scenario`.
- Inputs: `assumption_name`, `assumption_value`, `units`, `source`.
- Outputs: `metric_name`, `metric_value`.
- Governance: `version_id`, `updated_by`, `updated_at`, `change_reason`.

This avoids one-off wide tables and makes exports, auditing, and scenario comparisons much easier.

## 5) Implementation guidance for this repository

Given the current codebase structure, implement schedules as separate modules under `finmodel/` (or a new `finmodel/schedules/` package) and keep orchestration in one service layer.

Recommended near-term refactor path:

1. Introduce typed dataclasses for schedule inputs (commercial, operations, working capital, financing, tax).
2. Add schedule builders that each return a DataFrame with standard keys.
3. Replace scalar-ratio shortcuts in core calculations with schedule outputs.
4. Add schedule-level tests (shape, reconciliation, sign conventions, edge cases).
5. Expose schedule tables in Streamlit and Excel export for traceability.

## 6) Quality gates (must-have checks)

Add automated checks before publishing any run:

- P&L, balance sheet, and cash flow tie-outs.
- Opening + movements = closing checks for debt, fixed assets, and working-capital accounts.
- No negative physical volumes unless explicitly allowed.
- Dividend and covenant constraints respected.
- Scenario deltas explainable by named drivers.

## 7) 90-day delivery plan

- **Weeks 1-3**: Net revenue bridge + BOM COGS + basic QA checks.
- **Weeks 4-6**: Payroll/logistics + capacity schedule + dashboard exposure.
- **Weeks 7-9**: Inventory and AR/AP aging + revolver/covenants.
- **Weeks 10-12**: Tax schedule + scenario driver layer + valuation bridge and sensitivities.

This sequence gives finance teams fast wins on forecast accuracy while building toward an investor-grade planning stack.
