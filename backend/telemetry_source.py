"""Swappable telemetry sources used by the stream endpoint.

Replace ``real_simulator_source`` with an adapter for a future simulator API;
the WebSocket route does not need to change.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_DATASET_PATH = ROOT_DIR / "datasets" / "dataset.csv"
DEFAULT_CHANNEL = "CADC0873"


def _normalise_simulator_reading(reading: dict) -> dict:
    """Adapt the current replay.py output to the raw-telemetry schema."""
    anomaly = int(reading["anomaly"])
    return {
        "channel": str(reading["channel"]),
        "timestamp": str(reading["timestamp"]),
        "value": float(reading["value"]),
        # replay.py currently omits these raw CSV columns, so preserve the
        # expected API contract with safe metadata defaults until it exposes them.
        "label": str(reading.get("label", "anomaly" if anomaly else "normal")),
        "sampling": int(reading.get("sampling", 1)),
        "anomaly": anomaly,
        "segment": int(reading.get("segment", 0)),
        "train": int(reading.get("train", 0)),
    }


async def real_simulator_source(
    channel: str = DEFAULT_CHANNEL,
    total_seconds: float = 60.0,
    max_gap: float = 2.0,
) -> AsyncIterator[dict]:
    """Yield the repository's working replay simulator output asynchronously."""
    from simulator.replay import replay_channel

    iterator = replay_channel(str(RAW_DATASET_PATH), channel, total_seconds, max_gap)
    sentinel = object()
    while True:
        reading = await asyncio.to_thread(next, iterator, sentinel)
        if reading is sentinel:
            return
        yield _normalise_simulator_reading(reading)


async def dummy_telemetry_source() -> AsyncIterator[dict]:
    """Fallback source retained for local development if the simulator is unavailable."""
    import random
    from datetime import datetime, timezone

    segment = 0
    while True:
        segment += 1
        anomaly = random.choice((0, 0, 0, 1))
        yield {
            "channel": "DUMMY001", "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": random.uniform(-0.001, 0.001), "label": "anomaly" if anomaly else "normal",
            "sampling": 1, "anomaly": anomaly, "segment": segment, "train": 0,
        }
        await asyncio.sleep(1)


# The replay simulator is available now. Switch this assignment to
# dummy_telemetry_source when developing without the repository dataset.
telemetry_source = real_simulator_source
