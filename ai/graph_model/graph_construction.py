import pandas as pd
import numpy as np

CHANNELS = ["CADC0872", "CADC0873", "CADC0874", "CADC0884", "CADC0886",
            "CADC0888", "CADC0890", "CADC0892", "CADC0894"]


def _count_peaks(values: np.ndarray) -> int:
    """Same validated peak-counting logic as backend/feature_extractor.py."""
    from scipy.signal import find_peaks
    if len(values) < 3:
        return 0
    std = float(np.std(values))
    if std == 0:
        return 0
    peaks, _ = find_peaks(values, prominence=0.5 * std)
    return len(peaks)


def compute_channel_features(sub: pd.DataFrame) -> np.ndarray:
    """Compute the 19 baseline-style features for one channel's readings
    within a single time window. Returns a fixed-length feature vector."""
    values = sub["value"].to_numpy()
    n = len(values)
    if n == 0:
        return np.zeros(19)

    mean = float(np.mean(values))
    var = float(np.var(values))
    std = float(np.std(values))

    if std > 0 and n > 1:
        normalized = (values - mean) / std
        skew = float(np.mean(normalized ** 3))
        kurtosis = float(np.mean(normalized ** 4) - 3)
    else:
        skew, kurtosis = 0.0, 0.0

    n_peaks = _count_peaks(values)
    smooth10 = pd.Series(values).rolling(10, min_periods=1).mean().to_numpy()
    smooth20 = pd.Series(values).rolling(20, min_periods=1).mean().to_numpy()
    smooth10_n_peaks = _count_peaks(smooth10)
    smooth20_n_peaks = _count_peaks(smooth20)

    diff = np.diff(values) if n > 1 else np.array([0.0])
    diff2 = np.diff(diff) if len(diff) > 1 else np.array([0.0])
    diff_peaks = _count_peaks(diff)
    diff2_peaks = _count_peaks(diff2)
    diff_var = float(np.var(diff))
    diff2_var = float(np.var(diff2))

    duration = max((sub["timestamp"].iloc[-1] - sub["timestamp"].iloc[0]).total_seconds(), 1e-6) if n > 1 else 1.0
    sampling = int(sub["sampling"].iloc[0]) if "sampling" in sub.columns else 1
    len_weighted = n * sampling
    var_div_duration = var / duration if duration > 0 else 0.0
    var_div_len = var / n if n > 0 else 0.0

    if n > 1:
        gaps = sub["timestamp"].diff().dt.total_seconds().dropna().to_numpy()
        gaps_squared = int(np.sum(gaps ** 2))
    else:
        gaps_squared = 0

    return np.array([
        sampling, duration, n, mean, var, std, kurtosis, skew, n_peaks,
        smooth10_n_peaks, smooth20_n_peaks, diff_peaks, diff2_peaks,
        diff_var, diff2_var, gaps_squared, len_weighted,
        var_div_duration, var_div_len,
    ], dtype=np.float32)


def build_graph_snapshots(raw_df: pd.DataFrame, window: str = "1D"):
    """
    Bin the raw telemetry into fixed time windows across ALL channels,
    and build one graph snapshot per window.

    Returns a list of dicts: {"node_features": [9,19], "adjacency": [9,9],
    "labels": [9], "window_start": timestamp}
    """
    raw_df = raw_df.copy()
    raw_df["timestamp"] = pd.to_datetime(raw_df["timestamp"])
    raw_df["window"] = raw_df["timestamp"].dt.floor(window)

    snapshots = []
    for window_start, window_df in raw_df.groupby("window"):
        node_features = np.zeros((len(CHANNELS), 19), dtype=np.float32)
        labels = np.zeros(len(CHANNELS), dtype=np.float32)
        channel_values = {}

        for i, ch in enumerate(CHANNELS):
            ch_sub = window_df[window_df["channel"] == ch].sort_values("timestamp")
            if len(ch_sub) == 0:
                continue
            node_features[i] = compute_channel_features(ch_sub)
            labels[i] = ch_sub["anomaly"].max()
            channel_values[i] = ch_sub["value"].to_numpy()

        adjacency = np.zeros((len(CHANNELS), len(CHANNELS)), dtype=np.float32)
        active = list(channel_values.keys())
        for a in active:
            for b in active:
                if a == b:
                    adjacency[a, b] = 1.0
                    continue
                va, vb = channel_values[a], channel_values[b]
                n = min(len(va), len(vb))
                if n >= 3:
                    corr = np.corrcoef(va[:n], vb[:n])[0, 1]
                    adjacency[a, b] = 0.0 if np.isnan(corr) else abs(corr)

        snapshots.append({
            "window_start": window_start,
            "node_features": node_features,
            "adjacency": adjacency,
            "labels": labels,
            "active_channels": active,
        })

    return snapshots