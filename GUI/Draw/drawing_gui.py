import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QSlider, QPushButton, QFileDialog,
                               QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent
import numpy as np
import cv2
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from poly_extract import ImageToPolylines


class ImageDropLabel(QLabel):
    """Custom QLabel that accepts drag and drop for images."""
    
    image_dropped = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px dashed #999;
                border-radius: 5px;
            }
        """)
        self.setText("Drag & Drop Image Here\nor Click to Browse")
        self.setMinimumSize(300, 300)
        self.setScaledContents(False)
        self.original_pixmap = None
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.load_image(file_path)
                self.image_dropped.emit(file_path)
                
    def mousePressEvent(self, event):
        """Allow browsing for file on click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.load_image(file_path)
            self.image_dropped.emit(file_path)
            
    def load_image(self, file_path):
        """Load and display an image."""
        self.original_pixmap = QPixmap(file_path)
        self.update_display()
        
    def update_display(self):
        """Update the displayed image to fit the label."""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            
    def resizeEvent(self, event):
        """Handle resize events to keep image scaled."""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update_display()


class MatplotlibCanvas(FigureCanvas):
    """Matplotlib canvas widget for embedding plots."""
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
    def clear(self):
        """Clear the canvas."""
        self.axes.clear()
        self.draw()


class DrawingGUI(QMainWindow):
    """Main GUI for image to polyline conversion."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Drawing - Image to Polylines Converter")
        self.setGeometry(100, 100, 1400, 700)
        
        self.image_path = None
        self.converter = None
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Left panel: Image and controls
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, stretch=1)
        
        # Middle panel: Edge detection
        middle_panel = self.create_middle_panel()
        main_layout.addWidget(middle_panel, stretch=1)
        
        # Right panel: Polylines
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, stretch=1)
        
    def create_left_panel(self):
        """Create the left panel with image drop zone and controls."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Input Image")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Image drop zone
        self.image_label = ImageDropLabel()
        self.image_label.image_dropped.connect(self.on_image_loaded)
        layout.addWidget(self.image_label, stretch=1)
        
        # Controls group
        controls_group = QGroupBox("Parameters")
        controls_layout = QGridLayout(controls_group)
        
        # Canny Threshold 1
        controls_layout.addWidget(QLabel("Canny Threshold 1:"), 0, 0)
        self.canny1_value_label = QLabel("50")
        controls_layout.addWidget(self.canny1_value_label, 0, 1)
        self.canny1_slider = QSlider(Qt.Horizontal)
        self.canny1_slider.setMinimum(0)
        self.canny1_slider.setMaximum(255)
        self.canny1_slider.setValue(50)
        self.canny1_slider.valueChanged.connect(self.on_parameter_changed)
        controls_layout.addWidget(self.canny1_slider, 1, 0, 1, 2)
        
        # Canny Threshold 2
        controls_layout.addWidget(QLabel("Canny Threshold 2:"), 2, 0)
        self.canny2_value_label = QLabel("150")
        controls_layout.addWidget(self.canny2_value_label, 2, 1)
        self.canny2_slider = QSlider(Qt.Horizontal)
        self.canny2_slider.setMinimum(0)
        self.canny2_slider.setMaximum(255)
        self.canny2_slider.setValue(150)
        self.canny2_slider.valueChanged.connect(self.on_parameter_changed)
        controls_layout.addWidget(self.canny2_slider, 3, 0, 1, 2)
        
        # Closing Kernel Size
        controls_layout.addWidget(QLabel("Closing Kernel:"), 4, 0)
        self.closing_value_label = QLabel("3")
        controls_layout.addWidget(self.closing_value_label, 4, 1)
        self.closing_slider = QSlider(Qt.Horizontal)
        self.closing_slider.setMinimum(0)
        self.closing_slider.setMaximum(15)
        self.closing_slider.setValue(3)
        self.closing_slider.setSingleStep(2)
        self.closing_slider.valueChanged.connect(self.on_parameter_changed)
        controls_layout.addWidget(self.closing_slider, 5, 0, 1, 2)
        
        # Endpoint Merge Distance
        controls_layout.addWidget(QLabel("Merge Distance:"), 6, 0)
        self.merge_value_label = QLabel("10")
        controls_layout.addWidget(self.merge_value_label, 6, 1)
        self.merge_slider = QSlider(Qt.Horizontal)
        self.merge_slider.setMinimum(0)
        self.merge_slider.setMaximum(50)
        self.merge_slider.setValue(10)
        self.merge_slider.valueChanged.connect(self.on_parameter_changed)
        controls_layout.addWidget(self.merge_slider, 7, 0, 1, 2)
        
        # Process button
        self.process_btn = QPushButton("Process Image")
        self.process_btn.clicked.connect(self.process_image)
        self.process_btn.setEnabled(False)
        controls_layout.addWidget(self.process_btn, 8, 0, 1, 2)
        
        # Export button
        self.export_btn = QPushButton("Export Waypoints")
        self.export_btn.clicked.connect(self.export_waypoints)
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn, 9, 0, 1, 2)
        
        # Stats label
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("font-size: 9pt; color: #666;")
        controls_layout.addWidget(self.stats_label, 10, 0, 1, 2)
        
        layout.addWidget(controls_group)
        
        return panel
        
    def create_middle_panel(self):
        """Create the middle panel for edge detection visualization."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Edge Detection")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Canvas
        self.edges_canvas = MatplotlibCanvas(panel, width=5, height=5)
        self.edges_canvas.axes.set_title("Detected Edges")
        self.edges_canvas.axes.axis('off')
        layout.addWidget(self.edges_canvas)
        
        return panel
        
    def create_right_panel(self):
        """Create the right panel for polyline visualization."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title
        title = QLabel("Polylines")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Canvas
        self.polylines_canvas = MatplotlibCanvas(panel, width=5, height=5)
        self.polylines_canvas.axes.set_title("Extracted Polylines")
        self.polylines_canvas.axes.set_aspect('equal')
        layout.addWidget(self.polylines_canvas)
        
        return panel
        
    def on_image_loaded(self, file_path):
        """Handle image loading."""
        self.image_path = file_path
        self.process_btn.setEnabled(True)
        self.process_image()
        
    def on_parameter_changed(self):
        """Handle parameter slider changes."""
        # Update value labels
        self.canny1_value_label.setText(str(self.canny1_slider.value()))
        self.canny2_value_label.setText(str(self.canny2_slider.value()))
        self.closing_value_label.setText(str(self.closing_slider.value()))
        self.merge_value_label.setText(str(self.merge_slider.value()))
        
        # Auto-process if image is loaded
        if self.image_path:
            self.process_image()
            
    def process_image(self):
        """Process the image with current parameters."""
        if not self.image_path:
            return
            
        try:
            # Create converter with current parameters
            self.converter = ImageToPolylines(
                image_path=self.image_path,
                drawing_z=-50.0,
                pen_lift_z=0.0,
                square_size=200.0,
                center_x=0.0,
                center_y=0.0,
                canny_threshold1=self.canny1_slider.value(),
                canny_threshold2=self.canny2_slider.value(),
                min_contour_length=10,
                closing_kernel_size=self.closing_slider.value(),
                endpoint_merge_distance=float(self.merge_slider.value())
            )
            
            # Process
            self.converter.load_and_process_image()
            self.converter.extract_polylines()
            self.converter.scale_to_workspace()
            
            # Update visualizations
            self.update_edges_display()
            self.update_polylines_display()
            
            # Update stats
            polylines_with_control = self.converter.get_waypoints_with_pen_control()
            polylines = self.converter.get_polylines_only()
            total_waypoints = sum(len(p) for p in polylines_with_control)
            stats_text = f"Polylines: {len(polylines)}\\n"
            stats_text += f"Total Points: {sum(len(p) for p in polylines)}\\n"
            stats_text += f"Total Waypoints: {total_waypoints}"
            self.stats_label.setText(stats_text)
            
            # Enable export
            self.export_btn.setEnabled(True)
            
        except Exception as e:
            print(f"Error processing image: {e}")
            import traceback
            traceback.print_exc()
            
    def update_edges_display(self):
        """Update the edge detection display."""
        if self.converter and self.converter.edges is not None:
            self.edges_canvas.axes.clear()
            self.edges_canvas.axes.imshow(self.converter.edges, cmap='gray')
            self.edges_canvas.axes.set_title('Detected Edges')
            self.edges_canvas.axes.axis('off')
            self.edges_canvas.draw()
            
    def update_polylines_display(self):
        """Update the polylines display."""
        if self.converter and self.converter.scaled_polylines:
            self.polylines_canvas.axes.clear()
            
            # Generate colors for each polyline
            colors = plt.cm.rainbow(np.linspace(0, 1, len(self.converter.scaled_polylines)))
            
            # Draw each polyline with a different color
            for polyline, color in zip(self.converter.scaled_polylines, colors):
                self.polylines_canvas.axes.plot(
                    polyline[:, 0], 
                    polyline[:, 1], 
                    color=color, 
                    linewidth=0.5, 
                    alpha=0.8
                )
            
            # Draw the square boundary
            half_size = self.converter.square_size / 2
            square_x = [
                self.converter.center_x - half_size, 
                self.converter.center_x + half_size,
                self.converter.center_x + half_size, 
                self.converter.center_x - half_size,
                self.converter.center_x - half_size
            ]
            square_y = [
                self.converter.center_y - half_size, 
                self.converter.center_y - half_size,
                self.converter.center_y + half_size, 
                self.converter.center_y + half_size,
                self.converter.center_y - half_size
            ]
            self.polylines_canvas.axes.plot(square_x, square_y, 'k--', linewidth=2, label='Drawing Area')
            
            self.polylines_canvas.axes.set_aspect('equal')
            self.polylines_canvas.axes.set_title(f'Extracted Polylines ({len(self.converter.scaled_polylines)} polylines)')
            self.polylines_canvas.axes.set_xlabel('X (mm)')
            self.polylines_canvas.axes.set_ylabel('Y (mm)')
            self.polylines_canvas.axes.grid(True, alpha=0.3)
            self.polylines_canvas.axes.legend()
            self.polylines_canvas.axes.margins(0.1)
            self.polylines_canvas.draw()
            
    def export_waypoints(self):
        """Export waypoints to a file."""
        if not self.converter:
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Waypoints", 
            "waypoints.txt", 
            "Text Files (*.txt)"
        )
        
        if file_path:
            self.converter.save_waypoints(file_path)
            print(f"Waypoints exported to {file_path}")


def main():
    app = QApplication(sys.argv)
    window = DrawingGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
