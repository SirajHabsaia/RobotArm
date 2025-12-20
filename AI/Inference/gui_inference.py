# gui_inference.py
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

from inference2 import predict_image  # import the function from your inference.py

class DragDropWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Square Inference")
        self.setAcceptDrops(True)
        self.resize(400, 500)

        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Image display
        self.image_label = QLabel("Drag and drop an image here")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 2px dashed gray;")
        self.layout.addWidget(self.image_label)

        # Prediction display
        self.pred_list = QListWidget()
        self.layout.addWidget(self.pred_list)

    # Handle drag enter
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    # Handle drop
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.display_image(file_path)
            self.show_predictions(file_path)

    def display_image(self, path):
        pixmap = QPixmap(path)
        pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)

    def show_predictions(self, path):
        self.pred_list.clear()
        try:
            results, time = predict_image(path)  # call your inference function
            for cls, conf in results:
                item = QListWidgetItem(f"{cls}: {conf*100:.2f}%")
                self.pred_list.addItem(item)
            self.pred_list.addItem(f"Time taken: {time*1000:.2f} ms")
        except Exception as e:
            self.pred_list.addItem(f"Error: {str(e)}")

# ----------------- RUN APPLICATION -----------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DragDropWidget()
    window.show()
    sys.exit(app.exec())
