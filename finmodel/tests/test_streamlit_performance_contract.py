from copy import deepcopy

import pandas as pd

from brewery_financial_model_all_in_one import DividendPolicy, ModelConfig
from streamlit_app import (
    LazyArtifactBundle,
    _build_draft_signature,
    _build_sample_assumptions,
    _compute_monte_carlo_payload,
    _compute_predictive_payload,
    _lazy_artifact_is_stale,
)


def test_build_draft_signature_is_stable_for_equal_drafts_and_changes_with_inputs():
    cfg = ModelConfig()
    div = DividendPolicy()
    inputs_a = _build_sample_assumptions(cfg, div)
    inputs_b = _build_sample_assumptions(cfg, div)

    signature_a = _build_draft_signature(cfg, div, inputs_a)
    signature_b = _build_draft_signature(cfg, div, inputs_b)

    assert signature_a == signature_b

    changed_inputs = deepcopy(inputs_b)
    changed_inputs.skus.loc[0, "markup_pct"] = float(changed_inputs.skus.loc[0, "markup_pct"]) + 0.01

    assert _build_draft_signature(cfg, div, changed_inputs) != signature_a


def test_lazy_artifact_staleness_requires_matching_result_and_config_signatures():
    artifact = LazyArtifactBundle(
        result_signature="run-1",
        config_signature="cfg-1",
        payload=None,
        computed_at=0.0,
        duration_seconds=0.5,
    )

    assert _lazy_artifact_is_stale(artifact, "run-1", "cfg-1") is False
    assert _lazy_artifact_is_stale(artifact, "run-2", "cfg-1") is True
    assert _lazy_artifact_is_stale(artifact, "run-1", "cfg-2") is True


def test_compute_monte_carlo_payload_is_deterministic_when_sigma_is_zero():
    payload = _compute_monte_carlo_payload(base_ebitda=125.0, sims=4, sigma_pct=0.0)

    chart_df = payload["chart_df"]
    summary = payload["summary"]

    assert payload["message"] is None
    assert chart_df["ebitda_sim"].tolist() == [125.0, 125.0, 125.0, 125.0]
    assert summary == {
        "simulations": 4,
        "mean": 125.0,
        "p05": 125.0,
        "p50": 125.0,
        "p95": 125.0,
    }


def test_compute_predictive_payload_projects_linear_revenue_trend():
    annual = pd.DataFrame({"total_revenue": [10.0, 20.0, 30.0]}, index=[2025, 2026, 2027])

    payload = _compute_predictive_payload(annual, forecast_steps=2)
    table = payload["table"]

    assert payload["message"] is None
    assert list(table.columns) == ["actual_revenue", "prediction_step_2"]
    assert table["prediction_step_2"].tolist() == [30.0, 40.0, 50.0]
