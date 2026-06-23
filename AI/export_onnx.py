"""Export the trained chess CNNs (PyTorch .pth) to ONNX for lightweight runtime
inference (onnxruntime) in the GUI — so the packaged app does not need PyTorch.

Run after training:
    python AI/export_onnx.py

Produces, next to GUI/Chess/:
    model.onnx           (square classifier:  black / empty / white logits)
    model_position.onnx  (piece-centre regressor: x, y in [0,1], sigmoid)

Both ONNX graphs take input (N, 3, 32, 32) float32 in [0, 1], RGB, with a
dynamic batch dimension.
"""

import os
import torch
import torch.nn as nn

HERE = os.path.dirname(os.path.abspath(__file__))
CHESS_DIR = os.path.join(HERE, "..", "GUI", "Chess")


class ChessCNN(nn.Module):
    """Square classifier (must match GUI/Chess/board_detector.py training)."""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1), nn.BatchNorm2d(8), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(32 * 4 * 4, 32), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(32, 3),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class PositionCNN(nn.Module):
    """Piece-centre regressor (sigmoid output in [0, 1])."""
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1), nn.BatchNorm2d(8), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(8, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.head = nn.Sequential(
            nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(64, 2), nn.Sigmoid(),
        )

    def forward(self, x):
        return self.head(self.features(x))


def export(model, weights_path, onnx_path):
    if not os.path.exists(weights_path):
        print(f"[skip] weights not found: {weights_path}")
        return False
    model.load_state_dict(torch.load(weights_path, map_location="cpu"))
    model.eval()  # fold BatchNorm running stats, disable Dropout
    dummy = torch.randn(1, 3, 32, 32)
    torch.onnx.export(
        model, dummy, onnx_path,
        input_names=["input"], output_names=["output"],
        dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        opset_version=17,
        dynamo=False,  # legacy exporter: correctly handles dynamic batch in Flatten
    )
    print(f"[ok] {weights_path}  ->  {onnx_path}")
    return True


if __name__ == "__main__":
    export(ChessCNN(),    os.path.join(CHESS_DIR, "model.pth"),
           os.path.join(CHESS_DIR, "model.onnx"))
    export(PositionCNN(), os.path.join(CHESS_DIR, "model_position.pth"),
           os.path.join(CHESS_DIR, "model_position.onnx"))
