import sys
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel
)
from PySide6.QtCore import QTimer

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# =========================
# HARD-CODED LIMITS
# =========================
VEL_LIMIT_A = 10.0
ACC_LIMIT_A = 10.0

VEL_LIMIT_B = 10.0
ACC_LIMIT_B = 10.0


# =========================
# MATPLOTLIB CANVAS
# =========================
class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        fig = Figure(figsize=(10, 6))
        self.ax = [
            fig.add_subplot(2, 2, 1), fig.add_subplot(2, 2, 2),
            fig.add_subplot(2, 2, 3), fig.add_subplot(2, 2, 4),
        ]
        super().__init__(fig)
        fig.tight_layout()


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

        top = QHBoxLayout()
        top.addWidget(self.load_btn)

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
        t = np.array(self.time)
        a = np.array(self.a)
        b = np.array(self.b)

        # Smooth position data to reduce jitter before differentiating
        window = 7
        pad = window // 2
        
        # Pad the data at edges to avoid edge artifacts
        a_padded = np.pad(a, pad, mode='edge')
        b_padded = np.pad(b, pad, mode='edge')
        
        # Convolve and remove padding
        a_smooth = np.convolve(a_padded, np.ones(window)/window, mode='valid')
        b_smooth = np.convolve(b_padded, np.ones(window)/window, mode='valid')

        va = np.gradient(a_smooth, t)
        vb = np.gradient(b_smooth, t)

        # Smooth velocity to reduce jitter
        va_padded = np.pad(va, pad, mode='edge')
        vb_padded = np.pad(vb, pad, mode='edge')
        
        va_smooth = np.convolve(va_padded, np.ones(window)/window, mode='valid')
        vb_smooth = np.convolve(vb_padded, np.ones(window)/window, mode='valid')

        ax = self.canvas.ax
        for axis in ax:
            axis.clear()

        # Joint A
        ax[0].plot(t, a, 'b-', alpha=0.5, label='Raw')
        ax[0].plot(t, a_smooth, 'r-', label='Smoothed')
        ax[0].set_title("Joint A Position")
        ax[0].legend()

        ax[2].plot(t, va, 'b-', alpha=0.5, label='Raw')
        ax[2].plot(t, va_smooth, 'r-', label='Smoothed')
        ax[2].axhline(VEL_LIMIT_A, linestyle="--", color='gray')
        ax[2].axhline(-VEL_LIMIT_A, linestyle="--", color='gray')
        ax[2].set_title("Joint A Velocity")
        ax[2].legend()

        # Joint B
        ax[1].plot(t, b, 'b-', alpha=0.5, label='Raw')
        ax[1].plot(t, b_smooth, 'r-', label='Smoothed')
        ax[1].set_title("Joint B Position")
        ax[1].legend()

        ax[3].plot(t, vb, 'b-', alpha=0.5, label='Raw')
        ax[3].plot(t, vb_smooth, 'r-', label='Smoothed')
        ax[3].axhline(VEL_LIMIT_B, linestyle="--", color='gray')
        ax[3].axhline(-VEL_LIMIT_B, linestyle="--", color='gray')
        ax[3].set_title("Joint B Velocity")
        ax[3].legend()

        self.canvas.draw_idle()


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1100, 800)
    win.show()
    sys.exit(app.exec())
