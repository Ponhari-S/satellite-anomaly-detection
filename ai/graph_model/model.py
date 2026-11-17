import torch
import torch.nn as nn


class DynamicGraphAnomalyDetector(nn.Module):
    def __init__(self, num_nodes=9, node_feature_dim=19, hidden_dim=32):
        super().__init__()
        self.num_nodes = num_nodes

        # Per-node feature encoder (same 19 features as the baseline)
        self.node_encoder = nn.Linear(node_feature_dim, hidden_dim)

        # Graph convolution: mixes each node's features with its
        # time-varying neighbors, using the per-window adjacency matrix
        self.graph_conv = nn.Linear(hidden_dim, hidden_dim)

        # Temporal layer: combines a sequence of graph snapshots over time
        self.temporal = nn.GRU(hidden_dim, hidden_dim, batch_first=True)

        self.classifier = nn.Linear(hidden_dim, 1)
        self.activation = nn.ReLU()

    def forward(self, node_features, adjacency):
        """
        node_features: [batch, time, num_nodes, node_feature_dim]
        adjacency:     [batch, time, num_nodes, num_nodes]
        returns:       [batch, num_nodes] anomaly logits (final time step)
        """
        batch, time_steps, num_nodes, feat_dim = node_features.shape

        # Encode each node's raw features into hidden_dim
        h = self.node_encoder(node_features)  # [batch, time, nodes, hidden]
        h = self.activation(h)

        # Graph convolution at each time step: h' = A @ h, then a linear layer
        # (A is the adjacency matrix — this mixes each node with its neighbors)
        h_conv = torch.matmul(adjacency, h)          # [batch, time, nodes, hidden]
        h_conv = self.graph_conv(h_conv)
        h_conv = self.activation(h_conv)

        # Reshape so each NODE gets its own time sequence fed through the GRU:
        # [batch, time, nodes, hidden] -> [batch*nodes, time, hidden]
        h_seq = h_conv.permute(0, 2, 1, 3).reshape(batch * num_nodes, time_steps, -1)

        _, h_final = self.temporal(h_seq)   # h_final: [1, batch*nodes, hidden]
        h_final = h_final.squeeze(0).reshape(batch, num_nodes, -1)  # [batch, nodes, hidden]

        logits = self.classifier(h_final).squeeze(-1)  # [batch, nodes]
        return logits


if __name__ == "__main__":
    import numpy as np
    import pandas as pd
    from graph_construction import build_graph_snapshots, CHANNELS

    print("Loading raw telemetry and building graph snapshots...")
    raw_df = pd.read_csv("datasets/dataset.csv")
    snapshots = build_graph_snapshots(raw_df, window="1D")
    print(f"Built {len(snapshots)} graph snapshots (1-day windows)")

    # Take a sequence of 5 consecutive snapshots as one training example
    seq_len = 5
    example_snapshots = snapshots[:seq_len]

    node_features = torch.tensor(
        np.array([s["node_features"] for s in example_snapshots]), dtype=torch.float32
    ).unsqueeze(0)  # [1, time, nodes, features]

    adjacency = torch.tensor(
        np.array([s["adjacency"] for s in example_snapshots]), dtype=torch.float32
    ).unsqueeze(0)  # [1, time, nodes, nodes]

    print(f"\nnode_features shape: {node_features.shape}  (expected [1, {seq_len}, 9, 19])")
    print(f"adjacency shape:     {adjacency.shape}  (expected [1, {seq_len}, 9, 9])")

    model = DynamicGraphAnomalyDetector(num_nodes=len(CHANNELS), node_feature_dim=19, hidden_dim=32)
    logits = model(node_features, adjacency)

    print(f"\nForward pass output shape: {logits.shape}  (expected [1, 9] — one logit per channel)")
    print(f"Output values (untrained, random weights): {logits.detach().numpy()}")
    print("\nForward pass successful — architecture is wired correctly end-to-end.")