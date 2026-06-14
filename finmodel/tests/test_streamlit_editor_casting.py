import pandas as pd
import pytest

from streamlit_app import _align_year_schedule_df, _apply_yearly_increment, _cast_value_for_dtype


def test_cast_value_for_dtype_preserves_bool_columns():
    column = pd.Series([True, False], dtype="bool")
    assert _cast_value_for_dtype(column, True) is True
    assert _cast_value_for_dtype(column, "false") is False


def test_cast_value_for_dtype_handles_numeric_columns():
    int_col = pd.Series([1, 2], dtype="int64")
    float_col = pd.Series([1.2, 2.3], dtype="float64")

    assert _cast_value_for_dtype(int_col, 3.9) == 3
    assert _cast_value_for_dtype(int_col, None) == 0
    assert _cast_value_for_dtype(float_col, "4.5") == 4.5
    assert _cast_value_for_dtype(float_col, None) == 0.0


def test_apply_yearly_increment_scales_year_columns_progressively():
    df = pd.DataFrame([{"role": "Ops", "Year 1": 10.0, "Year 2": 10.0, "Year 3": 10.0}])

    updated = _apply_yearly_increment(df, 0.10)

    assert updated.loc[0, "Year 1"] == 10.0
    assert updated.loc[0, "Year 2"] == 11.0
    assert updated.loc[0, "Year 3"] == pytest.approx(12.1)


def test_align_year_schedule_df_extends_last_available_year_and_drops_extra_years():
    current = pd.DataFrame([{"role": "Ops", "Year 1": 1.0, "Year 2": 2.0, "Year 4": 9.0}])
    template = pd.DataFrame([{"role": "Ops", "Year 1": 0.0, "Year 2": 0.0, "Year 3": 0.0}])

    aligned = _align_year_schedule_df(current, template)

    assert list(aligned.columns) == ["role", "Year 1", "Year 2", "Year 3"]
    assert aligned.loc[0, "Year 1"] == 1.0
    assert aligned.loc[0, "Year 2"] == 2.0
    assert aligned.loc[0, "Year 3"] == 9.0
