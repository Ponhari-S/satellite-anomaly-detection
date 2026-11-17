import sys
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
MAX_GAP = 0.01
FAULT_EVERY_N = 300


def test_channel_faults(channel: str, model_type: str = "auto") -> dict:
    reset_window(channel)

    total = 0
    injected_total = 0
    injected_correctly_flagged = 0
    fault_type_results = {"spike": [0, 0], "dropout": [0, 0], "drift": [0, 0]}  # [correct, total]

    historical_anomaly_total = 0
    historical_anomaly_correct = 0
    normal_total = 0
    normal_correct = 0

    for reading in replay_with_faults(RAW_PATH, channel, TOTAL_SECONDS, MAX_GAP, fault_every_n=FAULT_EVERY_N):
        features = features_from_telemetry(reading)
        result = predict(features, channel=channel, model_type=model_type)
        total += 1

        if reading["injected_fault"]:
            injected_total += 1
            correct = int(result.prediction == 1)
            injected_correctly_flagged += correct
            fault_type_results[reading["injected_fault"]][0] += correct
            fault_type_results[reading["injected_fault"]][1] += 1
        elif reading["anomaly"] == 1:
            historical_anomaly_total += 1
            historical_anomaly_correct += int(result.prediction == 1)
        else:
            normal_total += 1
            normal_correct += int(result.prediction == 0)

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
