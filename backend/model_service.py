<<<<<<< HEAD
"""Loading and inference for OrbitGuard models: Baseline Logistic Regression and Dynamic Graph + GRU."""

import json
import logging
import os
from collections import deque
=======
"""Loading and inference for the saved OrbitGuard baseline model."""

>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
from functools import lru_cache
from pathlib import Path

import joblib
<<<<<<< HEAD
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from backend.schemas import FeatureInput, PredictionResponse

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "ai" / "baseline_logreg.pkl"
GRAPH_MODEL_PATH = ROOT_DIR / "ai" / "graph_model.pt"
SCALER_PATH = ROOT_DIR / "ai" / "feature_scaler.pkl"
CHANNEL_GRAPH_PATH = ROOT_DIR / "ai" / "channel_graph.json"

CHANNELS = [
    "CADC0872", "CADC0873", "CADC0874",
    "CADC0884", "CADC0886", "CADC0888", "CADC0890", "CADC0892", "CADC0894"
]
CHANNEL_TO_INDEX = {ch: idx for idx, ch in enumerate(CHANNELS)}
=======
import pandas as pd

from backend.schemas import FeatureInput, PredictionResponse


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "ai" / "baseline_logreg.pkl"
SCALER_PATH = ROOT_DIR / "ai" / "feature_scaler.pkl"
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94

FEATURE_NAMES = [
    "sampling", "duration", "len", "mean", "var", "std", "kurtosis", "skew",
    "n_peaks", "smooth10_n_peaks", "smooth20_n_peaks", "diff_peaks", "diff2_peaks",
    "diff_var", "diff2_var", "gaps_squared", "len_weighted", "var_div_duration",
    "var_div_len",
]


<<<<<<< HEAD
class DynamicGraphAnomalyDetector(nn.Module):
    """Spatio-temporal Dynamic Graph + GRU model matching paper Section IV-D2."""

    def __init__(self, num_nodes=9, node_feature_dim=19, hidden_dim=32):
        super().__init__()
        self.num_nodes = num_nodes
        self.node_encoder = nn.Linear(node_feature_dim, hidden_dim)
        self.graph_conv = nn.Linear(hidden_dim, hidden_dim)
        self.temporal = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
        self.classifier = nn.Linear(hidden_dim, 1)
        self.activation = nn.ReLU()

    def forward(self, node_features: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        """
        node_features: [batch, time, num_nodes, node_feature_dim]
        adjacency:     [batch, time, num_nodes, num_nodes]
        returns:       [batch, num_nodes] anomaly logits
        """
        batch, time_steps, num_nodes, feat_dim = node_features.shape
        h = self.activation(self.node_encoder(node_features))
        h_conv = torch.matmul(adjacency, h)
        h_conv = self.activation(self.graph_conv(h_conv))
        h_seq = h_conv.permute(0, 2, 1, 3).reshape(batch * num_nodes, time_steps, -1)
        _, h_final = self.temporal(h_seq)
        h_final = h_final.squeeze(0).reshape(batch, num_nodes, -1)
        logits = self.classifier(h_final).squeeze(-1)
        return logits


@lru_cache
def load_artifacts():
    """Load baseline artifacts once per process."""
=======
@lru_cache
def load_artifacts():
    """Load once per process so each request does not touch disk."""
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    if not MODEL_PATH.is_file() or not SCALER_PATH.is_file():
        raise RuntimeError(
            "Saved model artifacts are missing. Expected "
            f"{MODEL_PATH.name} and {SCALER_PATH.name} in ai/."
        )
<<<<<<< HEAD
    logreg_model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    # Load Dynamic Graph + GRU model
    graph_model = None
    if GRAPH_MODEL_PATH.is_file():
        try:
            ckpt = torch.load(GRAPH_MODEL_PATH, weights_only=False, map_location="cpu")
            num_nodes = ckpt.get("num_nodes", len(CHANNELS))
            feat_dim = ckpt.get("node_feature_dim", len(FEATURE_NAMES))
            hidden_dim = ckpt.get("hidden_dim", 32)
            graph_model = DynamicGraphAnomalyDetector(
                num_nodes=num_nodes, node_feature_dim=feat_dim, hidden_dim=hidden_dim
            )
            graph_model.load_state_dict(ckpt["model_state_dict"])
            graph_model.eval()
            logger.info("Successfully loaded Dynamic Graph + GRU model artifact from %s", GRAPH_MODEL_PATH)
        except Exception:
            logger.exception("Failed to load Dynamic Graph + GRU model checkpoint")

    # Load baseline channel adjacency matrix
    adj_matrix = np.eye(len(CHANNELS), dtype=np.float32)
    if CHANNEL_GRAPH_PATH.is_file():
        try:
            with open(CHANNEL_GRAPH_PATH, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            for edge in cdata.get("edges", []):
                src = edge.get("source")
                tgt = edge.get("target")
                val = float(edge.get("strength", 0.0))
                if src in CHANNEL_TO_INDEX and tgt in CHANNEL_TO_INDEX:
                    i, j = CHANNEL_TO_INDEX[src], CHANNEL_TO_INDEX[tgt]
                    adj_matrix[i, j] = val
                    adj_matrix[j, i] = val
            # Row-normalize adjacency
            row_sums = adj_matrix.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1.0
            adj_matrix = adj_matrix / row_sums
        except Exception:
            logger.warning("Could not build normalized adjacency from channel_graph.json, using identity.")

    return logreg_model, scaler, graph_model, adj_matrix


# State buffers for multi-sensor graph spatiotemporal inference
_channel_features: dict[str, np.ndarray] = {
    ch: np.zeros(len(FEATURE_NAMES), dtype=np.float32) for ch in CHANNELS
}
_graph_sequence_buffer: deque[np.ndarray] = deque(maxlen=5)


def predict_logreg(scaled_values: np.ndarray) -> tuple[int, float]:
    logreg_model, _, _, _ = load_artifacts()
    probability = float(logreg_model.predict_proba(scaled_values)[0, 1])
    prediction = int(logreg_model.predict(scaled_values)[0])
    return prediction, probability


def predict_graph_gru(
    scaled_values: np.ndarray, channel: str | None = None
) -> tuple[int, float]:
    _, _, graph_model, adj_matrix = load_artifacts()
    if graph_model is None:
        raise RuntimeError("Dynamic Graph + GRU model artifact is not loaded.")

    ch_name = channel if channel in CHANNEL_TO_INDEX else CHANNELS[0]
    ch_idx = CHANNEL_TO_INDEX[ch_name]

    # Update channel feature state
    _channel_features[ch_name] = scaled_values[0].astype(np.float32)

    # Snapshot of all 9 nodes: [9, 19]
    current_snapshot = np.array([_channel_features[ch] for ch in CHANNELS], dtype=np.float32)
    _graph_sequence_buffer.append(current_snapshot)

    # Build sequence of length 5 (pad with earliest snapshot if buffer still filling)
    seq = list(_graph_sequence_buffer)
    while len(seq) < 5:
        seq.insert(0, seq[0] if seq else current_snapshot)
    seq_array = np.array(seq, dtype=np.float32)  # [5, 9, 19]

    # Adjacency sequence [5, 9, 9]
    adj_seq = np.tile(adj_matrix[np.newaxis, :, :], (5, 1, 1)).astype(np.float32)

    node_tensor = torch.tensor(seq_array, dtype=torch.float32).unsqueeze(0)  # [1, 5, 9, 19]
    adj_tensor = torch.tensor(adj_seq, dtype=torch.float32).unsqueeze(0)     # [1, 5, 9, 9]

    with torch.no_grad():
        logits = graph_model(node_tensor, adj_tensor)  # [1, 9]
        probs = torch.sigmoid(logits).squeeze(0).numpy()

    probability = float(probs[ch_idx])
    prediction = int(probability >= 0.5)
    return prediction, probability


def predict(
    features: FeatureInput,
    channel: str | None = None,
    model_type: str | None = None,
) -> PredictionResponse:
    """
    Run inference across candidate detectors:
    - 'graph_gru' (default or if available): Spatio-Temporal Dynamic Graph + GRU
    - 'logreg': Validated class-balanced Logistic Regression baseline
    - 'auto': Use Dynamic Graph + GRU if loaded, falling back to Logistic Regression
    """
    _, scaler, graph_model, _ = load_artifacts()

    # Active model selection: query param > env var > default ('graph_gru' if artifact available)
    if not model_type:
        model_type = os.getenv("ORBITGUARD_ACTIVE_MODEL", "graph_gru").lower()
    else:
        model_type = model_type.lower()

=======
    return joblib.load(MODEL_PATH), joblib.load(SCALER_PATH)


def predict(features: FeatureInput) -> PredictionResponse:
    model, scaler = load_artifacts()
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    values = pd.DataFrame(
        [[getattr(features, name) for name in FEATURE_NAMES]], columns=FEATURE_NAMES
    )
    scaled_values = scaler.transform(values)
<<<<<<< HEAD

    # Check for near-zero flatline dropout fault (Section VI-A of paper)
    # When a sensor flatlines to exact zero for >= 10 readings, variance collapses.
    if features.len >= 10 and features.std == 0.0 and abs(features.mean) < 1e-9:
        return PredictionResponse(
            prediction=1,
            probability=0.999,
            model_name="FlatlineDropoutDetector",
        )

    if model_type in ("graph_gru", "dynamic_graph") and graph_model is not None:
        try:
            pred, prob = predict_graph_gru(scaled_values, channel)
            return PredictionResponse(
                prediction=pred,
                probability=prob,
                model_name="DynamicGraph+GRU",
            )
        except Exception:
            logger.exception("Graph GRU inference failed, falling back to Logistic Regression")

    # Default / Baseline inference
    pred, prob = predict_logreg(scaled_values)
    return PredictionResponse(
        prediction=pred,
        probability=prob,
        model_name="LogisticRegression",
    )
=======
    probability = float(model.predict_proba(scaled_values)[0, 1])
    prediction = int(model.predict(scaled_values)[0])
    return PredictionResponse(prediction=prediction, probability=probability)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
