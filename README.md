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

## Making the brewery model more detailed

For a prioritized checklist of granular features to add (e.g., seasonality, SKU-level BOMs, payroll plans, covenants, and sensitivity dashboards), see `docs/MODEL_ENHANCEMENTS.md`.
