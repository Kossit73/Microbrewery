from __future__ import annotations

from .core import MicrobreweryFinancialModel
from .schemas import (
    CapexItem,
    DebtFacility,
    EmployeeRole,
    EventTourLine,
    ExpansionEvent,
    GeneralSettings,
    InvestorRound,
    MarketVolumeAssumption,
    OpexLine,
    OtherIncomeLine,
    PackagingSize,
    SKU,
    StartupExpense,
    TaxAssumptions,
    WACCConfig,
    WorkingCapitalAssumptions,
)


def build_default_model() -> MicrobreweryFinancialModel:
    packaging_sizes = {
        "Small Bottle": PackagingSize("Small Bottle", "Milliliter", "Milliliters", "mL", "Milliliter", 330.0, 0.330),
        "Large Bottle": PackagingSize("Large Bottle", "Milliliter", "Milliliters", "mL", "Milliliter", 500.0, 0.500),
        "Can": PackagingSize("Can", "Milliliter", "Milliliters", "mL", "Milliliter", 475.0, 0.475),
        "Keg": PackagingSize("Keg", "Liter", "Liters", "L", "Liter", 20.0, 20.0),
    }

    expansions = [
        ExpansionEvent("Initial Capacity", 0, 0, 50_000),
        ExpansionEvent("1st Expansion", 1, 10, 50_000),
        ExpansionEvent("2nd Expansion", 2, 24, 30_000),
        ExpansionEvent("3rd Expansion", 4, 41, 20_000),
        ExpansionEvent("4th Expansion", 6, 62, 50_000),
    ]

    def sku(sku_id, name, product_type, package, annual_units, direct_cost, prices):
        return SKU(
            sku_id=sku_id,
            name=name,
            product_type=product_type,
            packaging_size=package,
            volume_unit="Liters" if package == "Keg" else "Milliliters",
            liters_per_sku=packaging_sizes[package].liters_per_sku,
            include=True,
            annual_units=annual_units,
            direct_cost_year1_per_sku=direct_cost,
            channel_prices_year1=prices,
        )

    common_prices = lambda w, r, e, o, x, f: {
        "Wholesale": w,
        "Retail": r,
        "E-Commerce": e,
        "On-Premise Sales": o,
        "Export": x,
        "Events & Festivals": f,
    }

    skus = [
        sku(1, "Pale Ale (Small Bottle)", "Ales", "Small Bottle", {"Year 1": 76798, "Year 2": 163873, "Year 3": 180241, "Year 4": 197942, "Year 5": 217569, "Year 6": 239348, "Year 7": 263530, "Year 8": 290398, "Year 9": 320270, "Year 10": 353501}, 3.75, common_prices(6.20, 8.68, 12.40, 10.85, 6.20, 6.20)),
        sku(2, "Pale Ale (Large Bottle)", "Ales", "Large Bottle", {"Year 1": 44085, "Year 2": 96615, "Year 3": 112423, "Year 4": 123465, "Year 5": 135709, "Year 6": 149295, "Year 7": 164381, "Year 8": 181143, "Year 9": 199778, "Year 10": 220509}, 3.95, common_prices(6.60, 9.24, 13.20, 11.55, 6.60, 6.60)),
        sku(3, "Pale Ale (Can)", "Ales", "Can", {"Year 1": 19578, "Year 2": 331875, "Year 3": 446801, "Year 4": 489700, "Year 5": 537192, "Year 6": 589805, "Year 7": 648134, "Year 8": 712844, "Year 9": 784683, "Year 10": 864487}, 3.25, common_prices(5.40, 7.56, 10.80, 9.45, 5.40, 5.40)),
        sku(4, "Pale Ale (Keg)", "Ales", "Keg", {"Year 1": 0, "Year 2": 88533, "Year 3": 132310, "Year 4": 158193, "Year 5": 189138, "Year 6": 226137, "Year 7": 270373, "Year 8": 323263, "Year 9": 386499, "Year 10": 462105}, 6.75, common_prices(10.60, 14.84, 21.20, 18.55, 10.60, 10.60)),
        sku(5, "Pilsner (Small Bottle)", "Bottom-Fermented", "Small Bottle", {"Year 1": 16372, "Year 2": 34936, "Year 3": 38425, "Year 4": 42199, "Year 5": 46383, "Year 6": 51026, "Year 7": 56181, "Year 8": 61909, "Year 9": 68277, "Year 10": 75362}, 4.85, common_prices(7.90, 11.06, 15.80, 13.83, 7.90, 7.90)),
    ]

    market_volume_assumptions = [
        MarketVolumeAssumption("Supermarkets- Local Area A", "Pale Ale (Small Bottle)", "Ales", "Retail", True, "Small Bottle", "Milliliters", 330.0, 3, 8, 5, None, 4550, 6728, 0.10, 0.01),
        MarketVolumeAssumption("Online Sales", "Pale Ale (Small Bottle)", "Ales", "E-Commerce", True, "Small Bottle", "Milliliters", 330.0, 10, 15, 5, None, 4550, 6107, 0.075, 0.005),
    ]

    startup_expenses = [
        StartupExpense("Incorporation Costs", {"Year 0": 30_000, "Year 1": 25_000}),
        StartupExpense("Legal", {"Year 0": 30_000, "Year 1": 25_000}),
    ]

    employee_roles = [
        EmployeeRole("Operators", "Direct Labor", {"Year 1": 3000, "Year 2": 3045, "Year 3": 3091, "Year 4": 3137, "Year 5": 3184, "Year 6": 3232, "Year 7": 3280, "Year 8": 3330, "Year 9": 3379, "Year 10": 3430}, {"Year 1": 5, "Year 2": 5, "Year 3": 5, "Year 4": 5, "Year 5": 5, "Year 6": 6, "Year 7": 6, "Year 8": 6, "Year 9": 6, "Year 10": 6}),
    ]

    opex_lines = [
        OpexLine("Utilities Expense", {"Year 1": 4000, "Year 2": 4600, "Year 3": 4669, "Year 4": 4739, "Year 5": 4810, "Year 6": 4882, "Year 7": 4956, "Year 8": 5030, "Year 9": 5105, "Year 10": 5182}),
    ]

    capex_items = [
        CapexItem("Land", 875000, 0, 0, 0, 0, 0.025, 20),
        CapexItem("Plant and Machinery", 1000000, 750000, 500000, 175000, 150000, 0.03, 10),
    ]

    debt_facilities = [
        DebtFacility("Mortgage", 750000, 0.03, "Year 0", 0, 6, 10),
        DebtFacility("Loan A", 450000, 0.025, "Year 1", 5, 4, 5),
    ]

    event_lines = [
        EventTourLine("Craft Beer Expo", {"Year 1": 50000, "Year 2": 50750, "Year 3": 51510, "Year 4": 52280, "Year 5": 53060, "Year 6": 53856, "Year 7": 54664, "Year 8": 55484, "Year 9": 56316, "Year 10": 57161}),
    ]

    other_income_lines = [
        OtherIncomeLine("Sponsorships", {"Year 1": 10000, "Year 2": 10150, "Year 3": 10300, "Year 4": 10450, "Year 5": 10610, "Year 6": 10769, "Year 7": 10931, "Year 8": 11095, "Year 9": 11261, "Year 10": 11430}),
    ]

    investor_rounds = [
        InvestorRound("Seed", True, 5_500_000, 0, "Year 0", {"Founders": 0.40, "Investor A": 0.40, "Investor B": 0.20}),
        InvestorRound("Series A", True, 1_000_000, 6, "Year 1", {"Investor C": 1.00}),
    ]

    return MicrobreweryFinancialModel(
        general=GeneralSettings(),
        packaging_sizes=packaging_sizes,
        expansions=expansions,
        working_capital=WorkingCapitalAssumptions(),
        taxes=TaxAssumptions(),
        wacc=WACCConfig(),
        skus=skus,
        market_volume_assumptions=market_volume_assumptions,
        startup_expenses=startup_expenses,
        employee_roles=employee_roles,
        opex_lines=opex_lines,
        capex_items=capex_items,
        debt_facilities=debt_facilities,
        event_lines=event_lines,
        other_income_lines=other_income_lines,
        investor_rounds=investor_rounds,
        minimum_cash_balance=1_500_000,
        property_lease_value_yearly=120_000,
        property_value_without_inflation=1_500_000,
        dividend_payout_ratio=0.25,
        dividend_start_year=5,
    )
