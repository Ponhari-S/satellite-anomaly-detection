import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, f1_score

df = pd.read_csv("datasets/segments.csv")
print(f"Loaded {len(df)} segments, {df.shape[1]} columns")

non_feature_cols = ["segment", "anomaly", "train", "channel"]
feature_cols = [c for c in df.columns if c not in non_feature_cols]
print(f"Using {len(feature_cols)} features: {feature_cols}")

X = df[feature_cols]
y = df["anomaly"]

X_train = X[df["train"] == 1]
y_train = y[df["train"] == 1]
X_test = X[df["train"] == 0]
y_test = y[df["train"] == 0]
print(f"Train: {len(X_train)} segments | Test: {len(X_test)} segments")

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

model = LogisticRegression(max_iter=1000, class_weight="balanced")
model.fit(X_train_scaled, y_train)

y_pred = model.predict(X_test_scaled)

print("\n" + "=" * 60)
print("INDEPENDENT REPLICATION RESULT")
print("=" * 60)
print(classification_report(y_test, y_pred, target_names=["normal", "anomaly"]))

f1 = f1_score(y_test, y_pred)
print(f"F1 score: {f1:.3f}")
print("\nExpected (from Day 5, original run): F1 = 0.848")
print("If this matches closely, the baseline is independently confirmed.")