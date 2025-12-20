"""Jupyter widget helpers (placeholder)."""
from __future__ import annotations

from typing import Callable

try:
    import ipywidgets as widgets
    from IPython.display import display
except Exception:  # pragma: no cover - optional dependency
    widgets = None
    display = None


def slider(label: str, min_value: float, max_value: float, value: float, on_change: Callable[[float], None]) -> None:
    if widgets is None or display is None:
        return
    w = widgets.FloatSlider(description=label, min=min_value, max=max_value, value=value)
    w.observe(lambda change: on_change(change["new"]), names="value")
    display(w)
