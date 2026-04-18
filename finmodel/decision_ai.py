from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List


class QuestionType(str, Enum):
    ASSUMPTIONS = "assumptions"
    CALCULATIONS = "calculations"
    OUTPUTS = "outputs"
    SCHEDULES = "schedules"
    LOGIC = "logic"
    DEPENDENCIES = "dependencies"
    SCENARIOS = "scenarios"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"


@dataclass
class DecisionTurn:
    question: str
    answer: str
    question_type: QuestionType
    topics: List[str] = field(default_factory=list)


@dataclass
class DecisionSessionMemory:
    turns: List[DecisionTurn] = field(default_factory=list)

    def remember(self, turn: DecisionTurn) -> None:
        self.turns.append(turn)

    def last_turn(self) -> DecisionTurn | None:
        return self.turns[-1] if self.turns else None


_KEYWORDS: Dict[QuestionType, List[str]] = {
    QuestionType.ASSUMPTIONS: ["assumption", "assume", "wacc", "tax", "inflation", "input"],
    QuestionType.CALCULATIONS: ["calculate", "formula", "how is", "computed", "derive", "math"],
    QuestionType.OUTPUTS: ["output", "result", "kpi", "metric", "valuation", "report"],
    QuestionType.SCHEDULES: ["schedule", "timeline", "monthly", "quarterly", "yearly", "forecast"],
    QuestionType.LOGIC: ["logic", "rule", "why", "decision", "allocation", "driver", "flow"],
    QuestionType.DEPENDENCIES: ["dependency", "dependencies", "depends", "linked", "relationship", "impact"],
    QuestionType.SCENARIOS: ["scenario", "stress", "downside", "upside", "sensitivity", "what if"],
}

_FOLLOW_UP_HINTS = {
    "follow up",
    "follow-up",
    "that",
    "those",
    "it",
    "same",
    "previous",
    "earlier",
    "also",
    "what about",
    "and if",
}


def classify_question(question: str, memory: DecisionSessionMemory | None = None) -> QuestionType:
    q = question.lower().strip()
    if memory and memory.turns and any(hint in q for hint in _FOLLOW_UP_HINTS):
        return QuestionType.FOLLOW_UP
    for qtype, keywords in _KEYWORDS.items():
        if any(k in q for k in keywords):
            return qtype
    return QuestionType.GENERAL


def detect_topics(question: str) -> List[str]:
    q = question.lower()
    topics: List[str] = []
    topic_keywords = {
        "revenue": ["revenue", "sales", "price", "volume"],
        "profitability": ["ebitda", "margin", "net income", "profit"],
        "cash_and_debt": ["cash", "debt", "dscr", "liquidity"],
        "opex_allocation": ["opex", "allocation", "driver", "pool"],
        "valuation": ["valuation", "dcf", "irr", "moic", "terminal"],
        "schedule": ["monthly", "quarterly", "yearly", "schedule"],
    }
    for topic, keys in topic_keywords.items():
        if any(k in q for k in keys):
            topics.append(topic)
    return topics or ["general"]


def _latest_metrics(snapshot: Dict[str, Any]) -> Dict[str, float]:
    prod = snapshot.get("production_and_revenues", {})
    fin = snapshot.get("financial_statements", {})
    val = snapshot.get("advanced_analytics", {}).get("valuation_summary", {})
    return {
        "revenue": float(prod.get("latest_total_revenue") or 0.0),
        "ebitda": float(prod.get("latest_ebitda") or 0.0),
        "net_income": float(fin.get("latest_net_income") or 0.0),
        "cash": float(fin.get("latest_cash") or 0.0),
        "debt": float(fin.get("latest_debt_balance") or 0.0),
        "irr": float(val.get("equity_irr_annual") or 0.0),
    }


def build_contextual_answer(question: str, snapshot: Dict[str, Any], memory: DecisionSessionMemory) -> DecisionTurn:
    qtype = classify_question(question, memory)
    topics = detect_topics(question)
    metrics = _latest_metrics(snapshot)

    previous_ref = ""
    if qtype == QuestionType.FOLLOW_UP and memory.last_turn():
        prev = memory.last_turn()
        previous_ref = (
            f"This follows your previous question on {', '.join(prev.topics)}. "
            "I am keeping the same model configuration unless you request a change. "
        )

    base = (
        f"{previous_ref}Given the current model outputs: revenue {metrics['revenue']:,.2f}, "
        f"EBITDA {metrics['ebitda']:,.2f}, net income {metrics['net_income']:,.2f}, "
        f"cash {metrics['cash']:,.2f}, and debt {metrics['debt']:,.2f}. "
    )

    guidance_map = {
        QuestionType.ASSUMPTIONS: "I will anchor the answer to core assumptions (WACC, tax, inflation, policy thresholds) and identify which assumptions drive the result most.",
        QuestionType.CALCULATIONS: "I will walk through the calculation chain and formulas linking assumptions to outputs, including intermediate schedules.",
        QuestionType.OUTPUTS: "I will interpret reported outputs and relate them to operating, financing, and valuation implications.",
        QuestionType.SCHEDULES: "I will explain the monthly-to-annual schedule flow and where each output is sourced.",
        QuestionType.LOGIC: "I will describe decision rules and model logic, including driver-based allocation behavior and control points.",
        QuestionType.DEPENDENCIES: "I will map dependencies across drivers, statements, and valuation so second-order impacts are explicit.",
        QuestionType.SCENARIOS: "I will frame this as scenario analysis and compare base vs changed assumptions in a traceable way.",
        QuestionType.FOLLOW_UP: "I will build directly on earlier answers and preserve continuity with prior assumptions and edits.",
        QuestionType.GENERAL: "I will provide a structured model-aware answer and flag any assumptions that should be confirmed.",
    }

    answer = f"{base}{guidance_map[qtype]}\n\nQuestion focus: {', '.join(topics)}."
    turn = DecisionTurn(question=question, answer=answer, question_type=qtype, topics=topics)
    memory.remember(turn)
    return turn
