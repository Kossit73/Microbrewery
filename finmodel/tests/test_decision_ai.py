from finmodel.decision_ai import (
    DecisionSessionMemory,
    QuestionType,
    benchmark_catalog,
    build_structured_answer,
    classify_question,
    detect_topics,
)


def _snapshot() -> dict:
    return {
        "production_and_revenues": {"latest_total_revenue": 1200.0, "latest_ebitda": 300.0},
        "financial_statements": {"latest_net_income": 180.0, "latest_cash": 400.0, "latest_debt_balance": 250.0},
        "advanced_analytics": {"valuation_summary": {"equity_irr_annual": 0.17, "equity_moic": 2.1, "enterprise_value_dcf": 3000.0}},
        "ratios": {"dscr": 1.4, "current_ratio": 1.7},
        "latest_annual": {"revenue_growth": 0.08},
    }


def test_classify_question_for_decision_topics_and_follow_up():
    memory = DecisionSessionMemory()
    assert classify_question("Is our EV/EBITDA valuation too high?", memory) == QuestionType.VALUATION
    assert classify_question("Are margins healthy?", memory) == QuestionType.PROFITABILITY
    assert classify_question("Is debt leverage safe?", memory) == QuestionType.LEVERAGE

    first = build_structured_answer("Is valuation aggressive?", _snapshot(), memory)
    assert first.question_type == QuestionType.VALUATION
    assert classify_question("What about that under downside?", memory) == QuestionType.VALUATION


def test_build_structured_answer_contains_required_sections_and_sources():
    memory = DecisionSessionMemory()
    turn = build_structured_answer(
        "Evaluate profitability versus benchmarks",
        _snapshot(),
        memory,
        web_sources=[{"title": "Industry report", "url": "https://example.com/bench"}],
    )
    assert "1) Direct answer" in turn.answer
    assert "2) Internal model analysis" in turn.answer
    assert "3) External benchmark analysis" in turn.answer
    assert "4) Comparison and interpretation" in turn.answer
    assert "5) Decision-quality recommendation" in turn.answer
    assert "6) Sources" in turn.answer
    assert "Live web search" in turn.answer


def test_detect_topics_and_benchmark_catalog():
    topics = detect_topics("If revenue drops what happens to EBITDA margin and debt coverage?")
    assert "revenue" in topics
    assert "profitability" in topics
    assert "leverage" in topics

    benchmarks = benchmark_catalog(QuestionType.VALUATION)
    assert any(b.metric == "EV/EBITDA" for b in benchmarks)
