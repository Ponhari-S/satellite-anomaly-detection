import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("../datasets/segments.csv")

print("=" * 60)
print("BASIC INFO")
print("=" * 60)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist())

print("\n" + "=" * 60)
print("ANOMALY BALANCE (segment-level, this is what we predict)")
print("=" * 60)
print(df["anomaly"].value_counts())
print("\nAs percentage:")
print(df["anomaly"].value_counts(normalize=True) * 100)

print("\n" + "=" * 60)
print("ANOMALY RATE PER CHANNEL")
print("=" * 60)
channel_anomaly = df.groupby("channel")["anomaly"].agg(["count", "mean"])
channel_anomaly.columns = ["num_segments", "anomaly_rate"]
channel_anomaly = channel_anomaly.sort_values("anomaly_rate", ascending=False)
print(channel_anomaly)

print("\n" + "=" * 60)
print("TRAIN / TEST SPLIT")
print("=" * 60)
print(df["train"].value_counts())

print("\n" + "=" * 60)
print("FEATURE MEANS: NORMAL vs ANOMALY")
print("=" * 60)
feature_cols = ["mean", "var", "std", "kurtosis", "skew",
                 "n_peaks", "smooth10_n_peaks", "smooth20_n_peaks"]
comparison = df.groupby("anomaly")[feature_cols].mean().T
comparison.columns = ["normal (0)", "anomaly (1)"]
print(comparison)

print("\n" + "=" * 60)
print("CORRELATION WITH ANOMALY LABEL (sorted, strongest first)")
print("=" * 60)
numeric_cols = df.select_dtypes(include="number").columns.tolist()
numeric_cols.remove("anomaly")
correlations = df[numeric_cols + ["anomaly"]].corr()["anomaly"].drop("anomaly")
correlations = correlations.reindex(correlations.abs().sort_values(ascending=False).index)
print(correlations)

top_features = correlations.abs().sort_values(ascending=False).index[:4].tolist()
print(f"\nPlotting top 4 features by correlation: {top_features}")

fig, axes = plt.subplots(1, 4, figsize=(18, 5))
for ax, feat in zip(axes, top_features):
    df.boxplot(column=feat, by="anomaly", ax=ax)
    ax.set_title(feat)
    ax.set_xlabel("anomaly (0=normal, 1=anomaly)")

plt.suptitle("Feature distributions: Normal vs Anomaly segments")
plt.tight_layout()
plt.savefig("feature_comparison.png", dpi=150)
print("Saved plot as feature_comparison.png")
plt.show()