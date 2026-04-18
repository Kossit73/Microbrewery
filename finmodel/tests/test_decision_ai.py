from finmodel.decision_ai import (
    DecisionSessionMemory,
    QuestionType,
    build_contextual_answer,
    classify_question,
    detect_topics,
)


def _snapshot() -> dict:
    return {
        "production_and_revenues": {"latest_total_revenue": 1200.0, "latest_ebitda": 300.0},
        "financial_statements": {"latest_net_income": 180.0, "latest_cash": 400.0, "latest_debt_balance": 250.0},
        "advanced_analytics": {"valuation_summary": {"equity_irr_annual": 0.17}},
    }


def test_classify_question_covers_multiple_model_question_types():
    memory = DecisionSessionMemory()
    assert classify_question("Which assumptions drive WACC sensitivity?", memory) == QuestionType.ASSUMPTIONS
    assert classify_question("How is EBITDA calculated?", memory) == QuestionType.CALCULATIONS
    assert classify_question("Show me output KPIs", memory) == QuestionType.OUTPUTS
    assert classify_question("How do monthly schedules roll up yearly?", memory) == QuestionType.SCHEDULES
    assert classify_question("Explain allocation logic", memory) == QuestionType.LOGIC
    assert classify_question("What dependencies link cash and debt?", memory) == QuestionType.DEPENDENCIES
    assert classify_question("What if we run a downside scenario?", memory) == QuestionType.SCENARIOS


def test_build_contextual_answer_preserves_follow_up_continuity():
    memory = DecisionSessionMemory()
    first = build_contextual_answer("Explain EBITDA output.", _snapshot(), memory)
    assert first.question_type == QuestionType.OUTPUTS
    assert len(memory.turns) == 1

    second = build_contextual_answer("What about that under stress scenario?", _snapshot(), memory)
    assert second.question_type == QuestionType.FOLLOW_UP
    assert "follows your previous question" in second.answer
    assert len(memory.turns) == 2


def test_detect_topics_handles_model_domain_dimensions():
    topics = detect_topics("If revenue drops, what happens to EBITDA, cash, debt and valuation?")
    assert "revenue" in topics
    assert "profitability" in topics
    assert "cash_and_debt" in topics
    assert "valuation" in topics
