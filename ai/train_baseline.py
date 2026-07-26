import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

X_train = pd.read_csv("X_train.csv")
X_test = pd.read_csv("X_test.csv")
y_train = pd.read_csv("y_train.csv").squeeze()
y_test = pd.read_csv("y_test.csv").squeeze()

print("X_train:", X_train.shape, " X_test:", X_test.shape)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("\n" + "=" * 60)
print("MODEL 1: Logistic Regression")
print("=" * 60)

logreg = LogisticRegression(max_iter=1000, class_weight="balanced")
logreg.fit(X_train_scaled, y_train)

y_pred_lr = logreg.predict(X_test_scaled)

print("\nClassification report:")
print(classification_report(y_test, y_pred_lr, target_names=["normal", "anomaly"]))

print("Confusion matrix (rows=actual, cols=predicted):")
print(confusion_matrix(y_test, y_pred_lr))

coef_importance = pd.Series(logreg.coef_[0], index=X_train.columns)
coef_importance = coef_importance.reindex(coef_importance.abs().sort_values(ascending=False).index)
print("\nTop 5 features by importance (Logistic Regression coefficients):")
print(coef_importance.head(5))

print("\n" + "=" * 60)
print("MODEL 2: Isolation Forest (unsupervised)")
print("=" * 60)

contamination_rate = y_train.mean()
print(f"Using contamination rate: {contamination_rate:.4f}")

iso_forest = IsolationForest(contamination=contamination_rate, random_state=42)
iso_forest.fit(X_train_scaled)

raw_pred = iso_forest.predict(X_test_scaled)
y_pred_iso = np.where(raw_pred == -1, 1, 0)

print("\nClassification report:")
print(classification_report(y_test, y_pred_iso, target_names=["normal", "anomaly"]))

print("Confusion matrix (rows=actual, cols=predicted):")
print(confusion_matrix(y_test, y_pred_iso))

print("\n" + "=" * 60)
print("SUMMARY: Logistic Regression vs Isolation Forest")
print("=" * 60)

summary = pd.DataFrame({
    "Logistic Regression": [
        precision_score(y_test, y_pred_lr),
        recall_score(y_test, y_pred_lr),
        f1_score(y_test, y_pred_lr),
    ],
    "Isolation Forest": [
        precision_score(y_test, y_pred_iso),
        recall_score(y_test, y_pred_iso),
        f1_score(y_test, y_pred_iso),
    ]
}, index=["Precision", "Recall", "F1-score"])

print(summary.round(3))

import joblib
joblib.dump(logreg, "baseline_logreg.pkl")
joblib.dump(iso_forest, "baseline_isoforest.pkl")
joblib.dump(scaler, "feature_scaler.pkl")
print("\nSaved baseline_logreg.pkl, baseline_isoforest.pkl, feature_scaler.pkl")