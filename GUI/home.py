from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
class AspectRatioLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = None
        self.setScaledContents(False)  # IMPORTANT: leave this OFF

    def setPixmap(self, pixmap):
        self.original_pixmap = pixmap
        super().setPixmap(pixmap)

    def resizeEvent(self, event):
        if self.original_pixmap:
            scaled = self.original_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            super().setPixmap(scaled)

        super().resizeEvent(event)
