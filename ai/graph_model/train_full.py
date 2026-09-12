import sys
sys.path.insert(0, "ai/graph_model")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import f1_score, precision_score, recall_score

from graph_construction import build_graph_snapshots, CHANNELS
from model import DynamicGraphAnomalyDetector

SEQUENCE_LENGTH = 5
WINDOW = "1h"
EPOCHS = 100
LEARNING_RATE = 0.01


def build_sequences(snapshots, seq_len):
    sequences = []
    for i in range(len(snapshots) - seq_len + 1):
        window = snapshots[i:i + seq_len]
        node_features = np.array([s["node_features"] for s in window])
        adjacency = np.array([s["adjacency"] for s in window])
        labels = window[-1]["labels"]
        active_mask = np.zeros(len(CHANNELS), dtype=np.float32)
        for idx in window[-1]["active_channels"]:
            active_mask[idx] = 1.0
        sequences.append((node_features, adjacency, labels, active_mask))
    return sequences


def main():
    raw_df = pd.read_csv("datasets/dataset.csv")
    print(f"Building graph snapshots with {WINDOW} windows...")
    snapshots = build_graph_snapshots(raw_df, window=WINDOW)
    snapshots = [s for s in snapshots if len(s["active_channels"]) >= 2]
    snapshots = sorted(snapshots, key=lambda s: s["window_start"])
    print(f"Usable snapshots: {len(snapshots)}")

    split_idx = int(len(snapshots) * 0.8)
    train_snapshots = snapshots[:split_idx]
    test_snapshots = snapshots[split_idx:]

    train_sequences = build_sequences(train_snapshots, SEQUENCE_LENGTH)
    test_sequences = build_sequences(test_snapshots, SEQUENCE_LENGTH)
    print(f"Train sequences: {len(train_sequences)} | Test sequences: {len(test_sequences)}")

    if len(train_sequences) == 0 or len(test_sequences) == 0:
        print("Not enough data to train and evaluate. Stopping.")
        return

    model = DynamicGraphAnomalyDetector(num_nodes=len(CHANNELS), node_feature_dim=19, hidden_dim=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)

    # Class-imbalance correction, matching the baseline's class_weight="balanced".
    # Without this, BCEWithLogitsLoss can converge to just predicting the
    # majority class if the training set's anomaly rate is far from 50%.
    train_labels_flat = []
    for _, _, labels, active_mask in train_sequences:
        for i in range(len(CHANNELS)):
            if active_mask[i] > 0:
                train_labels_flat.append(labels[i])
    train_labels_flat = np.array(train_labels_flat)
    n_pos = train_labels_flat.sum()
    n_neg = len(train_labels_flat) - n_pos
    pos_weight = torch.tensor([n_neg / n_pos]) if n_pos > 0 else torch.tensor([1.0])
    print(f"Train anomaly rate: {train_labels_flat.mean():.3f} | pos_weight = {pos_weight.item():.3f}")

    loss_fn = nn.BCEWithLogitsLoss(reduction="none", pos_weight=pos_weight)

    print(f"\nTraining for {EPOCHS} epochs...")
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0.0
        for node_features, adjacency, labels, active_mask in train_sequences:
            nf = torch.tensor(node_features, dtype=torch.float32).unsqueeze(0)
            adj = torch.tensor(adjacency, dtype=torch.float32).unsqueeze(0)
            y = torch.tensor(labels, dtype=torch.float32).unsqueeze(0)
            mask = torch.tensor(active_mask, dtype=torch.float32).unsqueeze(0)

            optimizer.zero_grad()
            logits = model(nf, adj)
            per_node_loss = loss_fn(logits, y)
            # Only count loss for channels that actually had data in this window
            masked_loss = (per_node_loss * mask).sum() / mask.sum().clamp(min=1)
            masked_loss.backward()
            optimizer.step()
            total_loss += masked_loss.item()

        if epoch % 20 == 0 or epoch == EPOCHS - 1:
            print(f"  epoch {epoch:3d}: avg loss = {total_loss / len(train_sequences):.4f}")

    # ---------------------------------------------------------
    # Evaluate on held-out test sequences
    # ---------------------------------------------------------
    print("\nEvaluating on held-out test sequences...")
    model.eval()
    all_preds, all_true = [], []
    with torch.no_grad():
        for node_features, adjacency, labels, active_mask in test_sequences:
            nf = torch.tensor(node_features, dtype=torch.float32).unsqueeze(0)
            adj = torch.tensor(adjacency, dtype=torch.float32).unsqueeze(0)
            logits = model(nf, adj)
            probs = torch.sigmoid(logits).squeeze(0).numpy()
            preds = (probs >= 0.5).astype(int)

            for i in range(len(CHANNELS)):
                if active_mask[i] > 0:
                    all_preds.append(preds[i])
                    all_true.append(int(labels[i]))

    all_preds = np.array(all_preds)
    all_true = np.array(all_true)

    print(f"\nTotal test predictions (active channels only): {len(all_true)}")
    print(f"True anomaly rate in test set: {all_true.mean():.3f}")

    if all_true.sum() == 0:
        print("No positive (anomaly) examples in test set — cannot compute meaningful F1.")
        return

    f1 = f1_score(all_true, all_preds, zero_division=0)
    precision = precision_score(all_true, all_preds, zero_division=0)
    recall = recall_score(all_true, all_preds, zero_division=0)

    print("\n" + "=" * 60)
    print("DYNAMIC-GRAPH MODEL RESULTS")
    print("=" * 60)
    print(f"F1:        {f1:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"\nBaseline (Logistic Regression) for comparison: F1 = 0.848")

    if f1 > 0.848:
        print(f"\nGraph model OUTPERFORMS the baseline by {f1 - 0.848:.3f} F1.")
    else:
        print(f"\nGraph model does NOT yet outperform the baseline (behind by {0.848 - f1:.3f} F1).")
        print("This is a legitimate, honest result given the small training set")
        print(f"({len(train_sequences)} sequences) — worth reporting as-is, not concealed.")


if __name__ == "__main__":
    main()