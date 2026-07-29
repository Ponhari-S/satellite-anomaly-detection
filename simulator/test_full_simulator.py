import threading
import queue
import time

from fault_injector import replay_with_faults

RAW_TELEMETRY_PATH = "../datasets/dataset.csv"

CHANNELS_TO_REPLAY = [
    "CADC0873",
    "CADC0872",
    "CADC0888",
]

TOTAL_PLAYBACK_SECONDS = 30
MAX_GAP_SECONDS = 1.0

FAULT_EVERY_N = 3000

reading_queue = queue.Queue()

def channel_worker(channel: str):
    """
    Replays one telemetry channel with synthetic faults and
    pushes each reading into the shared queue.
    """

    start = time.time()

    for reading in replay_with_faults(
        RAW_TELEMETRY_PATH,
        channel,
        TOTAL_PLAYBACK_SECONDS,
        MAX_GAP_SECONDS,
        fault_every_n=FAULT_EVERY_N,
    ):
        reading_queue.put(reading)

    elapsed = time.time() - start

    print(f"{channel} finished in {elapsed:.2f}s")

    reading_queue.put(
        {
            "channel": channel,
            "_done": True,
        }
    )

def run_integration_test():

    print("=" * 60)
    print("SIMULATOR INTEGRATION TEST")
    print("=" * 60)

    print(f"Dataset              : {RAW_TELEMETRY_PATH}")
    print(f"Channels             : {CHANNELS_TO_REPLAY}")
    print(f"Playback Time        : {TOTAL_PLAYBACK_SECONDS}s")
    print(f"Fault Interval       : Every {FAULT_EVERY_N} readings")

    print("=" * 60)
    print()

    start_time = time.time()

    threads = []

    for channel in CHANNELS_TO_REPLAY:

        thread = threading.Thread(
            target=channel_worker,
            args=(channel,),
            daemon=True,
        )

        thread.start()
        threads.append(thread)

    finished_channels = set()

    total_readings = 0
    total_historical_anomalies = 0
    total_injected_faults = 0

    per_channel_counts = {
        ch: 0
        for ch in CHANNELS_TO_REPLAY
    }

    per_channel_injected = {
        ch: 0
        for ch in CHANNELS_TO_REPLAY
    }

    fault_type_counts = {
        "spike": 0,
        "dropout": 0,
        "drift": 0,
    }

    # ------------------------------------------------------
    # Read streamed telemetry from all worker threads
    # ------------------------------------------------------

    while len(finished_channels) < len(CHANNELS_TO_REPLAY):

        reading = reading_queue.get()

        if reading.get("_done"):

            finished_channels.add(reading["channel"])

            print(f"--- {reading['channel']} finished ---")

            continue

        total_readings += 1
        per_channel_counts[reading["channel"]] += 1

        if reading["injected_fault"] is not None:

            total_injected_faults += 1

            per_channel_injected[
                reading["channel"]
            ] += 1

            fault_type_counts[
                reading["injected_fault"]
            ] += 1

        else:

            total_historical_anomalies += reading["anomaly"]

    for thread in threads:
        thread.join()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("INTEGRATION TEST RESULTS")
    print("=" * 60)

    print(f"Wall-clock time taken      : {elapsed:.2f}s")
    print(f"Target playback time       : ~{TOTAL_PLAYBACK_SECONDS}s")
    print(f"Total readings streamed    : {total_readings}")
    print(f"Historical anomalies       : {total_historical_anomalies}")
    print(f"Synthetic faults injected  : {total_injected_faults}")

    print("\nFault Breakdown")
    print("-" * 60)
    print(f"Spikes   : {fault_type_counts['spike']}")
    print(f"Dropouts : {fault_type_counts['dropout']}")
    print(f"Drifts   : {fault_type_counts['drift']}")

    print("\nPer-Channel Statistics")
    print("-" * 60)

    for channel in CHANNELS_TO_REPLAY:

        print(
            f"{channel:<10}"
            f" Readings: {per_channel_counts[channel]:>6}"
            f" | Injected Faults: {per_channel_injected[channel]}"
        )

    print("\n" + "=" * 60)
    print("CHECKLIST")
    print("=" * 60)

    checks_passed = 0
    total_checks = 4

    if all(cnt > 0 for cnt in per_channel_counts.values()):
        print("[PASS] All channels streamed data")
        checks_passed += 1
    else:
        print("[FAIL] One or more channels streamed zero readings")

    if total_injected_faults > 0:
        print("[PASS] Fault injection executed successfully")
        checks_passed += 1
    else:
        print("[FAIL] No synthetic faults were injected")

    if all(cnt > 0 for cnt in fault_type_counts.values()):
        print("[PASS] Spike, Dropout and Drift all occurred")
        checks_passed += 1
    else:
        print("[FAIL] One or more fault types never occurred")

    expected_ok = True

    for channel in CHANNELS_TO_REPLAY:

        expected = per_channel_counts[channel] // FAULT_EVERY_N
        actual = per_channel_injected[channel]

        if actual != expected:

            expected_ok = False

            print(
                f"[WARN] {channel}: "
                f"expected approximately {expected} injected faults, "
                f"observed {actual}"
            )

    if expected_ok:
        print("[PASS] Per-channel fault counts are correct")
        checks_passed += 1

    print("\n" + "=" * 60)
    print(f"FINAL SCORE : {checks_passed}/{total_checks}")
    print("=" * 60)

    print(
        f"\nPlayback completed in {elapsed:.2f} seconds "
        f"while streaming {total_readings:,} telemetry readings."
    )

    if checks_passed == total_checks:

        print(
            "\nSimulator module validation completed successfully."
        )

        print(
            "The simulator is ready for Phase 4 "
            "(Backend Integration)."
        )

    else:

        print(
            "\nReview the warnings/failures above "
            "before proceeding to Phase 4."
        )

if __name__ == "__main__":
    run_integration_test()