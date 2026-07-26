import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../datasets/dataset.csv")

print("=" * 60)
print("BASIC INFO")
print("=" * 60)
print("Shape:", df.shape)
print("\nColumns:", df.columns.tolist())
print("\nData types:\n", df.dtypes)

print("\n" + "=" * 60)
print("MISSING VALUES")
print("=" * 60)
print(df.isnull().sum())

print("\n" + "=" * 60)
print("CHANNELS")
print("=" * 60)
print("Number of unique channels:", df["channel"].nunique())
print("\nRows per channel (top 10):")
print(df["channel"].value_counts().head(10))

print("\n" + "=" * 60)
print("ANOMALY LABEL BALANCE (row-level)")
print("=" * 60)
print(df["anomaly"].value_counts())
print("\nAs percentage:")
print(df["anomaly"].value_counts(normalize=True) * 100)

print("\n" + "=" * 60)
print("TRAIN / TEST SPLIT")
print("=" * 60)
print(df["train"].value_counts())

print("\n" + "=" * 60)
print("SEGMENTS")
print("=" * 60)
print("Number of unique segments:", df["segment"].nunique())

top_channel = df["channel"].value_counts().index[0]
print(f"\nPlotting channel: {top_channel}")

sub = df[df["channel"] == top_channel].copy()
sub["timestamp"] = pd.to_datetime(sub["timestamp"])
sub = sub.sort_values("timestamp")

plt.figure(figsize=(14, 5))
plt.plot(sub["timestamp"], sub["value"], color="steelblue", linewidth=0.8, label="value")

anomaly_points = sub[sub["anomaly"] == 1]
plt.scatter(anomaly_points["timestamp"], anomaly_points["value"],
            color="red", s=10, label="anomaly", zorder=5)

plt.title(f"Telemetry — Channel: {top_channel}")
plt.xlabel("Timestamp")
plt.ylabel("Value")
plt.legend()
plt.tight_layout()
plt.savefig("channel_plot.png", dpi=150)
print("Saved plot as channel_plot.png")
plt.show()