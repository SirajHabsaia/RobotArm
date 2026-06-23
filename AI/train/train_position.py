"""Train a small CNN that regresses the chess-piece center within a square.

This complements the classification model ([train_classification.py]).  Where the
classifier only answers black / empty / white, this model predicts WHERE the
piece sits inside its 32x32 square so the robot arm can aim at the real center
instead of the geometric middle.

Labels
------
Each labeled image ``N.<ext>`` in ``data/<split>/<color>/`` has a matching
``N.txt`` in ``data/<split>/<color>_labels/`` containing two numbers::

    <x> <y>

both in percent, measured from the BOTTOM-LEFT corner (x to the right, y up).
``50 50`` is the center.  These are produced by ``AI/label_tool.py``.

Targets fed to the network are those percentages divided by 100, i.e. fractions
in [0, 1] keeping the same bottom-left origin, so the model output can be written
straight back into the same convention.  The network ends in a sigmoid so its
two outputs are always in [0, 1].

Only images that actually have a label file are used; ``empty`` squares are
ignored entirely (no piece to locate).

Run:
    python AI/train/train_position.py
"""

import math
import os
import random

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms
from tqdm.auto import tqdm

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

DATA_DIR = "../data"
COLORS = ["white", "black"]      # folders that contain pieces (with *_labels)
IMG_EXTS = (".jpg", ".png")

BATCH_SIZE = 32
LR = 0.001
EPOCHS = 60
IMG_SIZE = 32                    # images are already 32x32

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ------------------------------------------------------------
# GEOMETRIC AUGMENTATION (THE 8 SQUARE SYMMETRIES, D4 GROUP)
# ------------------------------------------------------------
# Instead of photometric jitter we expand every labeled image into the 8
# orientations of a square: the 4 multiples of 90 deg rotation, each optionally
# mirrored.  Rotations + mirroring about the two axes generate this whole group.
# Each variant is stored as a real extra sample with its label moved to match.
#
# Labels are fractions in [0, 1] with x measured left -> right and y measured
# BOTTOM -> TOP (so y = 1 is the top of the image).  All coordinate maths below
# is done in that bottom-left origin space.

N_SYMMETRIES = 8                 # 4 rotations x {no mirror, mirror}


def _rot90_coord(x, y, k):
    """Apply k counter-clockwise 90-degree rotations in bottom-left space."""
    for _ in range(k % 4):
        x, y = 1.0 - y, x        # CCW about the square center (0.5, 0.5)
    return x, y


def apply_symmetry(tensor, x, y, tid):
    """Map one of the 8 square symmetries onto a CHW tensor and its label.

    ``tid`` in 0..7 encodes (k rotations, mirror).  The image op and the
    coordinate op are kept in lock-step so the label still points at the piece.
    """
    k = tid % 4
    mirror = tid >= 4

    # torch.rot90 over (H, W) rotates from the H axis toward the W axis; in the
    # bottom-left (y-up) label space this matches the CCW _rot90_coord step, so
    # the same k is used for both the image and the coordinates.
    img = torch.rot90(tensor, k, dims=(1, 2))
    nx, ny = _rot90_coord(x, y, k)

    if mirror:
        img = torch.flip(img, dims=(2,))   # mirror columns = flip about y axis
        nx = 1.0 - nx                      # x -> 1 - x, y unchanged

    return img.contiguous(), nx, ny


# ------------------------------------------------------------
# TRANSLATION AUGMENTATION (SYNTHESIZE OFF-CENTER PIECES)
# ------------------------------------------------------------
# Most labeled pieces sit near the center, so the model learns the lazy habit of
# always predicting (50, 50).  Randomly shifting the piece inside the square
# manufactures off-center examples and moves the label with it, which is the most
# direct cure for the radial imbalance.  The border strip uncovered by the shift
# is filled with the board-square colour plus noise so it looks like real board.

MAX_TRANSLATE = 0.30         # max shift per axis, fraction of the square
TRANSLATE_NOISE_STD = 0.04   # gaussian noise on the filled background
CENTER_MARGIN = 0.05         # keep the shifted label at least this far from edges

FILL_RGB = {                 # board-square colour behind the piece, per folder
    "black": (0x36 / 255, 0x52 / 255, 0x39 / 255),   # #365239 noisy green
    "white": (0xe3 / 255, 0xc7 / 255, 0x98 / 255),   # #e3c798 noisy cream
}


def apply_translation(tensor, x, y, fill_rgb,
                      max_shift=MAX_TRANSLATE, noise_std=TRANSLATE_NOISE_STD):
    """Shift the piece by a random offset, filling the exposed border strip.

    Operates on a CHW tensor in [0, 1].  The shift is clamped so the labeled
    center stays inside the frame.  Returns ``(tensor, nx, ny)`` with the label
    moved to match (bottom-left origin).
    """
    _, H, W = tensor.shape

    dx = random.uniform(-max_shift, max_shift)
    dy = random.uniform(-max_shift, max_shift)
    nx = min(max(x + dx, CENTER_MARGIN), 1.0 - CENTER_MARGIN)
    ny = min(max(y + dy, CENTER_MARGIN), 1.0 - CENTER_MARGIN)
    dx, dy = nx - x, ny - y

    col_shift = round(dx * W)     # +x (right) moves content toward higher cols
    row_shift = round(-dy * H)    # +y (up) moves content toward row 0

    # noisy board-coloured background
    out = torch.empty_like(tensor)
    for c, base in enumerate(fill_rgb):
        out[c] = base
    out.add_(torch.randn_like(out) * noise_std).clamp_(0.0, 1.0)

    # copy the overlapping region into its shifted destination
    src_r0, src_r1 = max(0, -row_shift), H - max(0, row_shift)
    src_c0, src_c1 = max(0, -col_shift), W - max(0, col_shift)
    dst_r0, dst_r1 = max(0, row_shift), H - max(0, -row_shift)
    dst_c0, dst_c1 = max(0, col_shift), W - max(0, -col_shift)
    out[:, dst_r0:dst_r1, dst_c0:dst_c1] = tensor[:, src_r0:src_r1, src_c0:src_c1]

    return out, nx, ny


# ------------------------------------------------------------
# DATASET
# ------------------------------------------------------------


class PieceCenterDataset(Dataset):
    """All labeled piece images of one split, across both colours.

    When ``augment`` is set every base image yields the 8 square symmetries;
    otherwise it yields the original image only.
    """

    def __init__(self, data_dir, split, augment):
        self.augment = augment
        self.base_tf = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
        ])
        self.samples = []  # (image_path, x_frac, y_frac, color)

        for color in COLORS:
            img_dir = os.path.join(data_dir, split, color)
            lbl_dir = os.path.join(data_dir, split, f"{color}_labels")
            if not os.path.isdir(img_dir):
                continue
            for fname in sorted(os.listdir(img_dir)):
                stem, ext = os.path.splitext(fname)
                if ext.lower() not in IMG_EXTS:
                    continue
                lbl_path = os.path.join(lbl_dir, stem + ".txt")
                if not os.path.isfile(lbl_path):
                    continue  # not labeled yet
                with open(lbl_path, "r", encoding="utf-8") as f:
                    parts = f.read().split()
                if len(parts) < 2:
                    print(f"  skipping malformed label: {lbl_path}")
                    continue
                x_frac = float(parts[0]) / 100.0
                y_frac = float(parts[1]) / 100.0
                self.samples.append(
                    (os.path.join(img_dir, fname), x_frac, y_frac, color)
                )

        n_variants = N_SYMMETRIES if augment else 1
        # flat index: (sample index, symmetry id)
        self.index = [
            (i, tid)
            for i in range(len(self.samples))
            for tid in range(n_variants)
        ]
        self.sample_weights = self._radial_weights() if augment else None

    def _radial_weights(self):
        """Inverse smoothed-density weights over distance-from-center (LDS).

        Counters the center-heavy target distribution so the sampler draws the
        rare off-center pieces more often.  ``sqrt`` + clipping keep the few
        extreme (and possibly mislabeled) samples from dominating.
        """
        if not self.samples:
            return None
        r = np.array([math.hypot(x - 0.5, y - 0.5)
                      for _, x, y, _ in self.samples])
        edges = np.linspace(0.0, r.max() + 1e-6, 16)
        dens = gaussian_filter1d(
            np.histogram(r, bins=edges)[0].astype(float), sigma=1.0
        )
        per_bin = 1.0 / np.sqrt(dens + 1e-6)
        bin_idx = np.clip(np.digitize(r, edges) - 1, 0, len(dens) - 1)
        w = per_bin[bin_idx]
        w = np.clip(w / w.mean(), 0.25, 5.0)
        # propagate each base sample's weight to its symmetry variants
        return [float(w[i]) for i, _ in self.index]

    def __len__(self):
        return len(self.index)

    def __getitem__(self, idx):
        sample_idx, tid = self.index[idx]
        path, x_frac, y_frac, color = self.samples[sample_idx]
        img = Image.open(path).convert("RGB")
        tensor = self.base_tf(img)
        tensor, nx, ny = apply_symmetry(tensor, x_frac, y_frac, tid)
        if self.augment:
            tensor, nx, ny = apply_translation(tensor, nx, ny, FILL_RGB[color])
        target = torch.tensor([nx, ny], dtype=torch.float32)
        return tensor, target


# ------------------------------------------------------------
# MODEL (LIGHTWEIGHT REGRESSOR)
# ------------------------------------------------------------
# 32 -> 16 -> 8 -> 4 after three max pools, then a tiny head with 2 outputs.


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


# ------------------------------------------------------------
# METRIC
# ------------------------------------------------------------


def mean_center_error(model, loader):
    """Mean Euclidean distance between prediction and label, in % points."""
    model.eval()
    total_err = 0.0
    n = 0
    with torch.no_grad():
        for imgs, targets in loader:
            imgs, targets = imgs.to(DEVICE), targets.to(DEVICE)
            preds = model(imgs)
            # fractions -> percentage points
            dist = torch.sqrt(((preds - targets) * 100.0).pow(2).sum(dim=1))
            total_err += dist.sum().item()
            n += imgs.size(0)
    return total_err / max(n, 1)


# ------------------------------------------------------------
# TRAINING
# ------------------------------------------------------------

if __name__ == "__main__":
    # train images are expanded into all 8 square symmetries; the test set is
    # kept in its original orientation so the reported error is realistic.
    train_data = PieceCenterDataset(DATA_DIR, "train", augment=True)
    test_data = PieceCenterDataset(DATA_DIR, "test", augment=False)

    print(f"Train samples (after {N_SYMMETRIES}x symmetry aug): {len(train_data)}")
    print(f"Test  samples: {len(test_data)}")
    if len(train_data) == 0:
        raise SystemExit(
            "No labeled training images found. Use AI/label_tool.py to create "
            "labels in data/train/<color>_labels first."
        )
    have_test = len(test_data) > 0
    if not have_test:
        print("Warning: no labeled test images; will save the last-epoch model.")

    # draw off-center pieces more often via inverse-density weights (LDS)
    sampler = WeightedRandomSampler(
        train_data.sample_weights,
        num_samples=len(train_data),
        replacement=True,
    )
    train_loader = DataLoader(train_data, batch_size=BATCH_SIZE, sampler=sampler)
    test_loader = DataLoader(test_data, batch_size=BATCH_SIZE, shuffle=False)

    model = PositionCNN().to(DEVICE)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=5
    )

    best_err = float("inf")

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        print(f"\nEpoch {epoch}/{EPOCHS}")
        progress_bar = tqdm(train_loader, desc="Training", leave=False)

        for imgs, targets in progress_bar:
            imgs, targets = imgs.to(DEVICE), targets.to(DEVICE)
            optimizer.zero_grad()
            preds = model(imgs)
            loss = criterion(preds, targets)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            progress_bar.set_postfix(loss=loss.item())

        avg_loss = train_loss / len(train_loader)

        if have_test:
            val_err = mean_center_error(model, test_loader)
            scheduler.step(val_err)
            print(
                f"Epoch {epoch} | Train MSE: {avg_loss:.5f} | "
                f"Test center error: {val_err:.2f}% pts"
            )
            if val_err < best_err:
                best_err = val_err
                torch.save(model.state_dict(), "best_position_model.pth")
                print(f"✔ Best model updated! ({val_err:.2f}% pts)")
        else:
            print(f"Epoch {epoch} | Train MSE: {avg_loss:.5f}")
            torch.save(model.state_dict(), "best_position_model.pth")

    print(f"\n{'='*50}")
    print("Training complete!")
    if have_test:
        print(f"Best test center error: {best_err:.2f}% points")
    print("Model saved as: best_position_model.pth")
    print(f"{'='*50}")
