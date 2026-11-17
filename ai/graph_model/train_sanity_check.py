import sys
sys.path.insert(0, "ai/graph_model")

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

from graph_construction import build_graph_snapshots, CHANNELS
from model import DynamicGraphAnomalyDetector

SEQUENCE_LENGTH = 5 
WINDOW = "1h"


def build_sequences(snapshots, seq_len):
    """Turn a list of individual snapshots into overlapping sequences,
    each with a node_features tensor, adjacency tensor, and label tensor
    (label = anomaly status at the LAST snapshot in the sequence)."""
    sequences = []
    for i in range(len(snapshots) - seq_len + 1):
        window = snapshots[i:i + seq_len]
        node_features = np.array([s["node_features"] for s in window])
        adjacency = np.array([s["adjacency"] for s in window])
        labels = window[-1]["labels"]
        sequences.append((node_features, adjacency, labels))
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
    print(f"Train: {len(train_snapshots)} snapshots | Test: {len(test_snapshots)} snapshots")

    train_sequences = build_sequences(train_snapshots, SEQUENCE_LENGTH)
    test_sequences = build_sequences(test_snapshots, SEQUENCE_LENGTH)
    print(f"Train sequences: {len(train_sequences)} | Test sequences: {len(test_sequences)}")

    if len(train_sequences) == 0:
        print("\nNot enough snapshots to build even one training sequence.")
        print("This is a real finding: 1-hour windows help, but the dataset's")
        print("total time span may still be too short for this sequence length.")
        print("Next step: try SEQUENCE_LENGTH=3, or an even finer window (30min).")
        return

    model = DynamicGraphAnomalyDetector(num_nodes=len(CHANNELS), node_feature_dim=19, hidden_dim=32)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.BCEWithLogitsLoss()

    print("\nRunning 20 training steps as a sanity check (not full convergence)...")
    losses = []
    for step in range(20):
        total_loss = 0.0
        for node_features, adjacency, labels in train_sequences:
            nf = torch.tensor(node_features, dtype=torch.float32).unsqueeze(0)
            adj = torch.tensor(adjacency, dtype=torch.float32).unsqueeze(0)
            y = torch.tensor(labels, dtype=torch.float32).unsqueeze(0)

            optimizer.zero_grad()
            logits = model(nf, adj)
            loss = loss_fn(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_sequences)
        losses.append(avg_loss)
        if step % 5 == 0 or step == 19:
            print(f"  step {step:2d}: avg loss = {avg_loss:.4f}")

    print(f"\nLoss trend: {losses[0]:.4f} -> {losses[-1]:.4f}")
    if losses[-1] < losses[0]:
        print("Loss decreased — gradients are flowing correctly through the model.")
    else:
        print("Loss did NOT decrease — needs investigation before real training.")


if __name__ == "__main__":
    main()