# Microbrewery Financial Model

This repository contains an all-in-one Python financial model for a microbrewery-style business. The model builds monthly and annual statements, debt schedules, cash flows, and valuation metrics from SKU-level assumptions.

## Features
- SKU x channel volume planning with price inflation and cost-plus pricing
- Direct costs, fixed OPEX, CAPEX with straight-line depreciation
- Working capital (DSO/DIO/DPO plus percentage add-ons)
- Multi-facility debt schedules (linear, annuity, interest-only-then-linear, or specified)
- Dividend policy (cash sweep or share-of-profits)
- Monthly and annual financial statements
- DCF valuation (FCFF with EV/EBITDA terminal multiple) and investor IRR/MOIC

## Setup
1. Create a virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies (online):
   ```bash
   pip install -r requirements.txt
   ```

   If you are in a restricted network where outbound HTTPS is blocked, download the wheels elsewhere using `python download_dependencies.py --dest ./vendor` and then install from that folder:

   ```bash
   pip install --no-index --find-links=./vendor -r requirements.txt
   ```

3. Verify the core dependencies are available:
   ```bash
   python check_env.py
   ```

### Troubleshooting dependency installs (numpy/streamlit/pandas)
- If you see `ModuleNotFoundError` for numpy, pandas, or streamlit, install directly:
  ```bash
  pip install numpy pandas streamlit openpyxl
  ```
- If you are behind a proxy or in a restricted network (e.g., receiving `Tunnel connection failed: 403 Forbidden`), try:
  ```bash
  pip install --proxy=http://<proxy_host>:<proxy_port> -r requirements.txt
  ```
  or download wheel files on a machine with internet access and install them locally:
  ```bash
  pip install --no-index --find-links=/path/to/wheels -r requirements.txt
  ```
- You can automate wheel downloads with the helper script (supports `--proxy`, `--index-url`, and `--extra-index-url`):
  ```bash
  python download_dependencies.py --dest ./vendor
  ```
- Always confirm your virtual environment is active before installing (`source .venv/bin/activate`).

### Quick start: getting pandas (and other deps) working
If you only need pandas (and friends) to run the model or the Streamlit app, use this minimal recipe:
```bash
# 1) Create/activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# 2) Install pandas plus the other core packages
pip install pandas numpy streamlit openpyxl

# 3) Verify pandas is ready
python - <<'PY'
import pandas as pd
print("pandas version:", pd.__version__)
PY

# 4) Run the example (pandas is required here)
python brewery_financial_model_all_in_one.py
# or launch the dashboard
streamlit run streamlit_app.py
```

## Usage
### Command-line example
Run the example model and (optionally) export an Excel workbook:
```bash
python brewery_financial_model_all_in_one.py
```

Replace the sample assumptions in `brewery_financial_model_all_in_one.py` with your own inputs to generate custom projections.

### Streamlit app
Launch the interactive dashboard to explore scenarios and download outputs:
```bash
streamlit run streamlit_app.py
```
Use the horizontal tab bar to adjust key assumptions (WACC, exit multiple, inflation, dividend timing) and to download a fully formatted Excel workbook of the results.

## Valuation Toolkit

This repository now includes the `finmodel` package that implements a modular valuation toolkit (DCF/rNPV, scenarios, forecasts, Monte Carlo, and ML multiples). See `docs/ARCHITECTURE.md` for class-level details.

## Driver-based OPEX allocation (new)

Flat OPEX-per-SKU rates are convenient but usually not investor-grade because they hide the operational drivers of cost (volume, complexity, channel mix, and scale steps). The package now supports driver-based OPEX pools that allocate to SKUs by year and reconcile back to total OPEX.

### Why this is better than flat OPEX-per-SKU
- Captures scale behavior (fixed, variable, step-fixed pools).
- Supports targeted scope (family/channel/SKU-specific pools).
- Produces traceable per-SKU unit costs (`opex_per_unit`, `opex_per_liter`) and pool breakdowns.
- Reconciles allocations to total OPEX by year for auditability.

### Core API
```python
from finmodel import build_default_model

model = build_default_model()
contexts = model.opex_contexts_by_sku_and_year()
allocation_report = model.allocate_opex()
metrics = model.opex_metrics_by_sku_and_year()
recon = model.reconcile_opex_allocation()
pool_view = model.opex_by_pool_view()
driver_view = model.opex_by_driver_type_view()
product_view = model.opex_by_product_view()
```

### Cost pools and driver mappings
Default pools include: Indirect Labor, Utilities, Supplies, Marketing & Advertising, Events & Promotion, Insurance, Permits & License, Local Fees, Transport, Administrative Expense, Quality Control, Certificates, Professional Services, Other Expense, and Contingencies.

You can map pools to drivers such as:
- `LITERS`, `UNITS`, `REVENUE`
- `CHANNEL_REVENUE`, `CHANNEL_UNITS`
- `FIXED_EQUAL`, `ACTIVE_SKU`, `COMPLEXITY`
- `STEP_CAPACITY`, `EXPLICIT_WEIGHT`
- `BATCH_COUNT`, `ORDER_COUNT`, `SHIPMENT_COUNT`

Blended rules are supported (for example 70% liters / 20% units / 10% complexity).

### Customizing pools
1. Build or edit `OpexCostPool` entries (driver, scope, classification, annual amounts).
2. Add optional blended `OpexAllocationRule` weights.
3. Pass custom pools to `model.allocate_opex(pools=...)`.
4. Optionally enable two-stage allocation (`two_stage_family_allocation=True`) to allocate to product family first, then down to SKU using `second_stage_driver`.

### Three output views (recommended)
- **A. OPEX by pool:** `model.opex_by_pool_view()`
- **B. OPEX by driver type:** `model.opex_by_driver_type_view()`
- **C. OPEX by product:** `model.opex_by_product_view()` (includes per-unit, per-liter, per-case, and fully loaded gross margin metrics).

## Making the brewery model more detailed

For a prioritized checklist of granular features to add (e.g., seasonality, SKU-level BOMs, payroll plans, covenants, and sensitivity dashboards), see `docs/MODEL_ENHANCEMENTS.md`. Start with the **Critical missing schedules and assumptions** section to surface the biggest gaps.

For a schedule-by-schedule build sequence (with phased implementation guidance), see `docs/DETAILED_SCHEDULE_ROADMAP.md`.
