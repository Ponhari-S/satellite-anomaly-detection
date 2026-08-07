"""Temporary in-memory result store and raw-telemetry pipeline adapter."""

from backend.model_service import predict
from backend.schemas import FeatureInput, StoredResult

results: list[StoredResult] = []


def features_from_telemetry(reading: dict) -> FeatureInput:
    """Provide a temporary feature vector until segment feature extraction is added.

    A model prediction needs a complete time-series segment, while the simulator
    emits individual readings. These neutral, deterministic placeholder values
    keep the streaming loop operational; replace this function with the project's
    segment feature extractor when that component is in scope.
    """
    value = float(reading["value"])
    return FeatureInput(
        sampling=int(reading.get("sampling", 1)), duration=1, len=1, mean=value,
        var=0.0, std=0.0, kurtosis=0.0, skew=0.0, n_peaks=0,
        smooth10_n_peaks=0, smooth20_n_peaks=0, diff_peaks=0, diff2_peaks=0,
        diff_var=0.0, diff2_var=0.0, gaps_squared=0, len_weighted=1,
        var_div_duration=0.0, var_div_len=0.0,
    )


def score_and_store(reading: dict) -> StoredResult:
    prediction = predict(features_from_telemetry(reading))
    result = StoredResult(
        timestamp=str(reading["timestamp"]), channel=str(reading["channel"]),
        prediction=prediction.prediction, probability=prediction.probability,
    )
    results.append(result)
    return result
