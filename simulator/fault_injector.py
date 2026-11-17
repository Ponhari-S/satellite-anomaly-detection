import random
from replay import replay_channel, _get_full_dataframe

def inject_spike(reading: dict, baseline_std: float) -> dict:
    direction = random.choice([1, -1])
    reading = reading.copy()
    reading["value"] = reading["value"] + direction * baseline_std * 15
    reading["anomaly"] = 1
    reading["injected_fault"] = "spike"
    return reading


def inject_dropout(reading: dict) -> dict:
    reading = reading.copy()
    reading["value"] = 0.0
    reading["anomaly"] = 1
    reading["injected_fault"] = "dropout"
    return reading


def inject_drift(reading: dict, step_index: int, baseline_std: float) -> dict:
    reading = reading.copy()
    reading["value"] = reading["value"] + (step_index * baseline_std * 2)
    reading["anomaly"] = 1
    reading["injected_fault"] = "drift"
    return reading


def replay_with_faults(csv_path: str, channel: str, total_seconds: float, max_gap: float, fault_every_n: int = 500, fault_types=("spike", "dropout", "drift")):
    df = _get_full_dataframe(csv_path)
    channel_values = df[df["channel"] == channel]["value"]
    baseline_std = channel_values.std()

    drift_counter = 0
    fault_type_index = 0

    for i, reading in enumerate(replay_channel(csv_path, channel, total_seconds, max_gap)):
        reading["injected_fault"] = None  # default: no

        if i > 0 and i % fault_every_n == 0:
            fault_type = fault_types[fault_type_index % len(fault_types)]
            fault_type_index += 1

            if fault_type == "spike":
                reading = inject_spike(reading, baseline_std)
            elif fault_type == "dropout":
                reading = inject_dropout(reading)
            elif fault_type == "drift":
                drift_counter += 1
                reading = inject_drift(reading, drift_counter, baseline_std)

        yield reading


if __name__ == "__main__":
    RAW_TELEMETRY_PATH = "../datasets/dataset.csv"
    CHANNEL = "CADC0873"
    TOTAL_SECONDS = 60
    MAX_GAP = 2.0
    FAULT_EVERY_N = 500 

    count = 0
    injected_count = 0
    original_anomaly_count = 0

    for reading in replay_with_faults(RAW_TELEMETRY_PATH, CHANNEL, TOTAL_SECONDS, MAX_GAP, fault_every_n=FAULT_EVERY_N):
        count += 1

        if reading["injected_fault"]:
            injected_count += 1
            print(f"*** INJECTED FAULT ({reading['injected_fault']}) at reading #{count}: "
                  f"value={reading['value']:.6e} ***")
        else:
            original_anomaly_count += reading["anomaly"]

    print("\n" + "=" * 60)
    print("FAULT INJECTION SUMMARY")
    print("=" * 60)
    print(f"Total readings streamed: {count}")
    print(f"Synthetic faults injected: {injected_count}")
    print(f"Original (historical) anomalies passed through: {original_anomaly_count}")