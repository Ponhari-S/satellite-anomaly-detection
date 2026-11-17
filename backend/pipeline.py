"""Temporary in-memory result store and raw-telemetry pipeline adapter."""

from collections import deque

from backend.model_service import predict
from backend.schemas import FeatureInput, StoredResult
from backend.feature_extractor import features_from_telemetry as real_features_from_telemetry

results: deque[StoredResult] = deque(maxlen=1000)


def features_from_telemetry(reading: dict) -> FeatureInput:
    return real_features_from_telemetry(reading)


<<<<<<< HEAD
def score_and_store(reading: dict, model_type: str | None = None) -> StoredResult:
    ch = str(reading.get("channel", ""))
    prediction = predict(features_from_telemetry(reading), channel=ch, model_type=model_type)
    result = StoredResult(
        timestamp=str(reading["timestamp"]),
        channel=ch,
        prediction=prediction.prediction,
        probability=prediction.probability,
        model_name=prediction.model_name,
=======
def score_and_store(reading: dict) -> StoredResult:
    prediction = predict(features_from_telemetry(reading))
    result = StoredResult(
        timestamp=str(reading["timestamp"]), channel=str(reading["channel"]),
        prediction=prediction.prediction, probability=prediction.probability,
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    )
    results.append(result)
    return result
