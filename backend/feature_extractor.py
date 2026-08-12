from collections import defaultdict, deque
import numpy as np
import pandas as pd

from backend.schemas import FeatureInput

# How many recent readings to keep per channel for feature computation.
# Larger = more stable features but slower to react to new anomalies.
WINDOW_SIZE = 50

# Per-channel rolling buffers of (timestamp, value) tuples.
_channel_windows: dict[str, deque] = defaultdict(lambda: deque(maxlen=WINDOW_SIZE))


def _count_peaks(values: np.ndarray) -> int:
    """Count local maxima: points strictly greater than both neighbors."""
    if len(values) < 3:
        return 0
    return int(np.sum((values[1:-1] > values[:-2]) & (values[1:-1] > values[2:])))


def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average smoothing, matching pandas rolling mean."""
    if len(values) < window:
        return values
    return pd.Series(values).rolling(window=window, min_periods=1).mean().to_numpy()


def reset_window(channel: str) -> None:
    """Clear the buffered window for a channel (useful between test runs)."""
    _channel_windows.pop(channel, None)


def features_from_telemetry(reading: dict) -> FeatureInput:
    """
    Update the rolling window for this reading's channel, then compute
    real segment-style features from the buffered window.
    """
    channel = str(reading["channel"])
    timestamp = pd.to_datetime(reading["timestamp"])
    value = float(reading["value"])

    window = _channel_windows[channel]
    window.append((timestamp, value))

    timestamps = [t for t, _ in window]
    values = np.array([v for _, v in window], dtype=float)
    n = len(values)

    sampling = int(reading.get("sampling", 1))
    duration = max((timestamps[-1] - timestamps[0]).total_seconds(), 1e-6) if n > 1 else 1.0
    length = n

    mean = float(np.mean(values))
    var = float(np.var(values))
    std = float(np.std(values))

    if std > 0 and n > 1:
        normalized = (values - mean) / std
        skew = float(np.mean(normalized ** 3))
        kurtosis = float(np.mean(normalized ** 4) - 3)
    else:
        skew = 0.0
        kurtosis = 0.0

    n_peaks = _count_peaks(values)
    smooth10 = _smooth(values, 10)
    smooth20 = _smooth(values, 20)
    smooth10_n_peaks = _count_peaks(smooth10)
    smooth20_n_peaks = _count_peaks(smooth20)

    diff = np.diff(values) if n > 1 else np.array([0.0])
    diff2 = np.diff(diff) if len(diff) > 1 else np.array([0.0])

    diff_peaks = _count_peaks(diff)
    diff2_peaks = _count_peaks(diff2)
    diff_var = float(np.var(diff))
    diff2_var = float(np.var(diff2))

    if n > 1:
        gaps = np.array([(timestamps[i] - timestamps[i - 1]).total_seconds()
                          for i in range(1, n)])
        gaps_squared = int(np.sum(gaps ** 2))
    else:
        gaps_squared = 0

    len_weighted = int(length * sampling)
    var_div_duration = var / duration if duration > 0 else 0.0
    var_div_len = var / length if length > 0 else 0.0

    return FeatureInput(
        sampling=sampling, duration=int(duration), len=length, mean=mean,
        var=var, std=std, kurtosis=kurtosis, skew=skew, n_peaks=n_peaks,
        smooth10_n_peaks=smooth10_n_peaks, smooth20_n_peaks=smooth20_n_peaks,
        diff_peaks=diff_peaks, diff2_peaks=diff2_peaks,
        diff_var=diff_var, diff2_var=diff2_var, gaps_squared=gaps_squared,
        len_weighted=len_weighted, var_div_duration=var_div_duration,
        var_div_len=var_div_len,
    )