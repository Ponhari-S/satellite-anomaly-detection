import sys
<<<<<<< HEAD
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "simulator"))
sys.path.insert(0, str(ROOT_DIR))

from fault_injector import replay_with_faults
from backend.feature_extractor import features_from_telemetry, reset_window
from backend.model_service import predict, CHANNELS

RAW_PATH = str(ROOT_DIR / "datasets" / "dataset.csv")
TOTAL_SECONDS = 0      # 0 = instantaneous benchmark mode (no thread sleep delay)
=======
sys.path.insert(0, "simulator")
sys.path.insert(0, ".")

from fault_injector import replay_with_faults
from backend.feature_extractor import features_from_telemetry, reset_window
from backend.model_service import predict

CHANNEL = "CADC0873"
RAW_PATH = "datasets/dataset.csv"
TOTAL_SECONDS = 5      # compressed playback, we don't need real-time waiting for this test
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
MAX_GAP = 0.01
FAULT_EVERY_N = 300


<<<<<<< HEAD
def test_channel_faults(channel: str, model_type: str = "auto") -> dict:
    reset_window(channel)
=======
def main():
    reset_window(CHANNEL)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94

    total = 0
    injected_total = 0
    injected_correctly_flagged = 0
    fault_type_results = {"spike": [0, 0], "dropout": [0, 0], "drift": [0, 0]}  # [correct, total]

    historical_anomaly_total = 0
    historical_anomaly_correct = 0
    normal_total = 0
    normal_correct = 0

<<<<<<< HEAD
    for reading in replay_with_faults(RAW_PATH, channel, TOTAL_SECONDS, MAX_GAP, fault_every_n=FAULT_EVERY_N):
        features = features_from_telemetry(reading)
        result = predict(features, channel=channel, model_type=model_type)
=======
    print(f"Streaming channel {CHANNEL} with injected faults through the REAL production pipeline...\n")

    for reading in replay_with_faults(RAW_PATH, CHANNEL, TOTAL_SECONDS, MAX_GAP, fault_every_n=FAULT_EVERY_N):
        features = features_from_telemetry(reading)
        result = predict(features)
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
        total += 1

        if reading["injected_fault"]:
            injected_total += 1
<<<<<<< HEAD
            correct = int(result.prediction == 1)
=======
            correct = int(result.prediction == 1)  # a fault was injected, so correct = flagged as anomaly
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
            injected_correctly_flagged += correct
            fault_type_results[reading["injected_fault"]][0] += correct
            fault_type_results[reading["injected_fault"]][1] += 1
        elif reading["anomaly"] == 1:
            historical_anomaly_total += 1
            historical_anomaly_correct += int(result.prediction == 1)
        else:
            normal_total += 1
            normal_correct += int(result.prediction == 0)

<<<<<<< HEAD
    return {
        "channel": channel,
        "total": total,
        "injected_total": injected_total,
        "injected_correctly_flagged": injected_correctly_flagged,
        "detection_rate": (injected_correctly_flagged / injected_total) if injected_total > 0 else 0.0,
        "by_fault": {k: (v[0] / v[1]) if v[1] > 0 else 0.0 for k, v in fault_type_results.items()},
        "counts_by_fault": fault_type_results,
        "historical_anomaly_rate": (historical_anomaly_correct / historical_anomaly_total) if historical_anomaly_total > 0 else 0.0,
        "normal_accuracy": (normal_correct / normal_total) if normal_total > 0 else 0.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Multi-channel fault injection test")
    parser.add_argument("--channel", type=str, default="CADC0873", help="Channel to test, or 'ALL' for full constellation")
    parser.add_argument("--model", type=str, default="auto", help="Model to evaluate (auto, graph_gru, logreg)")
    args = parser.parse_args()

    channels_to_test = CHANNELS if args.channel.upper() == "ALL" else [args.channel]

    print("=" * 70)
    print(f"ORBITGUARD FAULT INJECTION BENCHMARK (Model: {args.model})")
    print("=" * 70)

    all_results = []
    for ch in channels_to_test:
        print(f"Testing channel: {ch}...")
        res = test_channel_faults(ch, model_type=args.model)
        all_results.append(res)

    print("\n" + "=" * 70)
    print(f"{'Channel':<10} | {'Spikes':<8} | {'Drifts':<8} | {'Dropouts':<8} | {'Overall Injected Detection'}")
    print("-" * 70)
    for r in all_results:
        bf = r["by_fault"]
        print(f"{r['channel']:<10} | {bf['spike']*100:>6.1f}% | {bf['drift']*100:>6.1f}% | {bf['dropout']*100:>6.1f}%  | {r['detection_rate']*100:>6.1f}% ({r['injected_correctly_flagged']}/{r['injected_total']})")
    print("=" * 70)


if __name__ == "__main__":
    main()
=======
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
>>>>>>> e361549f8885c4846fb32beefbc37ed519dadc94
