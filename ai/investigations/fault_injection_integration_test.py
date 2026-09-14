import sys
sys.path.insert(0, "simulator")
sys.path.insert(0, ".")

from fault_injector import replay_with_faults
from backend.feature_extractor import features_from_telemetry, reset_window
from backend.model_service import predict

CHANNEL = "CADC0873"
RAW_PATH = "datasets/dataset.csv"
TOTAL_SECONDS = 5      # compressed playback, we don't need real-time waiting for this test
MAX_GAP = 0.01
FAULT_EVERY_N = 300


def main():
    reset_window(CHANNEL)

    total = 0
    injected_total = 0
    injected_correctly_flagged = 0
    fault_type_results = {"spike": [0, 0], "dropout": [0, 0], "drift": [0, 0]}  # [correct, total]

    historical_anomaly_total = 0
    historical_anomaly_correct = 0
    normal_total = 0
    normal_correct = 0

    print(f"Streaming channel {CHANNEL} with injected faults through the REAL production pipeline...\n")

    for reading in replay_with_faults(RAW_PATH, CHANNEL, TOTAL_SECONDS, MAX_GAP, fault_every_n=FAULT_EVERY_N):
        features = features_from_telemetry(reading)
        result = predict(features)
        total += 1

        if reading["injected_fault"]:
            injected_total += 1
            correct = int(result.prediction == 1)  # a fault was injected, so correct = flagged as anomaly
            injected_correctly_flagged += correct
            fault_type_results[reading["injected_fault"]][0] += correct
            fault_type_results[reading["injected_fault"]][1] += 1
        elif reading["anomaly"] == 1:
            historical_anomaly_total += 1
            historical_anomaly_correct += int(result.prediction == 1)
        else:
            normal_total += 1
            normal_correct += int(result.prediction == 0)

    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Total readings processed: {total}")

    print(f"\nSynthetic (injected) faults: {injected_total}")
    if injected_total > 0:
        print(f"  Correctly flagged as anomaly: {injected_correctly_flagged}/{injected_total} "
              f"({100*injected_correctly_flagged/injected_total:.1f}%)")
        print("  By fault type:")
        for fault_type, (correct, tot) in fault_type_results.items():
            if tot > 0:
                print(f"    {fault_type:8s}: {correct}/{tot} ({100*correct/tot:.1f}%)")

    print(f"\nHistorical (labeled) anomalies: {historical_anomaly_total}")
    if historical_anomaly_total > 0:
        print(f"  Correctly flagged: {historical_anomaly_correct}/{historical_anomaly_total} "
              f"({100*historical_anomaly_correct/historical_anomaly_total:.1f}%)")

    print(f"\nNormal (undisturbed) readings: {normal_total}")
    if normal_total > 0:
        print(f"  Correctly NOT flagged: {normal_correct}/{normal_total} "
              f"({100*normal_correct/normal_total:.1f}%)")

    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    if injected_total > 0 and injected_correctly_flagged / injected_total > 0.7:
        print("The system correctly detects synthetic anomalies it was never")
        print("trained on or shown historical labels for — this demonstrates")
        print("real generalization, not just memorization of known anomalies.")
    else:
        print("Detection rate on synthetic faults is low — needs investigation")
        print("before claiming genuine generalization in the final report.")


if __name__ == "__main__":
    main()