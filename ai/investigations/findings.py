import sys
sys.path.insert(0, ".")
import pandas as pd
from backend.model_service import predict
from backend.feature_extractor import features_from_telemetry, reset_window


def evaluate_segment_progression(channel, segment_id, raw_df):
    sub = raw_df[(raw_df["channel"] == channel) & (raw_df["segment"] == segment_id)].copy()
    sub["timestamp"] = pd.to_datetime(sub["timestamp"])
    sub = sub.sort_values("timestamp").reset_index(drop=True)
    true_label = int(sub["anomaly"].iloc[0])
    reset_window(channel)
    records = []
    for i, row in sub.iterrows():
        reading = {"channel": row["channel"], "timestamp": str(row["timestamp"]),
                   "value": row["value"], "anomaly": int(row["anomaly"]),
                   "segment": int(row["segment"]), "sampling": int(row["sampling"])}
        result = predict(features_from_telemetry(reading))
        records.append({"fraction_complete": (i + 1) / len(sub), "correct": int(result.prediction == true_label)})
    return pd.DataFrame(records)


def main():
    raw_df = pd.read_csv("datasets/dataset.csv")
    seg_counts = raw_df.groupby(["channel", "segment"]).size().reset_index(name="n")
    seg_counts = seg_counts[seg_counts["n"] >= 15]

    all_results = []
    for ch in seg_counts["channel"].unique():
        sample = seg_counts[seg_counts["channel"] == ch].sample(min(4, len(seg_counts[seg_counts["channel"] == ch])), random_state=1)
        for _, row in sample.iterrows():
            df = evaluate_segment_progression(row["channel"], row["segment"], raw_df)
            df["channel"] = row["channel"]
            all_results.append(df)

    combined = pd.concat(all_results, ignore_index=True)
    combined["bucket"] = pd.cut(combined["fraction_complete"], bins=[0, 0.5, 1.0], labels=["first_half", "second_half"])

    print("ACCURACY BY CHANNEL (first half vs second half of segment):")
    print(combined.groupby(["channel", "bucket"], observed=False)["correct"].mean().unstack().round(3))


if __name__ == "__main__":
    main()