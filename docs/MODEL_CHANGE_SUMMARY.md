# Model Change Summary

## Overview
This repository now includes a full driver-based OPEX allocation layer that replaces flat, single-rate OPEX-per-SKU assumptions with auditable cost-pool logic.

### Implemented capabilities
- Full OPEX schema layer with explicit finance models:
  - `OpexAllocationRule`
  - `OpexCostPool`
  - `SKUCostContext`
  - `SKUOpexAllocation`
  - `OpexAllocationSummary`
  - `OpexAllocationReport`
- Enums for requested driver types and cost classifications.

## Allocation engine behavior
The allocation engine now:
1. Normalizes blended rule weights.
2. Supports family/SKU scope filters.
3. Supports channel-aware drivers.
4. Supports step-capacity and step-fixed pool behavior.
5. Computes `opex_per_unit` and `opex_per_liter`.
6. Reconciles pool totals to allocated totals by year.

## Default OPEX pool design
Default pools now include:
- Indirect Labor
- Utilities
- Supplies
- Marketing & Advertising
- Events & Promotion
- Insurance
- Permits & License
- Local Fees
- Transport
- Administrative Expense
- Quality Control
- Certificates
- Professional Services
- Other Expense
- Contingencies

These include driver mappings and blended/step logic where applicable.

## Public API additions
`MicrobreweryFinancialModel` now exposes:
- `opex_contexts_by_sku_and_year()`
- `allocate_opex()`
- `opex_metrics_by_sku_and_year()`
- `reconcile_opex_allocation()`

Default pool generation is wired into model flow when custom pools are not provided.

## Packaging and repo readiness
- Allocation schemas/builders are exposed through package exports.
- `pyproject.toml` supports editable install workflow.
- `AGENTS.md` provides local guidance for structure, style, testing, and reconciliation expectations.

## Tests and validation coverage
Coverage includes:
- end-to-end allocation execution,
- reconciliation checks,
- active/inactive SKU behavior,
- scoped pool behavior,
- blended weight normalization,
- step-cost behavior.

## Assumptions / limitations
1. Channel-level SKU revenue/units are currently derived from default channel-mix weights as a fallback assumption.
2. Step-fixed pool sizing uses configured bands and annual pool assumptions and is not yet connected to an external capacity-planning system.
