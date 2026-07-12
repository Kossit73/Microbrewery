from copy import deepcopy
from types import SimpleNamespace

import pandas as pd

import streamlit_app
from brewery_financial_model_all_in_one import DividendPolicy, ModelConfig
from streamlit_app import ComputedResultBundle, _build_draft_signature, _build_sample_assumptions, _draft_is_dirty


def _config_state_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "start_date": "2028-01-01",
                "months": 120,
                "price_inflation_annual": 0.015,
                "cost_inflation_annual": 0.015,
                "tax_rate": 0.25,
                "wacc_annual": 0.11,
                "exit_ev_ebitda_multiple": 8.0,
                "revolver_limit": 750000.0,
                "revolver_interest_annual": 0.085,
                "revolver_target_cash": 250000.0,
                "min_dscr": 1.2,
                "min_interest_coverage": 1.6,
                "max_leverage_ratio": 3.5,
                "temporary_labor_premium_pct": 0.2,
            }
        ]
    )


def _dividend_state_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "enabled": True,
                "model": "cash_sweep",
                "start_month": 60,
                "minimum_cash_position": 500000.0,
                "payout_ratio": 0.25,
            }
        ]
    )


def _sales_plan_state_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"date": pd.Timestamp("2028-01-01"), "sku_id": 1, "channel": "Wholesale", "units": 1000.0},
            {"date": pd.Timestamp("2028-02-01"), "sku_id": 1, "channel": "Wholesale", "units": 1100.0},
        ]
    )


def _completed_bundle() -> ComputedResultBundle:
    cfg = ModelConfig(months=24)
    div = DividendPolicy()
    inputs = _build_sample_assumptions(cfg, div)
    return ComputedResultBundle(
        signature=_build_draft_signature(cfg, div, inputs),
        cfg=cfg,
        div=div,
        inputs=inputs,
        result=None,
        computed_at=0.0,
        base_duration_seconds=0.0,
    )


def test_build_draft_signature_changes_when_inputs_change():
    cfg = ModelConfig(months=24)
    div = DividendPolicy()
    inputs = _build_sample_assumptions(cfg, div)

    original = _build_draft_signature(cfg, div, inputs)
    modified_inputs = deepcopy(inputs)
    modified_inputs.sales_plan.loc[modified_inputs.sales_plan.index[0], "units"] += 1.0

    assert _build_draft_signature(cfg, div, modified_inputs) != original


def test_draft_is_dirty_tracks_last_completed_run_signature():
    cfg = ModelConfig(months=24)
    div = DividendPolicy()
    inputs = _build_sample_assumptions(cfg, div)
    completed_signature = _build_draft_signature(cfg, div, inputs)
    completed_run = ComputedResultBundle(
        signature=completed_signature,
        cfg=cfg,
        div=div,
        inputs=inputs,
        result=None,
        computed_at=0.0,
        base_duration_seconds=0.0,
    )

    assert _draft_is_dirty(completed_signature, completed_run) is False

    modified_inputs = deepcopy(inputs)
    modified_inputs.channels.loc[modified_inputs.channels.index[0], "price_factor"] += 0.05

    assert _draft_is_dirty(_build_draft_signature(cfg, div, modified_inputs), completed_run) is True


def test_get_state_includes_core_controls_and_omits_runtime_bundle(monkeypatch):
    config_df = _config_state_frame()
    session_state = {
        "assump_data_config": config_df,
        streamlit_app._START_YEAR_KEY: 2028,
        streamlit_app._END_YEAR_KEY: 2037,
        streamlit_app._WACC_KEY: 0.11,
        streamlit_app._CURRENT_RESULT_KEY: _completed_bundle(),
    }
    monkeypatch.setattr(streamlit_app, "st", SimpleNamespace(session_state=session_state))

    state = streamlit_app.get_state()

    assert state[streamlit_app._START_YEAR_KEY] == 2028
    assert state[streamlit_app._END_YEAR_KEY] == 2037
    assert state[streamlit_app._WACC_KEY] == 0.11
    assert state["assump_data_config"].equals(config_df)
    assert streamlit_app._CURRENT_RESULT_KEY not in state

    state["assump_data_config"].loc[0, "start_date"] = "2030-01-01"
    assert session_state["assump_data_config"].loc[0, "start_date"] == "2028-01-01"


def test_set_state_restores_saved_case_controls_and_clears_runtime_bundle(monkeypatch):
    config_df = _config_state_frame()
    dividend_df = _dividend_state_frame()
    sales_plan_df = _sales_plan_state_frame()
    session_state = {
        streamlit_app._CURRENT_RESULT_KEY: _completed_bundle(),
        streamlit_app._CURRENT_RESULT_META_KEY: {"cache_hit": False},
        streamlit_app._RUNTIME_DRAFT_SIGNATURE_KEY: "stale-draft",
        streamlit_app._RUNTIME_LAST_RUN_SIGNATURE_KEY: "stale-run",
        streamlit_app._RUNTIME_RESULTS_STALE_KEY: False,
        "assump_timeline_signature": ("2025-01-01", 120),
        "assump_saved_config": pd.DataFrame([{"start_date": "2025-01-01"}]),
        "assump_work_config": pd.DataFrame([{"start_date": "2025-01-01"}]),
        "assump_edit_config": True,
        "assump_data_sales_plan": pd.DataFrame([{"month": "2025-01", "sku_id": 1, "channel": "Wholesale", "units": 999.0}]),
        "assump_saved_sales_plan": pd.DataFrame([{"month": "2025-01", "sku_id": 1, "channel": "Wholesale", "units": 999.0}]),
        "assump_work_sales_plan": pd.DataFrame([{"month": "2025-01", "sku_id": 1, "channel": "Wholesale", "units": 999.0}]),
        "assump_edit_sales_plan": True,
        "assump_sales_plan_frequency_selector": "Yearly",
        "assump_prev_sales_plan_frequency": "yearly",
        "input_inc_config": 0.3,
        "field_config_0_start_date": "bad-value",
        "assump_row_select_config": 7,
    }
    monkeypatch.setattr(streamlit_app, "st", SimpleNamespace(session_state=session_state))

    streamlit_app.set_state(
        {
            "assump_data_config": config_df,
            "assump_data_dividend": dividend_df,
            "assump_data_sales_plan_base": sales_plan_df,
            "assump_sales_plan_frequency": "monthly",
        }
    )

    assert session_state[streamlit_app._START_YEAR_KEY] == 2028
    assert session_state[streamlit_app._END_YEAR_KEY] == 2037
    assert session_state[streamlit_app._WACC_KEY] == 0.11
    assert session_state[streamlit_app._EXIT_MULTIPLE_KEY] == 8.0
    assert session_state[streamlit_app._PRICE_INFLATION_KEY] == 0.015
    assert session_state[streamlit_app._COST_INFLATION_KEY] == 0.015
    assert session_state[streamlit_app._DIVIDEND_START_KEY] == 60
    assert session_state[streamlit_app._MIN_CASH_KEY] == 500000.0

    assert streamlit_app._CURRENT_RESULT_KEY not in session_state
    assert streamlit_app._CURRENT_RESULT_META_KEY not in session_state
    assert streamlit_app._RUNTIME_DRAFT_SIGNATURE_KEY not in session_state
    assert streamlit_app._RUNTIME_LAST_RUN_SIGNATURE_KEY not in session_state
    assert streamlit_app._RUNTIME_RESULTS_STALE_KEY not in session_state
    assert "assump_timeline_signature" not in session_state

    assert session_state["assump_saved_config"].equals(config_df)
    assert session_state["assump_work_config"].equals(config_df)
    assert session_state["assump_saved_dividend"].equals(dividend_df)
    assert session_state["assump_work_dividend"].equals(dividend_df)
    assert session_state["assump_edit_config"] is False
    assert session_state["assump_edit_dividend"] is False
    assert session_state["assump_inc_config"] == 0.0
    assert session_state["assump_inc_dividend"] == 0.0

    assert session_state["assump_sales_plan_frequency"] == "monthly"
    assert session_state["assump_prev_sales_plan_frequency"] == "monthly"
    assert session_state["assump_sales_plan_frequency_selector"] == "Monthly"
    assert session_state["assump_edit_sales_plan"] is False
    assert session_state["assump_inc_sales_plan"] == 0.0
    assert "assump_data_sales_plan" not in session_state
    assert "assump_saved_sales_plan" not in session_state
    assert "assump_work_sales_plan" not in session_state

    assert "input_inc_config" not in session_state
    assert "field_config_0_start_date" not in session_state
    assert "assump_row_select_config" not in session_state
