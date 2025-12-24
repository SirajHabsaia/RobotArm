import sys
import serial
import serial.tools.list_ports
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QLineEdit
)
from PySide6.QtCore import QThread, Signal, QTimer

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# =========================
# HARD-CODED LIMITS
# =========================
VEL_LIMIT_A = 10.0     # deg/s
ACC_LIMIT_A = 10.0    # deg/s^2

VEL_LIMIT_B = 10.0
ACC_LIMIT_B = 10.0


# =========================
# SERIAL READER THREAD
# =========================
class SerialThread(QThread):
    new_sample = Signal(float, float, float)

    def __init__(self, port, baud=115200):
        super().__init__()
        self.port = port
        self.baud = baud
        self.running = True
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
        except Exception as e:
            print("Serial error:", e)
            return

        while self.running:
            try:
                line = self.ser.readline().decode(errors="ignore").strip()
                if not line:
                    continue

                # Expected: t0.050a0.00b0.00
                if not (line.startswith("t") and "a" in line and "b" in line):
                    continue

                t = float(line.split("a")[0][1:])
                a = float(line.split("a")[1].split("b")[0])
                b = float(line.split("b")[1])

                self.new_sample.emit(t, a, b)

            except:
                pass

        if self.ser:
            self.ser.close()

    def write_command(self, command):
        """Send a command to the serial port."""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((command + "\n").encode())
                return True
            except Exception as e:
                print("Write error:", e)
                return False
        return False

    def stop(self):
        self.running = False
        self.wait()


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
        self.setWindowTitle("Robot Arm Debugger")

        self.time = []
        self.a = []
        self.b = []

        self.thread = None

        self.canvas = PlotCanvas()

        self.port_box = QComboBox()
        self.refresh_ports()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connection)

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command...")
        self.command_input.returnPressed.connect(self.send_command)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_command)
        self.send_btn.setEnabled(False)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_data)

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("COM Port:"))
        top_bar.addWidget(self.port_box)
        top_bar.addWidget(self.connect_btn)
        top_bar.addWidget(QLabel("Command:"))
        top_bar.addWidget(self.command_input)
        top_bar.addWidget(self.send_btn)
        top_bar.addWidget(self.clear_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(100)  # 10 Hz update

    def refresh_ports(self):
        self.port_box.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_box.addItem(p.device)

    def toggle_connection(self):
        if self.thread is None:
            port = self.port_box.currentText()
            if not port:
                return

            self.time.clear()
            self.a.clear()
            self.b.clear()

            self.thread = SerialThread(port)
            self.thread.new_sample.connect(self.on_sample)
            self.thread.start()
            self.connect_btn.setText("Disconnect")
            self.send_btn.setEnabled(True)
        else:
            self.thread.stop()
            self.thread = None
            self.connect_btn.setText("Connect")
            self.send_btn.setEnabled(False)

    def on_sample(self, t, a, b):
        self.time.append(t)
        self.a.append(a)
        self.b.append(b)

    def send_command(self):
        if self.thread is None:
            return
        
        command = self.command_input.text().strip()
        if not command:
            return
        
        if self.thread.write_command(command):
            print(f"Sent: {command}")
            self.command_input.clear()
        else:
            print("Failed to send command")

    def clear_data(self):
        """Clear all data and graphs without disconnecting serial."""
        self.time.clear()
        self.a.clear()
        self.b.clear()
        
        # Clear all plots
        for axis in self.canvas.ax:
            axis.clear()
        self.canvas.draw_idle()
        
        print("Data cleared")

    def update_plots(self):
        if len(self.time) < 3:
            return

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
