"""Temporary in-memory result store and raw-telemetry pipeline adapter."""

from collections import deque

from backend.model_service import predict
from backend.schemas import FeatureInput, StoredResult
from backend.feature_extractor import features_from_telemetry as real_features_from_telemetry

results: deque[StoredResult] = deque(maxlen=1000)


def features_from_telemetry(reading: dict) -> FeatureInput:
    return real_features_from_telemetry(reading)


def score_and_store(reading: dict) -> StoredResult:
    prediction = predict(features_from_telemetry(reading))
    result = StoredResult(
        timestamp=str(reading["timestamp"]), channel=str(reading["channel"]),
        prediction=prediction.prediction, probability=prediction.probability,
    )
    results.append(result)
    return result
