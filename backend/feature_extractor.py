from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
from backend.schemas import FeatureInput


<<<<<<< HEAD
class _AutonomousSegmentBuffer:
    """
    Autonomous streaming buffer for a single telemetry channel.
    
    Supports:
    1. Autonomous time-gap boundary detection (e.g., orbital downlink gap > 30s)
    2. Bounded sliding FIFO window (max 120 samples) to prevent historical dilution on unsegmented feeds
    3. Backward-compatibility with labeled historical segment IDs when available
    """
    __slots__ = ("segment_id", "timestamps", "values", "max_window_size", "gap_threshold_seconds")

    def __init__(self, max_window_size: int = 120, gap_threshold_seconds: float = 30.0):
        self.segment_id = None
        self.timestamps = []
        self.values = []
        self.max_window_size = max_window_size
        self.gap_threshold_seconds = gap_threshold_seconds

    def reset(self, segment_id=None):
=======
class _SegmentBuffer:
    """Holds the readings seen so far for one channel's CURRENT segment."""
    __slots__ = ("segment_id", "timestamps", "values")

    def __init__(self):
        self.segment_id = None
        self.timestamps = []
        self.values = []

    def reset(self, segment_id):
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
        self.segment_id = segment_id
        self.timestamps = []
        self.values = []

<<<<<<< HEAD
    def append(self, timestamp: pd.Timestamp, value: float, segment_id: int | None = None):
        # 1. Historical explicit segment change (if segment_id is present and known)
        if segment_id is not None and self.segment_id is not None and segment_id != self.segment_id:
            self.reset(segment_id)
        elif self.segment_id is None and segment_id is not None:
            self.segment_id = segment_id

        # 2. Autonomous time-gap change-point detection (satellite pass/downlink gap)
        if self.timestamps:
            delta_sec = (timestamp - self.timestamps[-1]).total_seconds()
            if delta_sec > self.gap_threshold_seconds:
                self.reset(segment_id)

        # 3. Append latest reading
        self.timestamps.append(timestamp)
        self.values.append(value)

        # 4. Autonomous bounded FIFO sliding window (prevents dilution on continuous unsegmented streams)
        if len(self.values) > self.max_window_size:
            self.timestamps.pop(0)
            self.values.pop(0)


_channel_buffers: dict[str, _AutonomousSegmentBuffer] = defaultdict(_AutonomousSegmentBuffer)
=======
    def append(self, timestamp, value):
        self.timestamps.append(timestamp)
        self.values.append(value)

_channel_buffers: dict[str, _SegmentBuffer] = defaultdict(_SegmentBuffer)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94


def _count_peaks(values: np.ndarray) -> int:
    """
    Count peaks using scipy find_peaks with a prominence threshold of
<<<<<<< HEAD
    0.5x the array's own standard deviation, matching paper Section III-B.
=======
    0.5x the array's own standard deviation.

    Why: a naive "any point higher than both neighbors" definition counts
    every tiny noise wiggle as a peak (verified: gave 19 peaks on a real
    segment where the training data says 1). Comparing against segments.csv
    across 8 test segments, a prominence threshold of 0.5*std reproduces
    n_peaks exactly in all 8 cases and is closely aligned on the
    diff/diff2/smoothed peak counts too. This will not be byte-identical
    to the original (unknown) feature engineering in every case, but it
    is a validated, order-of-magnitude-correct approximation, a major
    improvement over the previous no-threshold version.
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    """
    if len(values) < 3:
        return 0
    std = float(np.std(values))
    if std == 0:
        return 0
    peaks, _ = find_peaks(values, prominence=0.5 * std)
    return len(peaks)


def _smooth(values: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average smoothing, matching pandas rolling mean."""
    if len(values) < window:
        return values
    return pd.Series(values).rolling(window=window, min_periods=1).mean().to_numpy()


def reset_window(channel: str) -> None:
<<<<<<< HEAD
    """Clear the buffered segment for a channel."""
=======
    """Clear the buffered segment for a channel (useful between test runs)."""
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    _channel_buffers.pop(channel, None)


def features_from_telemetry(reading: dict) -> FeatureInput:
    """
<<<<<<< HEAD
    Extract the 19 statistical and signal processing features from the
    autonomous per-channel streaming buffer.
    
    Works with both historical pre-segmented data and continuous unsegmented live telemetry.
=======
    Append this reading to its channel's current segment buffer (starting
    a fresh buffer if the segment ID just changed), then compute real
    segment-style features from everything buffered so far in that segment.
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
    """
    channel = str(reading["channel"])
    timestamp = pd.to_datetime(reading["timestamp"])
    value = float(reading["value"])
<<<<<<< HEAD
    segment_id = reading.get("segment")
    if segment_id is not None:
        try:
            segment_id = int(segment_id)
        except (ValueError, TypeError):
            segment_id = None

    buffer = _channel_buffers[channel]
    buffer.append(timestamp, value, segment_id=segment_id)
=======
    segment_id = int(reading.get("segment", 0))

    buffer = _channel_buffers[channel]

    if buffer.segment_id != segment_id:
        buffer.reset(segment_id)

    buffer.append(timestamp, value)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94

    timestamps = buffer.timestamps
    values = np.array(buffer.values, dtype=float)
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
<<<<<<< HEAD
    )
=======
    )
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
