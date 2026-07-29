import pandas as pd
import time
import threading

CHANNEL_TO_REPLAY = "CADC0873"
TOTAL_PLAYBACK_SECONDS = 60
MAX_GAP_SECONDS = 2.0
_raw_csv_cache = {}
_cache_lock = threading.Lock()


def _get_full_dataframe(csv_path: str) -> pd.DataFrame:
    if csv_path in _raw_csv_cache:
        return _raw_csv_cache[csv_path]

    with _cache_lock:
        if csv_path not in _raw_csv_cache:
            _raw_csv_cache[csv_path] = pd.read_csv(csv_path)
    return _raw_csv_cache[csv_path]


def load_channel_data(csv_path: str, channel: str) -> pd.DataFrame:
    df = _get_full_dataframe(csv_path)
    sub = df[df["channel"] == channel].copy()
    sub["timestamp"] = pd.to_datetime(sub["timestamp"])
    sub = sub.sort_values("timestamp").reset_index(drop=True)
    return sub


def compute_playback_delays(sub: pd.DataFrame, total_seconds: float, max_gap: float) -> list:

    real_gaps = sub["timestamp"].diff().dt.total_seconds().fillna(0)

    capped_gaps = real_gaps.clip(upper=real_gaps[real_gaps > 0].quantile(0.99) if (real_gaps > 0).any() else 1)

    total_capped = capped_gaps.sum()
    if total_capped == 0:
        
        return [total_seconds / len(sub)] * len(sub)

    scale_factor = total_seconds / total_capped
    scaled_delays = (capped_gaps * scale_factor).clip(upper=max_gap)

    return scaled_delays.tolist()


def replay_channel(csv_path: str, channel: str, total_seconds: float, max_gap: float):
    """
    Generator that yields one telemetry reading at a time, with a
    realistic (compressed) delay between readings — just like a live feed.

    Yields dicts like:
        {"channel": "CADC0873", "timestamp": ..., "value": ..., "anomaly": 0}
    """
    sub = load_channel_data(csv_path, channel)
    delays = compute_playback_delays(sub, total_seconds, max_gap)

    print(f"Replaying channel '{channel}' — {len(sub)} readings over ~{total_seconds}s\n")
    channels_arr = sub["channel"].to_numpy()
    timestamps_arr = sub["timestamp"].astype(str).to_numpy()
    values_arr = sub["value"].to_numpy()
    anomalies_arr = sub["anomaly"].to_numpy()

    for i in range(len(sub)):
        delay = delays[i]
        if delay > 0:
            time.sleep(delay)

        reading = {
            "channel": channels_arr[i],
            "timestamp": timestamps_arr[i],
            "value": values_arr[i],
            "anomaly": int(anomalies_arr[i]),
        }
        yield reading


if __name__ == "__main__":
    RAW_TELEMETRY_PATH = "../datasets/dataset.csv"  

    count = 0
    anomaly_count = 0

    for reading in replay_channel(RAW_TELEMETRY_PATH, CHANNEL_TO_REPLAY,
                                    TOTAL_PLAYBACK_SECONDS, MAX_GAP_SECONDS):
        flag = "ANOMALY" if reading["anomaly"] == 1 else "normal"
        print(f"[{reading['timestamp']}] {reading['channel']} = {reading['value']:.6e}  ({flag})")

        count += 1
        anomaly_count += reading["anomaly"]

    print(f"\nPlayback complete. Streamed {count} readings, {anomaly_count} flagged as anomalies.")