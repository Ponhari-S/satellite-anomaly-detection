"""Loading and inference for the saved OrbitGuard baseline model."""

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from backend.schemas import FeatureInput, PredictionResponse


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "ai" / "baseline_logreg.pkl"
SCALER_PATH = ROOT_DIR / "ai" / "feature_scaler.pkl"

FEATURE_NAMES = [
    "sampling", "duration", "len", "mean", "var", "std", "kurtosis", "skew",
    "n_peaks", "smooth10_n_peaks", "smooth20_n_peaks", "diff_peaks", "diff2_peaks",
    "diff_var", "diff2_var", "gaps_squared", "len_weighted", "var_div_duration",
    "var_div_len",
]


@lru_cache
def load_artifacts():
    """Load once per process so each request does not touch disk."""
    if not MODEL_PATH.is_file() or not SCALER_PATH.is_file():
        raise RuntimeError(
            "Saved model artifacts are missing. Expected "
            f"{MODEL_PATH.name} and {SCALER_PATH.name} in ai/."
        )
    return joblib.load(MODEL_PATH), joblib.load(SCALER_PATH)


def predict(features: FeatureInput) -> PredictionResponse:
    model, scaler = load_artifacts()
    values = pd.DataFrame(
        [[getattr(features, name) for name in FEATURE_NAMES]], columns=FEATURE_NAMES
    )
    scaled_values = scaler.transform(values)
    probability = float(model.predict_proba(scaled_values)[0, 1])
    prediction = int(model.predict(scaled_values)[0])
    return PredictionResponse(prediction=prediction, probability=probability)
