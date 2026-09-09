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
    return list(results)


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
            # Safely serialize features for both Pydantic v1 (.dict()) and v2 (.model_dump())
            feat_dict = feat_obj.model_dump() if hasattr(feat_obj, "model_dump") else feat_obj.dict()
            # Send the normalized raw telemetry row plus its live model result and extracted feature vector.
            await websocket.send_json({
                **reading,
                "prediction": result.prediction,
                "probability": result.probability,
                "features": feat_dict,
            })
    except WebSocketDisconnect:
        logger.info("Telemetry client disconnected")
    except Exception:
        logger.exception("Telemetry stream failed")
        await websocket.close(code=1011)


_channel_graph_cache: dict | None = None


@app.get("/channel-graph")
def channel_graph() -> dict:
    """
    Real, computed channel relationships — replaces the frontend's
    previous hardcoded/illustrative edge list with actual correlation
    values derived from the dataset (see ai/graph_model/graph_construction.py).

    Returns edges with their real correlation strength, so the dashboard's
    topology graph reflects genuine relationships rather than a fabricated
    layout. Computed once and cached, since it's derived from static
    historical data, not live-changing.
    """
    global _channel_graph_cache
    if _channel_graph_cache is not None:
        return _channel_graph_cache

    import json
    from pathlib import Path

    cache_file = Path(__file__).resolve().parents[1] / "ai" / "channel_graph.json"
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                _channel_graph_cache = json.load(f)
                return _channel_graph_cache
        except Exception:
            logger.exception("Failed to load precomputed channel_graph.json, recomputing...")

    import sys
    import numpy as np
    import pandas as pd

    graph_model_dir = str(Path(__file__).resolve().parents[1] / "ai" / "graph_model")
    if graph_model_dir not in sys.path:
        sys.path.insert(0, graph_model_dir)
    from graph_construction import build_graph_snapshots, CHANNELS

    raw_df = pd.read_csv(Path(__file__).resolve().parents[1] / "datasets" / "dataset.csv")
    snapshots = build_graph_snapshots(raw_df, window="1h")
    snapshots = [s for s in snapshots if len(s["active_channels"]) >= 2]

    avg_adj = np.zeros((len(CHANNELS), len(CHANNELS)))
    counts = np.zeros((len(CHANNELS), len(CHANNELS)))
    for s in snapshots:
        mask = s["adjacency"] > 0
        avg_adj += s["adjacency"]
        counts += mask
    avg_adj = np.divide(avg_adj, counts, out=np.zeros_like(avg_adj), where=counts > 0)

    edges = []
    for i in range(len(CHANNELS)):
        for j in range(i + 1, len(CHANNELS)):
            strength = float(avg_adj[i, j])
            if strength > 0.1:  # only report meaningfully-correlated pairs
                edges.append({
                    "source": CHANNELS[i],
                    "target": CHANNELS[j],
                    "strength": round(strength, 3),
                })

    edges.sort(key=lambda e: -e["strength"])
    _channel_graph_cache = {"channels": CHANNELS, "edges": edges}

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(_channel_graph_cache, f, indent=2)
    except Exception:
        logger.warning("Could not persist channel_graph.json to disk")

    return _channel_graph_cache