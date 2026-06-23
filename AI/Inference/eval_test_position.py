# eval_test_position.py
"""Evaluate the piece-center model on every labeled test image.

Reports the mean / median center error (Euclidean distance in percentage points)
and lists the 10 worst predictions with their file paths, so badly-fitting or
mislabeled squares are easy to find and inspect.

Run from anywhere:
    python AI/Inference/eval_test_position.py
"""

import math
import os
from pathlib import Path

from inference_position import load_model, predict_position

# test images live in data/<split>/<color> with labels in <color>_labels
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SPLIT = "test"
COLORS = ["white", "black"]
IMG_EXTS = (".jpg", ".png")


def gather_labeled(split):
    """Yield (image_path, x_pct, y_pct) for every labeled image in a split."""
    samples = []
    for color in COLORS:
        img_dir = DATA_DIR / split / color
        lbl_dir = DATA_DIR / split / f"{color}_labels"
        if not img_dir.is_dir():
            continue
        for fname in sorted(os.listdir(img_dir)):
            stem, ext = os.path.splitext(fname)
            if ext.lower() not in IMG_EXTS:
                continue
            lbl_path = lbl_dir / f"{stem}.txt"
            if not lbl_path.is_file():
                continue
            parts = lbl_path.read_text(encoding="utf-8").split()
            if len(parts) < 2:
                print(f"  skipping malformed label: {lbl_path}")
                continue
            samples.append((img_dir / fname, float(parts[0]), float(parts[1])))
    return samples


def main():
    model = load_model()
    samples = gather_labeled(SPLIT)
    if not samples:
        raise SystemExit(
            f"No labeled images in data/{SPLIT}/<color>_labels. Label some first."
        )

    results = []  # (error_pct, image_path, (px, py), (gx, gy))
    for img_path, gx, gy in samples:
        px, py, _ = predict_position(str(img_path), model=model)
        err = math.hypot(px - gx, py - gy)  # distance in percentage points
        results.append((err, img_path, (px, py), (gx, gy)))

    errors = sorted(r[0] for r in results)
    n = len(errors)
    mean_err = sum(errors) / n
    median_err = errors[n // 2]

    print(f"\nEvaluated {n} labeled {SPLIT} images")
    print(f"  mean   center error: {mean_err:.2f}% pts")
    print(f"  median center error: {median_err:.2f}% pts")
    print(f"  max    center error: {errors[-1]:.2f}% pts")

    # Error binned by how far the TRUE center is from the middle of the square.
    # A lazy "always predict 50,50" model looks fine on the (crowded) near-center
    # bins and terrible on the far bins, so this exposes it; the balanced average
    # weights each bin equally instead of letting near-center samples dominate.
    bin_edges = [0, 5, 10, 15, 20, 25, 100]   # distance from center, % pts
    buckets = [[] for _ in range(len(bin_edges) - 1)]
    for err, _, _, (gx, gy) in results:
        radius = math.hypot(gx - 50.0, gy - 50.0)
        for b in range(len(bin_edges) - 1):
            if bin_edges[b] <= radius < bin_edges[b + 1]:
                buckets[b].append(err)
                break

    print("\nError by distance of true center from the middle:")
    print(f"  {'radius band':>14}  {'count':>6}  {'mean err':>9}")
    bin_means = []
    for b, bucket in enumerate(buckets):
        if not bucket:
            continue
        m = sum(bucket) / len(bucket)
        bin_means.append(m)
        band = f"{bin_edges[b]}-{bin_edges[b+1]}%"
        print(f"  {band:>14}  {len(bucket):>6}  {m:>7.2f}% pts")
    if bin_means:
        print(f"  balanced (per-band) mean error: "
              f"{sum(bin_means)/len(bin_means):.2f}% pts")

    print("\nWorst 10 predictions:")
    print(f"  {'error':>7}  {'predicted':>13}  {'label':>13}  path")
    for err, img_path, (px, py), (gx, gy) in sorted(results, reverse=True)[:10]:
        rel = os.path.relpath(img_path, DATA_DIR.parent.parent)
        print(
            f"  {err:6.2f}%  ({px:5.1f},{py:5.1f})  ({gx:5.1f},{gy:5.1f})  {rel}"
        )


if __name__ == "__main__":
    main()
