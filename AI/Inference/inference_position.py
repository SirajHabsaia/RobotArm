# inference_position.py
"""Inference for the piece-center regression model (see AI/train/train_position.py).

Predicts where the chess piece sits inside a 32x32 square crop.  The output is
(x, y) in percent, measured from the BOTTOM-LEFT corner: x left -> right, y
bottom -> top, so ``50 50`` is the center.  This is the same convention used by
the labeling tool and the training targets.
"""

import os
import time
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

# ------------------ CONFIG ------------------
IMG_SIZE = 32

HERE = Path(__file__).resolve().parent
# prefer a model copied next to this script, else the freshly trained one
_MODEL_CANDIDATES = [
    HERE / "position_model.pth",
    HERE.parent / "train" / "best_position_model.pth",
]
MODEL_FILE = next((str(p) for p in _MODEL_CANDIDATES if p.exists()),
                  str(_MODEL_CANDIDATES[0]))

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_TRANSFORM = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
])


# ------------------ MODEL DEFINITION ------------------
# Must match PositionCNN in AI/train/train_position.py
class PositionCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1),
            nn.BatchNorm2d(8),
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 32 -> 16

            nn.Conv2d(8, 16, 3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 16 -> 8

            nn.Conv2d(16, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),                  # 8 -> 4
        )
        self.head = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 4 * 4, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 2),
            nn.Sigmoid(),                     # outputs in [0, 1]
        )

    def forward(self, x):
        return self.head(self.features(x))


# ------------------ MODEL LOADING ------------------
def load_model(model_path=MODEL_FILE):
    """Load the position model once so it can be reused across many images."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model weights not found: {model_path}\n"
            "Train the model first (python AI/train/train_position.py) or copy "
            "best_position_model.pth next to this script as position_model.pth."
        )
    model = PositionCNN().to(DEVICE)
    model.load_state_dict(torch.load(model_path, map_location=DEVICE))
    model.eval()
    return model


# ------------------ INFERENCE ------------------
def predict_position(image_path, model=None, model_path=MODEL_FILE):
    """Predict the piece center for one image.

    Returns ``(x_pct, y_pct, elapsed_seconds)`` where the percentages use the
    bottom-left origin convention.  Pass a preloaded ``model`` to avoid reloading
    the weights on every call.
    """
    if model is None:
        model = load_model(model_path)

    img = Image.open(image_path).convert("RGB")
    img_tensor = _TRANSFORM(img).unsqueeze(0).to(DEVICE)

    start = time.time()
    with torch.no_grad():
        out = model(img_tensor).squeeze(0).cpu()
    elapsed = time.time() - start

    x_pct = out[0].item() * 100.0
    y_pct = out[1].item() * 100.0
    return x_pct, y_pct, elapsed


# ------------------ STANDALONE EXECUTION ------------------
if __name__ == "__main__":
    for fname in ["image.jpg", "image.png"]:
        if os.path.exists(fname):
            image_file = fname
            break
    else:
        print("No image.jpg or image.png found in current folder.")
        raise SystemExit

    x_pct, y_pct, elapsed = predict_position(image_file)
    print(f"Predicted center for {image_file}:")
    print(f"  x = {x_pct:.1f}%  (left -> right)")
    print(f"  y = {y_pct:.1f}%  (bottom -> top)")
    print(f"Inference time: {elapsed*1000:.2f} ms")
