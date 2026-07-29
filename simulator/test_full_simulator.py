import threading
import queue
import time

from fault_injector import replay_with_faults

RAW_TELEMETRY_PATH = "../datasets/dataset.csv"
CHANNELS_TO_REPLAY = ["CADC0873", "CADC0872", "CADC0888"]
TOTAL_PLAYBACK_SECONDS = 30
MAX_GAP_SECONDS = 1.0
FAULT_EVERY_N = 3000    

reading_queue = queue.Queue()


def channel_worker(channel: str):
    for reading in replay_with_faults(RAW_TELEMETRY_PATH, channel,
                                       TOTAL_PLAYBACK_SECONDS, MAX_GAP_SECONDS,
                                       fault_every_n=FAULT_EVERY_N):
        reading_queue.put(reading)
    reading_queue.put({"channel": channel, "_done": True})


def run_integration_test():
    print(f"Integration test: {len(CHANNELS_TO_REPLAY)} channels, "
          f"with fault injection, over ~{TOTAL_PLAYBACK_SECONDS}s\n")

    start_time = time.time()

    threads = []
    for ch in CHANNELS_TO_REPLAY:
        t = threading.Thread(target=channel_worker, args=(ch,), daemon=True)
        t.start()
        threads.append(t)

    finished_channels = set()

    total_readings = 0
    total_historical_anomalies = 0
    total_injected_faults = 0
    per_channel_counts = {ch: 0 for ch in CHANNELS_TO_REPLAY}
    fault_type_counts = {"spike": 0, "dropout": 0, "drift": 0}

    while len(finished_channels) < len(CHANNELS_TO_REPLAY):
        reading = reading_queue.get()

        if reading.get("_done"):
            finished_channels.add(reading["channel"])
            print(f"--- {reading['channel']} finished ---")
            continue

        total_readings += 1
        per_channel_counts[reading["channel"]] += 1

        if reading["injected_fault"]:
            total_injected_faults += 1
            fault_type_counts[reading["injected_fault"]] += 1
        else:
            total_historical_anomalies += reading["anomaly"]

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Wall-clock time taken:        {elapsed:.1f}s (target was ~{TOTAL_PLAYBACK_SECONDS}s)")
    print(f"Total readings streamed:      {total_readings}")
    print(f"Historical anomalies passed:  {total_historical_anomalies}")
    print(f"Synthetic faults injected:    {total_injected_faults}")
    print(f"  - spikes:   {fault_type_counts['spike']}")
    print(f"  - dropouts: {fault_type_counts['dropout']}")
    print(f"  - drifts:   {fault_type_counts['drift']}")
    print("\nReadings per channel:")
    for ch, cnt in per_channel_counts.items():
        print(f"  {ch}: {cnt}")

    print("\n" + "=" * 60)
    print("CHECKLIST")
    print("=" * 60)

    checks_passed = 0
    checks_total = 4

    if all(cnt > 0 for cnt in per_channel_counts.values()):
        print("[PASS] All channels streamed data")
        checks_passed += 1
    else:
        print("[FAIL] At least one channel produced zero readings")

    if total_injected_faults > 0:
        print("[PASS] Fault injection fired at least once")
        checks_passed += 1
    else:
        print("[FAIL] No faults were injected — check fault_every_n vs channel size")

    if elapsed <= TOTAL_PLAYBACK_SECONDS * 2:
        print("[PASS] Timing within acceptable range")
        checks_passed += 1
    else:
        print(f"[FAIL] Took {elapsed:.1f}s, expected ~{TOTAL_PLAYBACK_SECONDS}s")

    if all(cnt > 0 for cnt in fault_type_counts.values()):
        print("[PASS] All 3 fault types (spike/dropout/drift) fired at least once")
        checks_passed += 1
    else:
        print("[FAIL] Not all fault types fired — may need lower fault_every_n for smaller channels")

    print(f"\n{checks_passed}/{checks_total} checks passed.")

    if checks_passed == checks_total:
        print("\nSimulator module is ready for backend integration (Phase 4).")
    else:
        print("\nReview failed checks above before moving to the backend.")


if __name__ == "__main__":
    run_integration_test()