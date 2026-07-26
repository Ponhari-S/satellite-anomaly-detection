import pandas as pd
import numpy as np

df = pd.read_csv("../datasets/segments.csv")
print("Loaded shape:", df.shape)

drop_cols = ["segment", "anomaly", "train", "channel"]
feature_cols = [c for c in df.columns if c not in drop_cols]

print(f"\nUsing {len(feature_cols)} features:")
print(feature_cols)

train_df = df[df["train"] == 1]
test_df = df[df["train"] == 0]

print(f"\nTrain rows: {len(train_df)}")
print(f"Test rows:  {len(test_df)}")

X_train = train_df[feature_cols]
y_train = train_df["anomaly"]

X_test = test_df[feature_cols]
y_test = test_df["anomaly"]

print("\nTrain anomaly rate:", y_train.mean().round(4))
print("Test anomaly rate: ", y_test.mean().round(4))

print("\nNaN check (train):")
print(X_train.isnull().sum()[X_train.isnull().sum() > 0])

print("\nInfinite value check (train):")
inf_counts = np.isinf(X_train.select_dtypes(include=[np.number])).sum()
print(inf_counts[inf_counts > 0])

X_train.to_csv("X_train.csv", index=False)
X_test.to_csv("X_test.csv", index=False)
y_train.to_csv("y_train.csv", index=False)
y_test.to_csv("y_test.csv", index=False)

print("\nSaved X_train.csv, X_test.csv, y_train.csv, y_test.csv")