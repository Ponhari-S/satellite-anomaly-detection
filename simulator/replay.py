import pandas as pd
import time

CHANNEL_TO_REPLAY = "CADC0873"
TOTAL_PLAYBACK_SECONDS = 60      
MAX_GAP_SECONDS = 2.0            


def load_channel_data(csv_path: str, channel: str) -> pd.DataFrame:
    """Load raw telemetry and return one channel, sorted by time."""
    df = pd.read_csv(csv_path)
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
    sub = load_channel_data(csv_path, channel)
    delays = compute_playback_delays(sub, total_seconds, max_gap)

    print(f"Replaying channel '{channel}' — {len(sub)} readings over ~{total_seconds}s\n")

    for i, row in sub.iterrows():
        delay = delays[i]
        if delay > 0:
            time.sleep(delay)

        reading = {
            "channel": row["channel"],
            "timestamp": str(row["timestamp"]),
            "value": row["value"],
            "anomaly": int(row["anomaly"]),
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