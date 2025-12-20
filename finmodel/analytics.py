"""Analytics helpers (ML, regression, classification)."""
from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier


class MultiplesModel:
    """Simple wrapper for an ML-based EV/EBITDA multiple predictor."""

    def __init__(self, model: Optional[Any] = None):
        self.model = model or LinearRegression()

    def fit(self, X: np.ndarray, y: np.ndarray) -> "MultiplesModel":
        self.model.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.model.predict(X)

    def __call__(self, revenue: float) -> float:
        X = np.array([[revenue]])
        return float(self.predict(X)[0])

    def save(self, path: Path) -> None:
        with path.open("wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def load(cls, path: Path) -> "MultiplesModel":
        with path.open("rb") as f:
            model = pickle.load(f)
        return cls(model=model)


@dataclass
class AnalyticsEngine:
    """Lightweight analytics helpers used by valuation workflows."""

    cost_model: Any = None
    churn_model: Any = None

    def fit_cost_regression(self, X: np.ndarray, y: np.ndarray, model_type: str = "linear") -> Dict[str, float]:
        if model_type == "random_forest":
            model = RandomForestRegressor(n_estimators=50, random_state=0)
        else:
            model = LinearRegression()
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        self.cost_model = model
        return {
            "mae": mean_absolute_error(y_test, preds),
            "rmse": mean_squared_error(y_test, preds) ** 0.5,
        }

    def fit_churn_classifier(self, X: np.ndarray, y: np.ndarray, model_type: str = "logistic") -> Dict[str, float]:
        if model_type == "random_forest":
            model = RandomForestClassifier(n_estimators=100, random_state=0)
        else:
            model = LogisticRegression(max_iter=500)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=0)
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        acc = np.mean(preds == y_test)
        self.churn_model = model
        return {"accuracy": float(acc)}

    def predicted_cost(self, X: np.ndarray) -> Optional[np.ndarray]:
        if self.cost_model is None:
            return None
        return self.cost_model.predict(X)

    def churn_probability(self, X: np.ndarray) -> Optional[np.ndarray]:
        if self.churn_model is None:
            return None
        if hasattr(self.churn_model, "predict_proba"):
            return self.churn_model.predict_proba(X)[:, 1]
        return self.churn_model.predict(X)
