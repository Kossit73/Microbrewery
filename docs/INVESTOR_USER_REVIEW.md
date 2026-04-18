# Investor & Customer Attractiveness Review

## Scope reviewed
- Product description and positioning from `README.md`
- Existing enhancement backlog from `docs/MODEL_ENHANCEMENTS.md`
- Architecture and valuation stack from `docs/ARCHITECTURE.md`
- Model assumptions and schedule logic from `finmodel/core.py`, `finmodel/microbrewery_dataclasses.py`, and `finmodel/default_model.py`

## Executive assessment
The model has a strong baseline for 10-year planning (revenue, direct costs, OPEX, debt, cash flow, and valuation), but there are **four investor-facing credibility gaps** and **three user-facing adoption gaps** that will likely limit financing and daily usage if not addressed.

---

## What already helps attract financiers and users
1. **Integrated statement flow exists** (P&L + cash flow + valuation), which is a good foundation for due diligence.
2. **SKU-level assumptions and channel pricing** support commercial storytelling beyond top-down revenue guesses.
3. **Scenario and Monte Carlo modules exist in the package architecture**, which can support stronger risk narratives when made more tightly connected to brewery operations.
4. **Streamlit UI availability** lowers friction for non-technical operators and potential investors.

---

## Priority improvements to attract financiers (capital-readiness)

### 1) Add covenant and liquidity controls (highest priority)
**Why financiers care:** lenders and equity investors need proof that downside periods are survivable.

**Current limitation:** debt schedule computes balances/interest/repayment, but no covenant-headroom logic, no revolver auto-draw/repay, and no explicit minimum-cash breach engine.

**Improve by adding:**
- DSCR, leverage, and interest-coverage covenant schedules with warning flags.
- Revolver facility logic tied to minimum cash target and pricing grid.
- Covenant breach timeline and cure assumptions (scenario visible in UI).

### 2) Build net-revenue bridge and trade-spend schedule
**Why financiers care:** they underwrite net sales quality, not gross list prices.

**Current limitation:** annual revenue currently uses weighted base channel price with inflation, but does not explicitly model discounts, promotions, returns/spoilage, and price realization bridge.

**Improve by adding:**
- Gross-to-net waterfall by channel and SKU.
- Promotional calendar + trade-spend assumptions.
- Return/spoilage assumptions tied to channel and format.

### 3) Add BOM-level COGS and procurement risk sensitivity
**Why financiers care:** they stress-test commodity, packaging, and freight shocks.

**Current limitation:** direct costs are a single per-SKU input inflated over time.

**Improve by adding:**
- Ingredient + packaging BOM per SKU.
- Supplier-level inflation/FX/freight levers.
- COGS variance decomposition (mix/price/efficiency).

### 4) Add tax realism for alcohol businesses
**Why financiers care:** excise and indirect taxes materially alter cash flow and valuation.

**Current limitation:** model includes aggregated income-tax assumptions only.

**Improve by adding:**
- Excise by product style/ABV/format and geography.
- VAT/GST or sales-tax pass-through logic by channel.
- Deferred tax / carryforward bridge.

### 5) Strengthen valuation governance
**Why financiers care:** auditability and repeatability reduce perceived model risk.

**Current limitation:** valuation is primarily EV/EBITDA-based in brewery core; versioning/audit trail is not first-class.

**Improve by adding:**
- Versioned assumption snapshots with author/date/reason metadata.
- Multiple valuation views (DCF + market multiples + downside case summary).
- Investment committee output pack (base/downside/upside + sensitivities + key risks).

---

## Priority improvements to attract users (operator and management adoption)

### 1) Introduce operational KPI dashboard with action thresholds
**Why users care:** operators adopt tools that explain what to do next, not just financial outputs.

**Improve by adding:**
- SKU/channel contribution margins.
- Capacity utilization and downtime metrics.
- Cash runway and covenant headroom status.
- “Action cards” when thresholds are breached (e.g., adjust channel mix, defer CAPEX, reduce promo intensity).

### 2) Improve planning granularity (monthly drivers and seasonality)
**Why users care:** breweries run on seasonality, events, and promotions.

**Current limitation:** most financial drivers are yearly aggregates.

**Improve by adding:**
- Monthly revenue seasonality profile.
- Event calendar uplifts and post-event decay logic.
- Monthly staffing and logistics driver model.

### 3) Build assumption quality controls in the UI
**Why users care:** trust and speed improve when errors are caught at entry.

**Improve by adding:**
- Input validation ranges and warnings (e.g., impossible utilization, negative margins, over-optimistic growth).
- Baseline benchmarks for key metrics.
- One-click scenario templates (conservative / base / aggressive).

---

## Quick wins (next 30 days)
1. Add gross-to-net revenue bridge schedule and expose it in Streamlit.
2. Add covenant headroom (DSCR + interest coverage + leverage) with red/amber/green status.
3. Add three built-in downside scenarios: commodity shock, demand dip, and delayed expansion.
4. Add top-10 sensitivity tornado chart for investor deck export.

## Medium-term (30–90 days)
1. BOM-level COGS with supplier risk factors.
2. Monthly seasonality and promo calendar engine.
3. Revolver and cash-sweep mechanics.
4. Excise + indirect tax layers.

## Long-term (90+ days)
1. Assumption versioning, audit trail, and reproducible run archive.
2. Scenario governance workflow (draft → review → approved).
3. Standardized investment memo outputs generated directly from model runs.

---

## Success metrics to track
- **Financier conversion:** % of funding conversations progressing to term-sheet stage.
- **Model confidence:** # of investor data requests answered without offline spreadsheet edits.
- **User adoption:** weekly active users in Streamlit and scenario runs per month.
- **Forecast quality:** MAPE on net revenue and gross margin vs actuals.
- **Decision velocity:** time from scenario request to approved decision packet.
