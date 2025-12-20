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
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
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
- Always confirm your virtual environment is active before installing (`source .venv/bin/activate`).

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
