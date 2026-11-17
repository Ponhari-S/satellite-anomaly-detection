<<<<<<< HEAD
"""FastAPI application for OrbitGuard telemetry and multi-model inference (Dynamic Graph + GRU & Logistic Regression)."""

import json
import logging
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
=======
"""FastAPI application for OrbitGuard telemetry and baseline inference."""

import logging

>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.feature_extractor import features_from_telemetry
<<<<<<< HEAD
from backend.model_service import predict, CHANNELS
=======
from backend.model_service import predict
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
from backend.pipeline import results
from backend.schemas import FeatureInput, PredictionResponse, StoredResult
from backend.telemetry_source import telemetry_source

logger = logging.getLogger(__name__)
<<<<<<< HEAD
app = FastAPI(title="OrbitGuard Backend", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
=======
app = FastAPI(title="OrbitGuard Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD
# Rolling buffer of recent telemetry readings for live dynamic graph correlation tracking
_live_channel_buffers: dict[str, deque] = defaultdict(lambda: deque(maxlen=60))


=======
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
@app.get("/")
def root() -> dict[str, str]:
    return {"message": "OrbitGuard Backend is running. Visit /docs for API documentation."}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
<<<<<<< HEAD
def predict_telemetry(
    features: FeatureInput,
    model_type: str | None = None,
    channel: str | None = None,
) -> PredictionResponse:
    try:
        return predict(features, channel=channel, model_type=model_type)
=======
def predict_telemetry(features: FeatureInput) -> PredictionResponse:
    try:
        return predict(features)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
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
<<<<<<< HEAD

    # Query parameters for configurable stream latency and active model selection
    delay_param = websocket.query_params.get("delay")
    speed_param = websocket.query_params.get("speed")
    model_param = websocket.query_params.get("model_type", "graph_gru")

    if speed_param == "benchmark":
        delay = 0.0
    elif delay_param is not None:
        try:
            delay = float(delay_param)
        except ValueError:
            delay = 0.08
    else:
        delay = 0.08

    try:
        async for reading in telemetry_source(delay_between_frames=delay):
            ch = str(reading["channel"])
            val = float(reading["value"])
            _live_channel_buffers[ch].append(val)

            feat_obj = features_from_telemetry(reading)
            result = predict(feat_obj, channel=ch, model_type=model_param)

            stored = StoredResult(
                timestamp=str(reading["timestamp"]),
                channel=ch,
=======
    try:
        async for reading in telemetry_source():
            feat_obj = features_from_telemetry(reading)
            result = predict(feat_obj)
            stored = StoredResult(
                timestamp=str(reading["timestamp"]),
                channel=str(reading["channel"]),
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
                prediction=result.prediction,
                probability=result.probability,
                model_name=result.model_name,
            )
            results.append(stored)
<<<<<<< HEAD

            # Safely serialize features for both Pydantic v1 (.dict()) and v2 (.model_dump())
            feat_dict = feat_obj.model_dump() if hasattr(feat_obj, "model_dump") else feat_obj.dict()

=======
            # Safely serialize features for both Pydantic v1 (.dict()) and v2 (.model_dump())
            feat_dict = feat_obj.model_dump() if hasattr(feat_obj, "model_dump") else feat_obj.dict()
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
            # Send the normalized raw telemetry row plus its live model result and extracted feature vector.
            await websocket.send_json({
                **reading,
                "prediction": result.prediction,
                "probability": result.probability,
                "model_name": result.model_name,
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
<<<<<<< HEAD
    """Precomputed baseline correlation graph across the 9 OPS-SAT channels."""
=======
    """
    Real, computed channel relationships — replaces the frontend's
    previous hardcoded/illustrative edge list with actual correlation
    values derived from the dataset (see ai/graph_model/graph_construction.py).

    Returns edges with their real correlation strength, so the dashboard's
    topology graph reflects genuine relationships rather than a fabricated
    layout. Computed once and cached, since it's derived from static
    historical data, not live-changing.
    """
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    global _channel_graph_cache
    if _channel_graph_cache is not None:
        return _channel_graph_cache

<<<<<<< HEAD
=======
    import json
    from pathlib import Path

>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    cache_file = Path(__file__).resolve().parents[1] / "ai" / "channel_graph.json"
    if cache_file.is_file():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                _channel_graph_cache = json.load(f)
                return _channel_graph_cache
        except Exception:
            logger.exception("Failed to load precomputed channel_graph.json, recomputing...")

    import sys
<<<<<<< HEAD
=======
    import numpy as np
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    import pandas as pd

    graph_model_dir = str(Path(__file__).resolve().parents[1] / "ai" / "graph_model")
    if graph_model_dir not in sys.path:
        sys.path.insert(0, graph_model_dir)
<<<<<<< HEAD
    from graph_construction import build_graph_snapshots, CHANNELS as G_CHANNELS
=======
    from graph_construction import build_graph_snapshots, CHANNELS
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94

    raw_df = pd.read_csv(Path(__file__).resolve().parents[1] / "datasets" / "dataset.csv")
    snapshots = build_graph_snapshots(raw_df, window="1h")
    snapshots = [s for s in snapshots if len(s["active_channels"]) >= 2]

<<<<<<< HEAD
    avg_adj = np.zeros((len(G_CHANNELS), len(G_CHANNELS)))
    counts = np.zeros((len(G_CHANNELS), len(G_CHANNELS)))
=======
    avg_adj = np.zeros((len(CHANNELS), len(CHANNELS)))
    counts = np.zeros((len(CHANNELS), len(CHANNELS)))
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    for s in snapshots:
        mask = s["adjacency"] > 0
        avg_adj += s["adjacency"]
        counts += mask
    avg_adj = np.divide(avg_adj, counts, out=np.zeros_like(avg_adj), where=counts > 0)

    edges = []
<<<<<<< HEAD
    for i in range(len(G_CHANNELS)):
        for j in range(i + 1, len(G_CHANNELS)):
            strength = float(avg_adj[i, j])
            if strength > 0.1:
                edges.append({
                    "source": G_CHANNELS[i],
                    "target": G_CHANNELS[j],
=======
    for i in range(len(CHANNELS)):
        for j in range(i + 1, len(CHANNELS)):
            strength = float(avg_adj[i, j])
            if strength > 0.1:  # only report meaningfully-correlated pairs
                edges.append({
                    "source": CHANNELS[i],
                    "target": CHANNELS[j],
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
                    "strength": round(strength, 3),
                })

    edges.sort(key=lambda e: -e["strength"])
<<<<<<< HEAD
    _channel_graph_cache = {"channels": G_CHANNELS, "edges": edges}
=======
    _channel_graph_cache = {"channels": CHANNELS, "edges": edges}
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(_channel_graph_cache, f, indent=2)
    except Exception:
        logger.warning("Could not persist channel_graph.json to disk")

<<<<<<< HEAD
    return _channel_graph_cache


@app.get("/channel-graph/live")
def live_channel_graph() -> dict:
    """
    Dynamic Graph Correlation: Computes live Pearson cross-correlations A^(t)
    directly across the rolling stream buffer of all 9 channels (matching Equation 4).
    """
    min_len = min((len(_live_channel_buffers[ch]) for ch in CHANNELS), default=0)
    if min_len < 8:
        # Buffer still populating: return baseline graph with is_live=False indicator
        base = channel_graph()
        return {**base, "is_live": False, "buffer_samples": min_len}

    # Extract aligned window arrays for each channel
    series = {ch: np.array(list(_live_channel_buffers[ch])[-min_len:], dtype=float) for ch in CHANNELS}

    edges = []
    for i in range(len(CHANNELS)):
        ch_i = CHANNELS[i]
        x_i = series[ch_i]
        std_i = np.std(x_i)
        if std_i == 0:
            continue
        for j in range(i + 1, len(CHANNELS)):
            ch_j = CHANNELS[j]
            x_j = series[ch_j]
            std_j = np.std(x_j)
            if std_j == 0:
                continue
            corr = float(np.corrcoef(x_i, x_j)[0, 1])
            if not np.isnan(corr) and abs(corr) > 0.05:
                edges.append({
                    "source": ch_i,
                    "target": ch_j,
                    "strength": round(abs(corr), 3),
                })

    edges.sort(key=lambda e: -e["strength"])
    return {
        "channels": CHANNELS,
        "edges": edges,
        "is_live": True,
        "buffer_samples": min_len,
    }



@app.get("/channel-graph/live")
def live_channel_graph() -> dict:
    """
    Dynamic Graph Correlation: Computes live Pearson cross-correlations A^(t)
    directly across the rolling stream buffer of all 9 channels (matching Equation 4).
    """
    min_len = min((len(_live_channel_buffers[ch]) for ch in CHANNELS), default=0)
    if min_len < 8:
        # Buffer still populating: return baseline graph with is_live=False indicator
        base = channel_graph()
        return {**base, "is_live": False, "buffer_samples": min_len}

    # Extract aligned window arrays for each channel
    series = {ch: np.array(list(_live_channel_buffers[ch])[-min_len:], dtype=float) for ch in CHANNELS}

    edges = []
    for i in range(len(CHANNELS)):
        ch_i = CHANNELS[i]
        x_i = series[ch_i]
        std_i = np.std(x_i)
        if std_i == 0:
            continue
        for j in range(i + 1, len(CHANNELS)):
            ch_j = CHANNELS[j]
            x_j = series[ch_j]
            std_j = np.std(x_j)
            if std_j == 0:
                continue
            corr = float(np.corrcoef(x_i, x_j)[0, 1])
            if not np.isnan(corr) and abs(corr) > 0.05:
                edges.append({
                    "source": ch_i,
                    "target": ch_j,
                    "strength": round(abs(corr), 3),
                })

    edges.sort(key=lambda e: -e["strength"])
    return {
        "channels": CHANNELS,
        "edges": edges,
        "is_live": True,
        "buffer_samples": min_len,
    }
=======
    return _channel_graph_cache
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
