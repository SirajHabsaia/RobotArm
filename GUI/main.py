import os
import sys

# Default to the X11 (xcb) Qt platform before any Qt module is imported.
# It works on both X11 and Wayland (via XWayland) and avoids the Wayland-default
# crash seen in packaged builds. Override by setting QT_QPA_PLATFORM beforehand.
if sys.platform == "linux":
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6.QtWidgets import QApplication
from gui import MainWindow

app = QApplication(sys.argv)

window = MainWindow()
window.show()
app.exec()
