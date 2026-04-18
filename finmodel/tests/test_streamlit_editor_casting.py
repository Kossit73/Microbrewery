import pandas as pd

from streamlit_app import _cast_value_for_dtype


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
