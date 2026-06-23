# gui_inference_position.py
"""Drag-and-drop GUI for the piece-center regression model.

Drop a square image and it shows the predicted piece center as a crosshair dot,
along with the (x, y) percentages (bottom-left origin: x right, y up).
"""

import sys

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from inference_position import load_model, predict_position


class PredictionCanvas(QWidget):
    """Shows an image (aspect-preserved) with a marker at a fractional point."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(360, 360)
        self._pixmap = None
        self._marker = None  # (frac_x, frac_y) top-left origin
        self._placeholder = "Drag and drop an image here"

    def show_placeholder(self, text):
        self._pixmap = None
        self._marker = None
        self._placeholder = text
        self.update()

    def set_result(self, pixmap, frac_x, frac_y):
        self._pixmap = pixmap
        self._marker = (frac_x, frac_y)
        self.update()

    def _image_rect(self):
        if self._pixmap is None or self._pixmap.isNull():
            return None
        pw, ph = self._pixmap.width(), self._pixmap.height()
        if not pw or not ph:
            return None
        scale = min(self.width() / pw, self.height() / ph)
        dw, dh = pw * scale, ph * scale
        return QRectF((self.width() - dw) / 2, (self.height() - dh) / 2, dw, dh)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(30, 30, 30))
        rect = self._image_rect()
        if rect is None:
            p.setPen(QColor(200, 200, 200))
            p.drawText(self.rect(), Qt.AlignCenter, self._placeholder)
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawPixmap(rect, self._pixmap, QRectF(self._pixmap.rect()))
        if self._marker is not None:
            fx, fy = self._marker
            px = rect.left() + fx * rect.width()
            py = rect.top() + fy * rect.height()
            p.setPen(QPen(QColor(255, 255, 255), 3))
            p.drawLine(QPointF(px - 11, py), QPointF(px + 11, py))
            p.drawLine(QPointF(px, py - 11), QPointF(px, py + 11))
            p.setPen(QPen(QColor(230, 30, 30), 1.5))
            p.drawLine(QPointF(px - 11, py), QPointF(px + 11, py))
            p.drawLine(QPointF(px, py - 11), QPointF(px, py + 11))
            p.setBrush(QColor(230, 30, 30))
            p.drawEllipse(QPointF(px, py), 4, 4)


class PositionInferenceGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Piece Center Inference")
        self.setAcceptDrops(True)
        self.resize(420, 520)

        layout = QVBoxLayout(self)
        self.canvas = PredictionCanvas()
        layout.addWidget(self.canvas, stretch=1)
        self.result = QLabel("Drop a square image to predict its piece center.")
        self.result.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result)

        # load the model once; report a friendly message if it is missing
        self.model = None
        try:
            self.model = load_model()
        except FileNotFoundError as e:
            self.canvas.show_placeholder("Model not found")
            self.result.setText(str(e))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        self.run(urls[0].toLocalFile())

    def run(self, path):
        if self.model is None:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self.canvas.show_placeholder("Could not load image")
            self.result.setText(f"Could not load: {path}")
            return
        try:
            x_pct, y_pct, elapsed = predict_position(path, model=self.model)
        except Exception as e:  # noqa: BLE001 - surface any inference error
            self.canvas.show_placeholder("Inference error")
            self.result.setText(f"Error: {e}")
            return
        # bottom-left percentage -> top-left fraction for drawing
        self.canvas.set_result(pixmap, x_pct / 100.0, 1.0 - y_pct / 100.0)
        self.result.setText(
            f"x = {x_pct:.1f}%  (right),   y = {y_pct:.1f}%  (up)"
            f"      [{elapsed*1000:.1f} ms]"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PositionInferenceGUI()
    window.show()
    sys.exit(app.exec())
