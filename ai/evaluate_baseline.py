import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import f1_score, precision_score, recall_score
import joblib

df = pd.read_csv("../datasets/segments.csv")

drop_cols = ["segment", "anomaly", "train", "channel"]
feature_cols = [c for c in df.columns if c not in drop_cols]

X = df[feature_cols]
y = df["anomaly"]
channels = df["channel"]

print("=" * 60)
print("PART 1: 5-Fold Cross-Validation (Logistic Regression)")
print("=" * 60)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

fold_f1_scores = []
for fold_num, (train_idx, val_idx) in enumerate(skf.split(X, y), start=1):
    X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

    scaler = StandardScaler()
    X_tr_scaled = scaler.fit_transform(X_tr)
    X_val_scaled = scaler.transform(X_val)

    model = LogisticRegression(max_iter=1000, class_weight="balanced")
    model.fit(X_tr_scaled, y_tr)
    preds = model.predict(X_val_scaled)

    fold_f1 = f1_score(y_val, preds)
    fold_f1_scores.append(fold_f1)
    print(f"Fold {fold_num}: F1 = {fold_f1:.3f}  (val anomaly rate: {y_val.mean():.3f})")

print(f"\nMean F1 across 5 folds: {np.mean(fold_f1_scores):.3f}")
print(f"Std dev across folds:   {np.std(fold_f1_scores):.3f}")
print("(A small std dev means the 0.85 we saw on Day 5 is a stable, trustworthy number,")
print(" not a lucky split. A large std dev would mean we need more data or simpler features.)")

print("\n" + "=" * 60)
print("PART 2: Per-Channel Performance (using Day 5's saved model)")
print("=" * 60)

X_test = pd.read_csv("X_test.csv")
y_test = pd.read_csv("y_test.csv").squeeze()

test_df = df[df["train"] == 0].reset_index(drop=True)
test_channels = test_df["channel"]

model = joblib.load("baseline_logreg.pkl")
scaler = joblib.load("feature_scaler.pkl")

X_test_scaled = scaler.transform(X_test)
y_pred = model.predict(X_test_scaled)

results = pd.DataFrame({
    "channel": test_channels,
    "actual": y_test,
    "predicted": y_pred
})

print("\nPerformance per channel (channels with at least 5 test segments):")
rows = []
for ch, group in results.groupby("channel"):
    if len(group) < 5:
        continue
    n_anomalies = group["actual"].sum()
    if n_anomalies == 0:
        rows.append([ch, len(group), n_anomalies, "N/A (no anomalies)", "N/A", "N/A"])
        continue
    p = precision_score(group["actual"], group["predicted"], zero_division=0)
    r = recall_score(group["actual"], group["predicted"], zero_division=0)
    f1 = f1_score(group["actual"], group["predicted"], zero_division=0)
    rows.append([ch, len(group), n_anomalies, round(p, 2), round(r, 2), round(f1, 2)])

per_channel_df = pd.DataFrame(rows, columns=["channel", "n_segments", "n_anomalies", "precision", "recall", "f1"])
print(per_channel_df.to_string(index=False))