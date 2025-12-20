from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton
import sys
from gui import MainWindow

app = QApplication(sys.argv)

window = MainWindow()
window.show()
app.exec()