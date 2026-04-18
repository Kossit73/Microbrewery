from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class QuestionType(str, Enum):
    VALUATION = "valuation"
    PROFITABILITY = "profitability"
    LIQUIDITY = "liquidity"
    LEVERAGE = "leverage"
    GROWTH = "growth"
    PRICING = "pricing"
    EFFICIENCY = "efficiency"
    RISK = "risk"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"


@dataclass
class ExternalBenchmark:
    metric: str
    low: float
    high: float
    unit: str
    interpretation: str
    source_name: str
    source_url: str


@dataclass
class DecisionTurn:
    question: str
    answer: str
    question_type: QuestionType
    topics: List[str] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class DecisionSessionMemory:
    turns: List[DecisionTurn] = field(default_factory=list)

    def remember(self, turn: DecisionTurn) -> None:
        self.turns.append(turn)

    def last_turn(self) -> DecisionTurn | None:
        return self.turns[-1] if self.turns else None


_KEYWORDS: Dict[QuestionType, List[str]] = {
    QuestionType.VALUATION: ["valuation", "ev/ebitda", "multiple", "irr", "moic", "dcf"],
    QuestionType.PROFITABILITY: ["profit", "ebitda", "margin", "gross", "net income"],
    QuestionType.LIQUIDITY: ["cash", "runway", "liquidity", "working capital", "current ratio"],
    QuestionType.LEVERAGE: ["debt", "leverage", "dscr", "coverage", "covenant"],
    QuestionType.GROWTH: ["growth", "cagr", "expand", "volume", "revenue growth"],
    QuestionType.PRICING: ["price", "pricing", "markup", "premium", "discount"],
    QuestionType.EFFICIENCY: ["efficiency", "cost", "opex", "utilization", "productivity"],
    QuestionType.RISK: ["risk", "stress", "downside", "scenario", "sensitivity"],
}

_FOLLOW_UP_HINTS = {"follow up", "follow-up", "that", "those", "same", "previous", "earlier", "also", "what about", "and if"}


def classify_question(question: str, memory: DecisionSessionMemory | None = None) -> QuestionType:
    q = question.lower().strip()
    if memory and memory.turns and any(hint in q for hint in _FOLLOW_UP_HINTS):
        prev = memory.last_turn()
        return prev.question_type if prev else QuestionType.FOLLOW_UP
    for qtype, keywords in _KEYWORDS.items():
        if any(k in q for k in keywords):
            return qtype
    return QuestionType.GENERAL


def detect_topics(question: str) -> List[str]:
    q = question.lower()
    topics: List[str] = []
    topic_keywords = {
        "revenue": ["revenue", "sales", "volume"],
        "profitability": ["ebitda", "gross", "net income", "margin"],
        "liquidity": ["cash", "liquidity", "runway", "working capital"],
        "leverage": ["debt", "leverage", "coverage", "dscr"],
        "valuation": ["valuation", "dcf", "irr", "moic", "multiple"],
        "pricing": ["price", "pricing", "markup"],
        "opex": ["opex", "cost", "allocation", "driver"],
    }
    for topic, keys in topic_keywords.items():
        if any(k in q for k in keys):
            topics.append(topic)
    return topics or ["general"]


def _safe(v: Any) -> float:
    try:
        if v is None:
            return 0.0
        return float(v)
    except Exception:
        return 0.0


def _internal_metrics(snapshot: Dict[str, Any]) -> Dict[str, float]:
    prod = snapshot.get("production_and_revenues", {})
    fin = snapshot.get("financial_statements", {})
    val = snapshot.get("advanced_analytics", {}).get("valuation_summary", {})
    annual = snapshot.get("latest_annual", {})

    revenue = _safe(prod.get("latest_total_revenue"))
    ebitda = _safe(prod.get("latest_ebitda"))
    net_income = _safe(fin.get("latest_net_income"))
    cash = _safe(fin.get("latest_cash"))
    debt = _safe(fin.get("latest_debt_balance"))
    enterprise_value = _safe(val.get("enterprise_value_dcf"))

    return {
        "revenue": revenue,
        "ebitda": ebitda,
        "net_income": net_income,
        "cash": cash,
        "debt": debt,
        "ebitda_margin": ebitda / revenue if abs(revenue) > 1e-9 else 0.0,
        "net_margin": net_income / revenue if abs(revenue) > 1e-9 else 0.0,
        "debt_to_ebitda": debt / ebitda if abs(ebitda) > 1e-9 else 0.0,
        "cash_to_debt": cash / debt if abs(debt) > 1e-9 else 0.0,
        "ev_to_ebitda": enterprise_value / ebitda if abs(ebitda) > 1e-9 else 0.0,
        "revenue_growth": _safe(annual.get("revenue_growth")),
        "irr": _safe(val.get("equity_irr_annual")),
        "moic": _safe(val.get("equity_moic")),
    }


def benchmark_catalog(question_type: QuestionType) -> List[ExternalBenchmark]:
    if question_type == QuestionType.VALUATION:
        return [
            ExternalBenchmark("EV/EBITDA", 8.0, 14.0, "x", "Small-cap food & beverage valuation band", "NYU Damodaran Data", "https://pages.stern.nyu.edu/~adamodar/"),
            ExternalBenchmark("Target Equity IRR", 0.20, 0.35, "%", "Lower-middle-market sponsor target returns", "Investopedia LBO overview", "https://www.investopedia.com/terms/l/leveragedbuyout.asp"),
        ]
    if question_type == QuestionType.PROFITABILITY:
        return [
            ExternalBenchmark("EBITDA margin", 0.10, 0.25, "%", "Typical healthy beverage margin range", "CSI Market Beverage Industry", "https://csimarket.com/Industry/industry_Profitability_Ratios.php?ind=503"),
            ExternalBenchmark("Net margin", 0.03, 0.12, "%", "Indicative packaged beverage net margin range", "CSI Market Beverage Industry", "https://csimarket.com/Industry/industry_Profitability_Ratios.php?ind=503"),
        ]
    if question_type == QuestionType.LIQUIDITY:
        return [
            ExternalBenchmark("Current ratio", 1.2, 2.0, "x", "Typical operating comfort range", "CFI Current Ratio", "https://corporatefinanceinstitute.com/resources/accounting/current-ratio-formula/"),
            ExternalBenchmark("Cash to debt", 0.25, 1.00, "x", "Liquidity cushion range", "S&P Global (credit metrics overview)", "https://www.spglobal.com/ratings/"),
        ]
    if question_type == QuestionType.LEVERAGE:
        return [
            ExternalBenchmark("Debt/EBITDA", 2.0, 4.5, "x", "Common leverage covenant zone", "CFI Debt/EBITDA", "https://corporatefinanceinstitute.com/resources/knowledge/finance/debt-ebitda-ratio/"),
            ExternalBenchmark("DSCR", 1.20, 2.00, "x", "Common minimum lender coverage", "SBA lending guidance", "https://www.sba.gov/funding-programs/loans"),
        ]
    if question_type == QuestionType.GROWTH:
        return [
            ExternalBenchmark("Revenue growth", 0.04, 0.12, "%", "Typical mature FMCG growth reference", "World Bank + OECD industry context", "https://data.worldbank.org/"),
        ]
    return []


def _compare(metric_name: str, value: float, bench: ExternalBenchmark) -> str:
    if value < bench.low:
        return f"below benchmark ({value:.2f}{bench.unit} vs {bench.low:.2f}-{bench.high:.2f}{bench.unit})"
    if value > bench.high:
        return f"above benchmark ({value:.2f}{bench.unit} vs {bench.low:.2f}-{bench.high:.2f}{bench.unit})"
    return f"within benchmark ({value:.2f}{bench.unit} vs {bench.low:.2f}-{bench.high:.2f}{bench.unit})"


def build_structured_answer(question: str, snapshot: Dict[str, Any], memory: DecisionSessionMemory, web_sources: List[dict] | None = None) -> DecisionTurn:
    qtype = classify_question(question, memory)
    topics = detect_topics(question)
    metrics = _internal_metrics(snapshot)
    benches = benchmark_catalog(qtype)
    web_sources = web_sources or []

    prev_line = ""
    if memory.last_turn() and classify_question(question, memory) == memory.last_turn().question_type:
        prev_line = "Follow-up context retained from prior question; assumptions unchanged unless edited. "

    direct_answer = "The model appears broadly reasonable, with benchmark-adjusted caveats highlighted below."
    if qtype == QuestionType.VALUATION and metrics["ev_to_ebitda"] > 0:
        if metrics["ev_to_ebitda"] > 14:
            direct_answer = "The valuation looks aggressive versus market norms."
        elif metrics["ev_to_ebitda"] < 8:
            direct_answer = "The valuation looks conservative versus market norms."
        else:
            direct_answer = "The valuation appears within a plausible market range."

    internal_line = (
        f"Model outputs: revenue {metrics['revenue']:,.2f}, EBITDA {metrics['ebitda']:,.2f} "
        f"(margin {metrics['ebitda_margin']:.2%}), net income {metrics['net_income']:,.2f} "
        f"(margin {metrics['net_margin']:.2%}), cash {metrics['cash']:,.2f}, debt {metrics['debt']:,.2f}, "
        f"debt/EBITDA {metrics['debt_to_ebitda']:.2f}x, cash/debt {metrics['cash_to_debt']:.2f}x, "
        f"EV/EBITDA {metrics['ev_to_ebitda']:.2f}x, IRR {metrics['irr']:.2%}, MOIC {metrics['moic']:.2f}x."
    )

    metric_map = {
        "EV/EBITDA": metrics["ev_to_ebitda"],
        "Target Equity IRR": metrics["irr"],
        "EBITDA margin": metrics["ebitda_margin"],
        "Net margin": metrics["net_margin"],
        "Current ratio": _safe(snapshot.get("ratios", {}).get("current_ratio", 0.0)),
        "Cash to debt": metrics["cash_to_debt"],
        "Debt/EBITDA": metrics["debt_to_ebitda"],
        "DSCR": _safe(snapshot.get("ratios", {}).get("dscr", 0.0)),
        "Revenue growth": metrics["revenue_growth"],
    }

    benchmark_lines = []
    comparison_lines = []
    for b in benches:
        benchmark_lines.append(f"{b.metric}: {b.low:.2f}-{b.high:.2f}{b.unit} ({b.interpretation}).")
        comparison_lines.append(f"{b.metric} is {_compare(b.metric, metric_map.get(b.metric, 0.0), b)}.")

    if not benchmark_lines:
        benchmark_lines.append("No strong benchmark range was mapped to this question type; use supplementary web references.")

    recommendation = "Prioritize sensitivity testing on the top two assumptions driving this gap before making capital decisions."
    if qtype in {QuestionType.LIQUIDITY, QuestionType.LEVERAGE}:
        recommendation = "Stress-test downside cash conversion and covenant headroom; set explicit trigger thresholds for debt draw, dividends, and capex pacing."
    elif qtype == QuestionType.PROFITABILITY:
        recommendation = "Validate gross-to-EBITDA bridge by channel and SKU, then test price/mix and direct-cost inflation to confirm margin durability."
    elif qtype == QuestionType.VALUATION:
        recommendation = "Triangulate valuation with both EV/EBITDA and return hurdles; re-run cases with tighter exit multiple and slower growth assumptions."

    sources = [f"Internal model snapshot (latest run)."]
    sources.extend([f"{b.source_name}: {b.source_url}" for b in benches])
    sources.extend([f"Live web search: {w.get('title', 'source')} - {w.get('url', '')}" for w in web_sources[:5]])

    answer = (
        f"1) Direct answer\n{direct_answer}\n\n"
        f"2) Internal model analysis\n{prev_line}{internal_line}\n\n"
        f"3) External benchmark analysis\n" + "\n".join(f"- {x}" for x in benchmark_lines) + "\n\n"
        f"4) Comparison and interpretation\n" + "\n".join(f"- {x}" for x in comparison_lines) + "\n\n"
        f"5) Decision-quality recommendation\n{recommendation}\n\n"
        f"6) Sources\n" + "\n".join(f"- {s}" for s in sources)
    )

    conclusion = comparison_lines[0] if comparison_lines else direct_answer
    turn = DecisionTurn(question=question, answer=answer, question_type=qtype, topics=topics, conclusion=conclusion)
    memory.remember(turn)
    return turn
