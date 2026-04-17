# Agent instructions for Microbrewery repo

## Scope
These instructions apply to the entire repository.

## Package structure expectations
- Keep reusable domain logic in the `finmodel/` package.
- Prefer adding new finance engines in dedicated modules (for example `allocation.py`, `opex_schemas.py`, `opex_defaults.py`) instead of expanding monolithic files.
- Public API exports should be wired through `finmodel/__init__.py` and `finmodel/schemas.py`.

## Style and design
- Use typed dataclasses and explicit enums for finance-facing models.
- Keep allocation logic deterministic and traceable from pool -> driver -> sku.
- Avoid hidden side effects in utility helpers.

## Testing expectations
- Run targeted tests for changed modules and at least one broader `pytest` run.
- When changing OPEX allocation logic, include tests for:
  - reconciliation (`total pool opex == allocated opex`),
  - active vs inactive SKU behavior,
  - scope filters (family/channel/explicit SKU),
  - blended weight normalization,
  - step-fixed behavior.

## Financial reconciliation requirement
- Any OPEX allocation implementation must reconcile by year within float tolerance (abs gap <= 1e-6).
- Do not merge changes that silently drop or create OPEX during allocation.
