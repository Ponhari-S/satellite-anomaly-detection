import threading
import queue
import time

from replay import replay_channel 

RAW_TELEMETRY_PATH = "../datasets/dataset.csv"
CHANNELS_TO_REPLAY = ["CADC0873", "CADC0872", "CADC0888", "CADC0892"]
TOTAL_PLAYBACK_SECONDS = 60
MAX_GAP_SECONDS = 2.0

reading_queue = queue.Queue()

active_threads = []


def channel_worker(channel: str):
    """Runs in its own thread: streams one channel's readings into the shared queue."""
    for reading in replay_channel(RAW_TELEMETRY_PATH, channel, TOTAL_PLAYBACK_SECONDS, MAX_GAP_SECONDS):
        reading_queue.put(reading)
    reading_queue.put({"channel": channel, "_done": True})


def run_multi_channel_simulation():
    print(f"Starting simulation for {len(CHANNELS_TO_REPLAY)} channels: {CHANNELS_TO_REPLAY}\n")

    for ch in CHANNELS_TO_REPLAY:
        t = threading.Thread(target=channel_worker, args=(ch,), daemon=True)
        t.start()
        active_threads.append(t)

    finished_channels = set()
    total_count = 0
    total_anomalies = 0
    per_channel_counts = {ch: 0 for ch in CHANNELS_TO_REPLAY}

    while len(finished_channels) < len(CHANNELS_TO_REPLAY):
        reading = reading_queue.get()

        if reading.get("_done"):
            finished_channels.add(reading["channel"])
            print(f"--- {reading['channel']} finished streaming ---")
            continue

        flag = "ANOMALY" if reading["anomaly"] == 1 else "normal"
        print(f"[{reading['timestamp']}] {reading['channel']:10s} = {reading['value']:.6e}  ({flag})")

        total_count += 1
        total_anomalies += reading["anomaly"]
        per_channel_counts[reading["channel"]] += 1

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Total readings streamed: {total_count}")
    print(f"Total anomalies flagged: {total_anomalies}")
    print("\nReadings per channel:")
    for ch, cnt in per_channel_counts.items():
        print(f"  {ch}: {cnt}")


if __name__ == "__main__":
    run_multi_channel_simulation()