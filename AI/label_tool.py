"""Chess-piece center labeling tool.

A small PySide6 GUI that helps build position labels for the piece-center
regression model.  For every image ``N.<ext>`` in a category folder it writes a
``N.txt`` file in the matching ``*_labels`` folder containing the piece center as
two percentages::

    <x> <y>

where ``x`` and ``y`` are measured from the BOTTOM-LEFT corner of the image, in
percent of the width / height respectively.  So ``50 50`` is the exact center,
``0 0`` is the bottom-left corner and ``100 100`` is the top-right corner.

Workflow
--------
* Pick one of the four categories (train/test x white/black).
* In **Label** mode the tool shows the next unlabeled image (the first image
  whose index is greater than the largest already-labeled index) and you click
  on the piece center.  The label is saved and the next image is shown.  When
  every image is labeled it shows "done".
* In **Check** mode you type an index and the tool shows that image with a dot
  on the stored center (if a label exists).

Run with::

    python AI/label_tool.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QColor, QIntValidator, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

# --- data layout -----------------------------------------------------------

DATA_ROOT = Path(__file__).resolve().parent / "data"
IMAGE_EXTS = (".jpg", ".png")

# (split, color) -> (images subdir, labels subdir)
CATEGORIES = {
    "Train White": ("train/white", "train/white_labels"),
    "Train Black": ("train/black", "train/black_labels"),
    "Test White": ("test/white", "test/white_labels"),
    "Test Black": ("test/black", "test/black_labels"),
}

_INDEX_RE = re.compile(r"\d+")


def parse_index(name: str) -> int | None:
    """Return the leading integer index encoded in a file stem, or None."""
    m = _INDEX_RE.search(name)
    return int(m.group()) if m else None


# --- image canvas ----------------------------------------------------------


class ImageCanvas(QWidget):
    """Displays an image (aspect-preserved, centered) and reports clicks.

    The ``clicked`` signal carries the click position as fractions in [0, 1]
    using the usual TOP-LEFT image origin (x right, y down).  Marker positions
    use the same top-left fractional space.
    """

    clicked = Signal(float, float)  # frac_x, frac_y (top-left origin)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 480)
        self._pixmap: QPixmap | None = None
        self._marker: tuple[float, float] | None = None  # top-left fractions
        self._placeholder = "Select a category"
        self.clickable = False

    # -- public API --
    def set_image(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._marker = None
        self.update()

    def show_placeholder(self, text: str):
        self._pixmap = None
        self._marker = None
        self._placeholder = text
        self.update()

    def set_marker(self, frac_x: float | None, frac_y: float | None):
        if frac_x is None or frac_y is None:
            self._marker = None
        else:
            self._marker = (frac_x, frac_y)
        self.update()

    # -- geometry helper --
    def _image_rect(self) -> QRectF | None:
        """Rect (in widget coords) where the pixmap is actually drawn."""
        if self._pixmap is None or self._pixmap.isNull():
            return None
        pw, ph = self._pixmap.width(), self._pixmap.height()
        if pw == 0 or ph == 0:
            return None
        scale = min(self.width() / pw, self.height() / ph)
        dw, dh = pw * scale, ph * scale
        ox = (self.width() - dw) / 2.0
        oy = (self.height() - dh) / 2.0
        return QRectF(ox, oy, dw, dh)

    # -- events --
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        rect = self._image_rect()
        if rect is None:
            painter.setPen(QColor(200, 200, 200))
            painter.drawText(self.rect(), Qt.AlignCenter, self._placeholder)
            return

        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.drawPixmap(rect, self._pixmap, QRectF(self._pixmap.rect()))

        if self._marker is not None:
            fx, fy = self._marker
            px = rect.left() + fx * rect.width()
            py = rect.top() + fy * rect.height()
            center = QPointF(px, py)
            # white halo + red core crosshair so it shows on any background
            painter.setPen(QPen(QColor(255, 255, 255), 3))
            painter.drawLine(QPointF(px - 11, py), QPointF(px + 11, py))
            painter.drawLine(QPointF(px, py - 11), QPointF(px, py + 11))
            painter.setPen(QPen(QColor(230, 30, 30), 1.5))
            painter.drawLine(QPointF(px - 11, py), QPointF(px + 11, py))
            painter.drawLine(QPointF(px, py - 11), QPointF(px, py + 11))
            painter.setBrush(QColor(230, 30, 30))
            painter.setPen(QPen(QColor(255, 255, 255), 1.5))
            painter.drawEllipse(center, 4, 4)

    def mousePressEvent(self, event):
        if not self.clickable or event.button() != Qt.LeftButton:
            return
        rect = self._image_rect()
        if rect is None or not rect.contains(event.position()):
            return
        fx = (event.position().x() - rect.left()) / rect.width()
        fy = (event.position().y() - rect.top()) / rect.height()
        self.clicked.emit(fx, fy)


# --- main window -----------------------------------------------------------


class LabelTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Piece Center Labeler")

        self.current_category = next(iter(CATEGORIES))
        self.current_image: Path | None = None  # image being labeled / shown

        self._build_ui()
        self._on_category_changed()

    # -- UI construction --
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)

        # category row
        cat_row = QHBoxLayout()
        cat_row.addWidget(QLabel("Category:"))
        self.cat_group = QButtonGroup(self)
        for i, name in enumerate(CATEGORIES):
            rb = QRadioButton(name)
            if i == 0:
                rb.setChecked(True)
            self.cat_group.addButton(rb, i)
            cat_row.addWidget(rb)
        cat_row.addStretch(1)
        self.cat_group.buttonClicked.connect(self._on_category_changed)
        root.addLayout(cat_row)

        # mode row
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_label = QRadioButton("Label")
        self.mode_check = QRadioButton("Check")
        self.mode_label.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self.mode_label)
        mode_group.addButton(self.mode_check)
        self.mode_label.toggled.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_label)
        mode_row.addWidget(self.mode_check)
        mode_row.addSpacing(20)

        # check controls (index entry)
        self.check_label = QLabel("Index:")
        self.index_edit = QLineEdit()
        self.index_edit.setValidator(QIntValidator(0, 10_000_000, self))
        self.index_edit.setFixedWidth(90)
        self.index_edit.returnPressed.connect(self._show_checked_index)
        self.show_btn = QPushButton("Show")
        self.show_btn.clicked.connect(self._show_checked_index)
        mode_row.addWidget(self.check_label)
        mode_row.addWidget(self.index_edit)
        mode_row.addWidget(self.show_btn)
        mode_row.addStretch(1)

        # undo (label mode)
        self.undo_btn = QPushButton("Undo last label")
        self.undo_btn.clicked.connect(self._undo_last)
        mode_row.addWidget(self.undo_btn)
        root.addLayout(mode_row)

        # canvas
        self.canvas = ImageCanvas()
        self.canvas.clicked.connect(self._on_canvas_clicked)
        root.addWidget(self.canvas, stretch=1)

        # status
        self.status = QLabel("")
        self.status.setAlignment(Qt.AlignCenter)
        self.coord = QLabel("")
        self.coord.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)
        root.addWidget(self.coord)

        self.setCentralWidget(central)
        self.resize(640, 720)

    # -- path / scanning helpers --
    def _paths(self, category: str) -> tuple[Path, Path]:
        img_sub, lbl_sub = CATEGORIES[category]
        images = DATA_ROOT / img_sub
        labels = DATA_ROOT / lbl_sub
        labels.mkdir(parents=True, exist_ok=True)
        return images, labels

    def _images_by_index(self, images: Path) -> dict[int, Path]:
        out: dict[int, Path] = {}
        if not images.is_dir():
            return out
        for p in images.iterdir():
            if p.suffix.lower() in IMAGE_EXTS:
                idx = parse_index(p.stem)
                if idx is not None:
                    out[idx] = p
        return out

    def _label_indices(self, labels: Path) -> set[int]:
        out: set[int] = set()
        if not labels.is_dir():
            return out
        for p in labels.glob("*.txt"):
            idx = parse_index(p.stem)
            if idx is not None:
                out.add(idx)
        return out

    def _label_path(self, labels: Path, image: Path) -> Path:
        # keep the image's exact zero padding: 0024.jpg -> 0024.txt
        return labels / (image.stem + ".txt")

    def _next_unlabeled(self, category: str) -> Path | None:
        images, labels = self._paths(category)
        idx_map = self._images_by_index(images)
        if not idx_map:
            return None
        labeled = self._label_indices(labels)
        max_labeled = max(labeled) if labeled else -1
        # first existing image whose index is greater than the largest label
        candidates = sorted(i for i in idx_map if i > max_labeled)
        return idx_map[candidates[0]] if candidates else None

    # -- mode / category changes --
    def _on_category_changed(self, *_):
        btn = self.cat_group.checkedButton()
        if btn is not None:
            self.current_category = btn.text()
        self._refresh()

    def _on_mode_changed(self, *_):
        self._refresh()

    def _is_label_mode(self) -> bool:
        return self.mode_label.isChecked()

    def _refresh(self):
        label_mode = self._is_label_mode()
        # toggle widget visibility per mode
        for w in (self.check_label, self.index_edit, self.show_btn):
            w.setVisible(not label_mode)
        self.undo_btn.setVisible(label_mode)

        if label_mode:
            self._load_next_to_label()
        else:
            self.canvas.clickable = False
            self.current_image = None
            self.canvas.show_placeholder("Enter an index and press Show")
            images, labels = self._paths(self.current_category)
            total = len(self._images_by_index(images))
            done = len(self._label_indices(labels))
            self.status.setText(
                f"{self.current_category} — Check mode "
                f"({done}/{total} labeled)"
            )
            self.coord.setText("")

    # -- label mode --
    def _load_next_to_label(self):
        images, labels = self._paths(self.current_category)
        idx_map = self._images_by_index(images)
        total = len(idx_map)
        done = len(self._label_indices(labels))

        nxt = self._next_unlabeled(self.current_category)
        self.current_image = nxt

        if nxt is None:
            self.canvas.clickable = False
            self.canvas.show_placeholder(
                "done" if total else "No images found in this folder"
            )
            self.status.setText(
                f"{self.current_category} — {done}/{total} labeled"
            )
            self.coord.setText("")
            return

        pix = QPixmap(str(nxt))
        if pix.isNull():
            self.canvas.clickable = False
            self.canvas.show_placeholder(f"Could not load {nxt.name}")
            return

        self.canvas.clickable = True
        self.canvas.set_image(pix)
        idx = parse_index(nxt.stem)
        self.status.setText(
            f"{self.current_category} — labeling {nxt.name}  "
            f"(index {idx},  {done}/{total} done)"
        )
        self.coord.setText("Click on the center of the chess piece")

    def _on_canvas_clicked(self, fx: float, fy: float):
        if not self._is_label_mode() or self.current_image is None:
            return
        # top-left fraction -> bottom-left percentage convention
        x_pct = fx * 100.0
        y_pct = (1.0 - fy) * 100.0

        _, labels = self._paths(self.current_category)
        out = self._label_path(labels, self.current_image)
        out.write_text(f"{x_pct:.1f} {y_pct:.1f}\n", encoding="utf-8")

        saved = self.current_image.name
        self._load_next_to_label()
        self.coord.setText(f"Saved {saved}: {x_pct:.1f} {y_pct:.1f}")

    def _undo_last(self):
        if not self._is_label_mode():
            return
        images, labels = self._paths(self.current_category)
        labeled = self._label_indices(labels)
        if not labeled:
            QMessageBox.information(self, "Undo", "No labels to undo.")
            return
        last = max(labeled)
        idx_map = self._images_by_index(images)
        img = idx_map.get(last)
        if img is None:
            return
        target = self._label_path(labels, img)
        if target.exists():
            target.unlink()
        self._load_next_to_label()
        self.coord.setText(f"Removed label for {img.name} — re-label it")

    # -- check mode --
    def _show_checked_index(self):
        text = self.index_edit.text().strip()
        if not text:
            return
        idx = int(text)
        images, labels = self._paths(self.current_category)
        idx_map = self._images_by_index(images)
        img = idx_map.get(idx)
        if img is None:
            self.canvas.show_placeholder(f"No image with index {idx}")
            self.status.setText(f"{self.current_category} — index {idx} not found")
            self.coord.setText("")
            return

        pix = QPixmap(str(img))
        if pix.isNull():
            self.canvas.show_placeholder(f"Could not load {img.name}")
            return
        self.canvas.set_image(pix)
        self.current_image = img

        lbl = self._label_path(labels, img)
        if lbl.exists():
            try:
                parts = lbl.read_text(encoding="utf-8").split()
                x_pct, y_pct = float(parts[0]), float(parts[1])
            except (ValueError, IndexError):
                self.canvas.set_marker(None, None)
                self.coord.setText(f"{lbl.name} is malformed")
            else:
                # bottom-left percentage -> top-left fraction for drawing
                self.canvas.set_marker(x_pct / 100.0, 1.0 - y_pct / 100.0)
                self.coord.setText(
                    f"{lbl.name}: {x_pct:.1f} {y_pct:.1f}  (x% right, y% up)"
                )
        else:
            self.canvas.set_marker(None, None)
            self.coord.setText(f"No label for {img.name}")
        self.status.setText(f"{self.current_category} — showing {img.name}")


def main():
    app = QApplication(sys.argv)
    win = LabelTool()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
