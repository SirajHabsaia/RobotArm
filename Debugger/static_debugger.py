import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QCheckBox
)
from PySide6.QtCore import QTimer

from plotter import PlotCanvas, update_plots


# =========================
# MAIN WINDOW
# =========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Offline Robot Arm Debugger")

        self.time = []
        self.a = []
        self.b = []

        self.canvas = PlotCanvas()

        self.load_btn = QPushButton("Load output.txt")
        self.load_btn.clicked.connect(self.load_file)

        self.show_raw_cb = QCheckBox("Show Raw")
        self.show_raw_cb.setChecked(True)
        self.show_raw_cb.stateChanged.connect(self.update_plots)

        self.show_smoothed_cb = QCheckBox("Show Smoothed")
        self.show_smoothed_cb.setChecked(True)
        self.show_smoothed_cb.stateChanged.connect(self.update_plots)

        top = QHBoxLayout()
        top.addWidget(self.load_btn)
        top.addStretch()
        top.addWidget(self.show_raw_cb)
        top.addWidget(self.show_smoothed_cb)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    # =========================
    # FILE PARSING
    # =========================
    def load_file(self):
        file_path = "Debugger/output.txt"
        if not file_path:
            return

        self.time.clear()
        self.a.clear()
        self.b.clear()

        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if not (line.startswith("t") and "a" in line and "b" in line):
                    continue

                try:
                    t = float(line.split("a")[0][1:])
                    a = float(line.split("a")[1].split("b")[0])
                    b = float(line.split("b")[1])

                    self.time.append(t)
                    self.a.append(a)
                    self.b.append(b)
                except:
                    pass

        if len(self.time) < 3:
            return

        self.update_plots()

    # =========================
    # PLOTTING
    # =========================
    def update_plots(self):
        update_plots(self.canvas, self.time, self.a, self.b,
                    show_raw=self.show_raw_cb.isChecked(),
                    show_smoothed=self.show_smoothed_cb.isChecked())


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1100, 800)
    win.show()
    sys.exit(app.exec())
