"""FastAPI application for OrbitGuard telemetry and baseline inference."""

import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.feature_extractor import features_from_telemetry
from backend.model_service import predict
from backend.pipeline import results
from backend.schemas import FeatureInput, PredictionResponse, StoredResult
from backend.telemetry_source import telemetry_source

logger = logging.getLogger(__name__)
app = FastAPI(title="OrbitGuard Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root() -> dict[str, str]:
    return {"message": "OrbitGuard Backend is running. Visit /docs for API documentation."}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict_telemetry(features: FeatureInput) -> PredictionResponse:
    try:
        return predict(features)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed.") from exc


@app.get("/results", response_model=list[StoredResult])
def get_results() -> list[StoredResult]:
    return results


@app.websocket("/stream")
async def stream_telemetry(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        async for reading in telemetry_source():
            feat_obj = features_from_telemetry(reading)
            result = predict(feat_obj)
            stored = StoredResult(
                timestamp=str(reading["timestamp"]),
                channel=str(reading["channel"]),
                prediction=result.prediction,
                probability=result.probability,
            )
            results.append(stored)
            # Send the normalized raw telemetry row plus its live model result and extracted feature vector.
            await websocket.send_json({
                **reading,
                "prediction": result.prediction,
                "probability": result.probability,
                "features": feat_obj.model_dump(),
            })
    except WebSocketDisconnect:
        logger.info("Telemetry client disconnected")
    except Exception:
        logger.exception("Telemetry stream failed")
        await websocket.close(code=1011)