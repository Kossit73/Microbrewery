# Microbrewery model enhancement checklist

The current financial model already covers pricing, volumes, direct costs, OPEX, CAPEX, depreciation, working capital, debt, dividends, and valuation. To make the model more detailed and closer to an investor-ready planning tool, consider incrementally adding the following elements.

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
