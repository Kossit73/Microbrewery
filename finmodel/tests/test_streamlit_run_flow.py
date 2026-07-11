from copy import deepcopy

from brewery_financial_model_all_in_one import DividendPolicy, ModelConfig
from streamlit_app import ComputedResultBundle, _build_draft_signature, _build_sample_assumptions, _draft_is_dirty


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

