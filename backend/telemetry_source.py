"""Multi-channel telemetry source for live WebSocket streaming."""

import asyncio
<<<<<<< HEAD
import os
=======
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
from collections.abc import AsyncIterator
from pathlib import Path
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATASET_PATH = ROOT_DIR / "datasets" / "dataset.csv"

_cached_df = None


def _get_chronological_records() -> pd.DataFrame:
    global _cached_df
    if _cached_df is None:
        df = pd.read_csv(RAW_DATASET_PATH)
<<<<<<< HEAD
        # Timestamps in ISO format sort correctly as strings with near-zero latency
        df["timestamp_str"] = df["timestamp"].astype(str)
        df = df.sort_values("timestamp_str").reset_index(drop=True)
=======
        df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
        # Sort chronologically so all 9 channels interleave smoothly across the mission timeline
        df = df.sort_values("timestamp_dt").reset_index(drop=True)
        df["timestamp_str"] = df["timestamp_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
        _cached_df = df
    return _cached_df


async def multi_channel_telemetry_source(
<<<<<<< HEAD
    delay_between_frames: float | None = None,
) -> AsyncIterator[dict]:
    """
    Yield all 9 OPS-SAT channels chronologically in real-time.
    Supports adjustable streaming rate from real-time human speed (0.08s)
    to high-throughput benchmark speed (~4,000+ readings/s).
    """
    if delay_between_frames is None:
        env_delay = os.getenv("ORBITGUARD_STREAM_DELAY")
        delay_between_frames = float(env_delay) if env_delay else 0.08

    df = _get_chronological_records()
=======
    delay_between_frames: float = 0.08,
) -> AsyncIterator[dict]:
    """Yield all 9 OPS-SAT channels chronologically in real-time."""
    df = await asyncio.to_thread(_get_chronological_records)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94

    channels = df["channel"].to_numpy()
    timestamps = df["timestamp_str"].to_numpy()
    values = df["value"].to_numpy()
    anomalies = df["anomaly"].to_numpy()
    labels = df["label"].to_numpy()
    segments = df["segment"].to_numpy()
    samplings = df["sampling"].to_numpy()
    trains = df["train"].to_numpy()

    total = len(df)
    while True:
        for i in range(total):
            anomaly_val = int(anomalies[i])
            reading = {
                "channel": str(channels[i]),
                "timestamp": str(timestamps[i]),
                "value": float(values[i]),
                "label": str(labels[i]),
                "sampling": int(samplings[i]),
                "anomaly": anomaly_val,
                "segment": int(segments[i]),
                "train": int(trains[i]),
            }
            yield reading
<<<<<<< HEAD
            if delay_between_frames and delay_between_frames > 0:
                await asyncio.sleep(delay_between_frames)
=======
            await asyncio.sleep(delay_between_frames)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94


telemetry_source = multi_channel_telemetry_source
