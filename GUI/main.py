import os
import sys

# Default to X11 on Linux to avoid issues with Wayland and PySide6.
if sys.platform == "linux":
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6.QtWidgets import QApplication
from gui import MainWindow

# --dev enables developer overlays
dev_mode = "--dev" in sys.argv

app = QApplication(sys.argv)

window = MainWindow(dev_mode=dev_mode)
window.show()
app.exec()