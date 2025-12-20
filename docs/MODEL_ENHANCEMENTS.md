# Microbrewery model enhancement checklist

The current financial model already covers pricing, volumes, direct costs, OPEX, CAPEX, depreciation, working capital, debt, dividends, and valuation. To make the model more detailed and closer to an investor-ready planning tool, consider incrementally adding the following elements.

## Critical missing schedules and assumptions
These are the most material gaps called out by stakeholders. Each item should become its own schedule with clear inputs, calculations, and outputs that tie into statements and dashboards.

- **Seasonality and trade-spend in revenue**
  - Inputs: monthly/weekly seasonal factors, promotional calendar, trade-spend/discount rate by channel, return/spoilage rates.
  - Calc/output: gross vs. net revenue bridge, uplift from events, and net billable units after returns.

- **BOM-level COGS**
  - Inputs: ingredient BOM per SKU (qty × unit cost), packaging BOM, yield/loss factors, supplier-specific inflation/FX and freight.
  - Calc/output: unit cost build per SKU, variance analysis vs. standard, and sensitivity to commodity shocks.

- **Payroll and logistics OPEX**
  - Inputs: headcount plan by function, salary bands, benefits, payroll taxes, bonus pools; logistics/3PL rates, warehouse and last-mile costs.
  - Calc/output: fully-loaded payroll rollforward, logistics cost per hl/unit/km, and CAC/LTV-linked marketing spend.

- **Capacity and overhaul capex**
  - Inputs: brew-house and packaging line capacity (batches per day, hl per batch), utilization curves, planned downtime, overhaul/maintenance capex with separate lives.
  - Calc/output: capacity headroom, ramp curves for new lines, and depreciation for growth vs. maintenance capex.

- **Granular working-capital aging**
  - Inputs: AR aging buckets with bad-debt rates by channel, AP terms by supplier category with early-pay discounts, inventory split (RM/WIP/FG) with spoilage/write-offs.
  - Calc/output: aging tables, effective DSO/DIO/DPO, write-off expenses, and cash conversion cycle diagnostics.

- **Covenants and revolver logic**
  - Inputs: DSCR/interest coverage/leverage thresholds, reporting frequency, cure periods; revolver limit, pricing grid, minimum cash sweep rules.
  - Calc/output: covenant headroom tracking, auto-draw/repay sweep to target cash, and warning flags on breaches.

- **Detailed tax (excise/VAT)**
  - Inputs: excise duty by style/ABV/format, VAT/GST by channel/region, carryforward rules, minimum/franchise taxes.
  - Calc/output: tax bridges (gross → excise/VAT → net), deferred tax rollforward, and sensitivity to rate changes.

- **Richer risk/valuation features**
  - Inputs: scenario library (commodity, FX, demand, regulation), real options (expand/abandon/defer), ML/market-driven exit multiples.
  - Calc/output: downside/base/upside valuation stack, option-adjusted values, and VaR/CVaR style summaries.

- **KPI dashboards**
  - Inputs: metric definitions for unit economics, production, quality, liquidity, and commercial efficiency.
  - Calc/output: tabular and charted KPIs (contribution per SKU/channel, utilization, defect/return rates, burn/runway, covenant headroom) with scenario toggles.

- **Governance (versioned assumptions and audit trails)**
  - Inputs: assumption set IDs, author/time stamps, change reasons, approval workflow markers.
  - Calc/output: versioned runs, change logs for pricing/capex/financing updates, and reproducible scenario archives.

## Revenue, volumes, and pricing
- Channel mix scenarios (e.g., on-premise vs. retail vs. e-commerce) with distinct growth curves and elasticity to price changes.
- Seasonality curves and event-driven uplifts (holidays, festivals, promotions) layered on top of the base growth series.
- Trade spend and discounts by channel (volume rebates, slotting fees, promotional spend) that reduce net revenue.
- Returns, breakage, and spoilage assumptions that reduce billable volume.
- Multi-pack and container format mix (kegs, cans, bottles) with format-specific margins and packaging costs.

## Cost of goods sold
- Detailed bill of materials per SKU (malt, hops, yeast, water, adjuncts) with supplier-specific inflation, FX, and freight assumptions.
- Packaging BOM (cans, bottles, labels, cartons, kegs) with yield/loss factors and deposit schemes for kegs.
- Utilities by driver (steam, electricity, CO2, water) tied to production volumes and efficiency improvements.
- Quality control and lab costs per batch.
- Contract brewing vs. owned production toggle with different fixed/variable cost structures.

## Operating expenses
- Payroll model (headcount by function, salary bands, benefits, payroll taxes, bonus pools) with hiring plans over time.
- Selling & marketing split (brand marketing vs. trade marketing vs. digital) with CAC/LTV style KPIs.
- Logistics and distribution costs (3PL fees, warehousing, last-mile delivery) driven by units and distance.
- Insurance, licensing, compliance, and testing fees.
- Maintenance reserve and planned downtime assumptions that influence capacity and repairs.

## Capacity, capex, and depreciation
- Brew capacity (hl per batch, batches per day/week) with utilization limits and efficiency curves.
- Expansion phases with ramp timing (install, commission, ramp-up) and partial utilization factors.
- Overhaul/major maintenance capex separate from growth capex, with distinct depreciation lives.
- Lease vs. own decision logic (rent vs. mortgage/lease liability) for facilities and equipment.

## Working capital
- Inventory stratified into raw materials, WIP, and finished goods with different DIO targets and spoilage/write-offs.
- Receivables aging buckets and bad-debt assumptions by channel.
- Payables terms by supplier category plus early-pay discount logic.

## Financing and cash
- Covenant tracking (DSCR, interest coverage, leverage ratio) with covenant headroom reporting.
- Revolving credit facility that sweeps to maintain a minimum cash balance before dividends.
- Equity waterfall with investor preference stacks and distribution rules.

## Tax and compliance
- Excise duties, VAT/GST, and state/local alcohol taxes with channel- or product-specific rates.
- Loss carryforward logic and minimum tax or franchise tax where applicable.

## Valuation and risk
- Scenario analysis for commodity shocks (grain, aluminum), FX swings, demand shocks, and regulatory changes.
- Real options for expansion/deferral/abandonment tied to capacity and market signals.
- ML-driven or market-linked exit multiples (e.g., industry beta spreads, peer comparables).

## Reporting and KPIs
- Unit economics dashboard (contribution margin per SKU/channel, CAC/LTV, payback period).
- Production KPIs (brew house yield, brews per week, utilization) and quality KPIs (defect rate, returns).
- Cash and liquidity dashboard with burn, runway, and minimum cash covenant tracking.
- Sensitivity tables (price ±x%, volume ±y%, cost ±z%) and tornado charts for key drivers.

## Data and governance
- Input validation, versioned assumption sets, and scenario tagging.
- Audit trails for key changes (pricing, capex, financing) and reproducible model runs.

Use this checklist to prioritize the next set of enhancements based on materiality and data availability.
