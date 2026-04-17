from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class OpexDriverType(str, Enum):
    FIXED_EQUAL = "fixed_equal"
    UNITS = "units"
    LITERS = "liters"
    REVENUE = "revenue"
    ACTIVE_SKU = "active_sku"
    COMPLEXITY = "complexity"
    CHANNEL_REVENUE = "channel_revenue"
    CHANNEL_UNITS = "channel_units"
    STEP_CAPACITY = "step_capacity"
    EXPLICIT_WEIGHT = "explicit_weight"


class OpexCostClassification(str, Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    STEP_FIXED = "step_fixed"


@dataclass
class StepCapacityBand:
    up_to: float
    weight: float


@dataclass
class StepFixedBand:
    up_to_total_liters: float
    annual_amount: float


@dataclass
class OpexAllocationRule:
    driver: OpexDriverType
    weight: float = 1.0
    channel: Optional[str] = None
    step_bands: List[StepCapacityBand] = field(default_factory=list)


@dataclass
class OpexCostPool:
    name: str
    category: str
    annual_amount_by_year: Dict[str, float]
    monthly_amount_by_year: Dict[str, float] = field(default_factory=dict)
    driver_type: OpexDriverType = OpexDriverType.FIXED_EQUAL
    classification: OpexCostClassification = OpexCostClassification.FIXED
    product_family_scope: Optional[List[str]] = None
    channel_scope: Optional[List[str]] = None
    explicit_sku_scope: Optional[List[int]] = None
    allocation_basis_weights: Dict[str, float] = field(default_factory=dict)
    rules: List[OpexAllocationRule] = field(default_factory=list)
    step_fixed_bands: List[StepFixedBand] = field(default_factory=list)
    notes: str = ""
    trace_metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class SKUCostContext:
    sku_id: int
    sku_name: str
    product_family: str
    package_type: str
    package_size: str
    active: bool
    units_sold_by_year: Dict[str, float]
    liters_sold_by_year: Dict[str, float]
    revenue_by_year: Dict[str, float]
    revenue_by_channel_by_year: Dict[str, Dict[str, float]]
    units_by_channel_by_year: Dict[str, Dict[str, float]]
    complexity_score: float = 1.0
    batch_count_by_year: Dict[str, float] = field(default_factory=dict)
    order_count_by_year: Dict[str, float] = field(default_factory=dict)
    shipment_count_by_year: Dict[str, float] = field(default_factory=dict)
    explicit_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class SKUOpexAllocation:
    year: str
    sku_id: int
    sku_name: str
    total_allocated_opex: float
    opex_per_unit: float
    opex_per_liter: float
    opex_per_case: float
    by_pool: Dict[str, float] = field(default_factory=dict)


@dataclass
class OpexAllocationSummary:
    year: str
    total_pool_opex: float
    total_allocated_opex: float
    reconciliation_gap: float
    by_pool_totals: Dict[str, float] = field(default_factory=dict)
    by_driver_type_totals: Dict[str, float] = field(default_factory=dict)


@dataclass
class OpexAllocationReport:
    allocations: List[SKUOpexAllocation]
    summaries: List[OpexAllocationSummary]
