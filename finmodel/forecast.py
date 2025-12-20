"""Forecasting engine with simple auto-model selection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

try:  # optional
    from statsmodels.tsa.arima.model import ARIMA
except Exception:  # pragma: no cover - optional dependency
    ARIMA = None  # type: ignore

try:  # optional
    from prophet import Prophet
except Exception:  # pragma: no cover
    Prophet = None  # type: ignore


@dataclass
class ForecastResult:
    model_name: str
    forecast: pd.Series
    metrics: Dict[str, float]


class ForecastEngine:
    """Fits multiple forecasters and selects the best via backtests."""

    def __init__(self, freq: str = "A") -> None:
        self.freq = freq

    def forecast(self, series: pd.Series, periods: int) -> ForecastResult:
        candidates = {
            "naive": self._forecast_naive,
            "arima": self._forecast_arima,
            "prophet": self._forecast_prophet,
        }
        metrics: Dict[str, float] = {}
        forecasts: Dict[str, pd.Series] = {}
        for name, fn in candidates.items():
            try:
                fc = fn(series, periods)
                forecasts[name] = fc
                metrics[name] = self._mae_backtest(series, fn)
            except Exception:
                continue
        if not forecasts:
            raise RuntimeError("No forecast models succeeded")
        best = min(metrics, key=metrics.get)
        return ForecastResult(model_name=best, forecast=forecasts[best], metrics=metrics)

    @staticmethod
    def _mae_backtest(series: pd.Series, forecaster) -> float:
        split = int(len(series) * 0.8)
        train, test = series.iloc[:split], series.iloc[split:]
        if len(test) == 0:
            return 0.0
        fc = forecaster(train, len(test))
        return float(np.mean(np.abs(test.values - fc.values[: len(test)])))

    @staticmethod
    def _forecast_naive(series: pd.Series, periods: int) -> pd.Series:
        last = series.iloc[-1]
        idx = pd.date_range(series.index[-1], periods=periods + 1, freq=series.index.freq or "A")[1:]
        return pd.Series(last, index=idx)

    def _forecast_arima(self, series: pd.Series, periods: int) -> pd.Series:
        if ARIMA is None:
            raise RuntimeError("statsmodels not available")
        model = ARIMA(series, order=(1, 0, 0)).fit()
        fc = model.forecast(periods)
        return pd.Series(fc, index=pd.date_range(series.index[-1], periods=periods + 1, freq=series.index.freq or self.freq)[1:])

    def _forecast_prophet(self, series: pd.Series, periods: int) -> pd.Series:
        if Prophet is None:
            raise RuntimeError("prophet not available")
        df = pd.DataFrame({"ds": series.index, "y": series.values})
        model = Prophet()
        model.fit(df)
        future = model.make_future_dataframe(periods=periods, freq=self.freq)
        forecast = model.predict(future)
        fc = forecast.set_index("ds")["yhat"].iloc[-periods:]
        return fc
