"""
Custom widgets for the drawing functionality in the main GUI.
"""

from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QPainter, QPen, QColor, QFont
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class ImageDisplayWidget(QLabel):
    """Widget for displaying dropped/loaded images with drag & drop support."""
    
    image_dropped = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                background-color: #333333;
                border: 2px dashed #666;
            }
        """)
        self.setText("Drop Image Here")
        self.setScaledContents(False)
        self.original_pixmap = None
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Accept image files."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle dropped files."""
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.load_image(file_path)
                self.image_dropped.emit(file_path)
                
    def load_image(self, file_path: str):
        """Load and display an image."""
        self.original_pixmap = QPixmap(file_path)
        self.update_display()
        
    def update_display(self):
        """Update the displayed image to fit while maintaining aspect ratio."""
        if self.original_pixmap:
            scaled_pixmap = self.original_pixmap.scaled(
                self.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
        else:
            self.clear()
            self.setText("Drop Image Here")
            
    def resizeEvent(self, event):
        """Handle resize events to keep image scaled."""
        super().resizeEvent(event)
        if self.original_pixmap:
            self.update_display()
    
    def clear_image(self):
        """Clear the displayed image."""
        self.original_pixmap = None
        self.update_display()


class ManualDrawingWidget(QWidget):
    """Widget for manual drawing with mouse to create polylines."""
    
    drawing_updated = Signal()  # Signal emitted when drawing changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(240, 240)
        self.polylines = []  # List of polylines, each is a list of QPoint
        self.current_polyline = []  # Current polyline being drawn
        self.is_drawing = False
        
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
            }
        """)
        self.setAutoFillBackground(True)
        
    def mousePressEvent(self, event):
        """Start a new polyline when left mouse button is pressed."""
        if event.button() == Qt.LeftButton:
            self.is_drawing = True
            self.current_polyline = [event.pos()]
            self.update()
    
    def mouseMoveEvent(self, event):
        """Add points to current polyline while dragging."""
        if self.is_drawing and event.buttons() & Qt.LeftButton:
            self.current_polyline.append(event.pos())
            self.update()
    
    def mouseReleaseEvent(self, event):
        """End current polyline when mouse is released."""
        if event.button() == Qt.LeftButton and self.is_drawing:
            self.is_drawing = False
            if len(self.current_polyline) > 1:  # Only save if has multiple points
                self.polylines.append(self.current_polyline.copy())
                self.drawing_updated.emit()
            self.current_polyline = []
            self.update()
    
    def paintEvent(self, event):
        """Draw all polylines and the current polyline being drawn."""
        # Call parent paintEvent to draw background
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw dashed border manually
        border_pen = QPen(QColor("#666666"), 2)
        border_pen.setStyle(Qt.DashLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
        
        # Show placeholder text if no polylines exist
        if not self.polylines and not self.current_polyline:
            painter.setPen(QColor("#666666"))
            font = QFont()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, "Start drawing")
            return
        
        # Draw completed polylines in cyan with dashed lines
        pen = QPen(QColor("#00FFFF"), 2)
        pen.setStyle(Qt.DashLine)  # Set dashed line style
        painter.setPen(pen)
        for polyline in self.polylines:
            if len(polyline) > 1:
                for i in range(len(polyline) - 1):
                    painter.drawLine(polyline[i], polyline[i + 1])
        
        # Draw current polyline being drawn in yellow (solid line)
        if self.current_polyline and len(self.current_polyline) > 1:
            pen.setColor(QColor("#FFFF00"))
            pen.setStyle(Qt.SolidLine)  # Solid line for active drawing
            painter.setPen(pen)
            for i in range(len(self.current_polyline) - 1):
                painter.drawLine(self.current_polyline[i], self.current_polyline[i + 1])
    
    def get_polylines_as_numpy(self):
        """Convert polylines from QPoint lists to numpy arrays.
        
        Returns:
            List of numpy arrays, each of shape (n, 2) containing (x, y) coordinates
        """
        numpy_polylines = []
        for polyline in self.polylines:
            if len(polyline) > 1:
                points = np.array([[p.x(), p.y()] for p in polyline], dtype=np.float32)
                numpy_polylines.append(points)
        return numpy_polylines
    
    def clear_drawing(self):
        """Clear all polylines."""
        self.polylines = []
        self.current_polyline = []
        self.is_drawing = False
        self.update()
        self.drawing_updated.emit()
    
    def undo_last_polyline(self):
        """Remove the last drawn polyline."""
        if self.polylines:
            self.polylines.pop()
            self.update()
            self.drawing_updated.emit()
    
    def has_polylines(self):
        """Check if there are any polylines drawn."""
        return len(self.polylines) > 0


class PolylineDisplayWidget(QWidget):
    """Widget for displaying extracted polylines using matplotlib."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.polylines = []
        self.square_size = 200.0
        self.center_x = 0.0
        self.center_y = 0.0
        
        # Set up matplotlib canvas
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(facecolor='#333333')
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)
        
        # Style the axes for dark theme
        self.axes.set_facecolor('#333333')
        self.axes.tick_params(colors='white', labelcolor='white')
        self.axes.spines['bottom'].set_color('white')
        self.axes.spines['top'].set_color('white')
        self.axes.spines['left'].set_color('white')
        self.axes.spines['right'].set_color('white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')
        self.axes.title.set_color('white')
        
        layout.addWidget(self.canvas)
        
        self.clear()
    
    def update_polylines(self, polylines, square_size, center_x, center_y):
        """Update and display polylines.
        
        Args:
            polylines: List of numpy arrays, each containing (x, y) coordinates
            square_size: Size of the drawing area square
            center_x: X coordinate of square center
            center_y: Y coordinate of square center
        """
        self.polylines = polylines
        self.square_size = square_size
        self.center_x = center_x
        self.center_y = center_y
        
        self.axes.clear()
        
        if not polylines:
            self.axes.set_facecolor('#333333')
            self.axes.axis('off')
            self.canvas.draw()
            return
        
        # Generate colors for each polyline
        colors = plt.cm.rainbow(np.linspace(0, 1, len(polylines)))
        
        # Draw each polyline
        for polyline, color in zip(polylines, colors):
            if len(polyline) > 0:
                self.axes.plot(
                    polyline[:, 0], 
                    polyline[:, 1], 
                    color=color, 
                    linewidth=0.8, 
                    alpha=0.9
                )
        
        # Draw the square boundary
        half_size = square_size / 2
        square_x = [
            center_x - half_size, 
            center_x + half_size,
            center_x + half_size, 
            center_x - half_size,
            center_x - half_size
        ]
        square_y = [
            center_y - half_size, 
            center_y - half_size,
            center_y + half_size, 
            center_y + half_size,
            center_y - half_size
        ]
        self.axes.plot(square_x, square_y, 'w--', linewidth=1.5, alpha=0.7)
        
        self.axes.set_aspect('equal')
        self.axes.axis('off')  # Hide axes, labels, and ticks
        self.axes.margins(0.05)
        
        # Update canvas
        self.figure.tight_layout()
        self.canvas.draw()
    
    def clear(self):
        """Clear the display."""
        self.polylines = []
        self.axes.clear()
        self.axes.set_facecolor('#333333')
        self.axes.axis('off')  # Hide axes
        self.canvas.draw()


class LiveDrawingWidget(QWidget):
    """Widget for displaying live drawing progress using Arduino feedback."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drawn_points = []  # List of (x, y) tuples
        self.current_position = None  # Current robot position (x, y) from feedback
        self.show_current_position = False  # Whether to show the green dot
        self.square_size = 200.0
        self.center_x = 0.0
        self.center_y = 0.0
        
        # Set up matplotlib canvas
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(facecolor='#333333')
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)
        
        # Style the axes for dark theme
        self.axes.set_facecolor('#333333')
        self.axes.tick_params(colors='white', labelcolor='white')
        self.axes.spines['bottom'].set_color('white')
        self.axes.spines['top'].set_color('white')
        self.axes.spines['left'].set_color('white')
        self.axes.spines['right'].set_color('white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')
        self.axes.title.set_color('white')
        
        layout.addWidget(self.canvas)
        
        self.clear()
    
    def set_workspace(self, square_size, center_x, center_y):
        """Set the workspace parameters.
        
        Args:
            square_size: Size of the drawing area square
            center_x: X coordinate of square center
            center_y: Y coordinate of square center
        """
        self.square_size = square_size
        self.center_x = center_x
        self.center_y = center_y
        self._redraw()
    
    def update_robot_position(self, x, y, show=True):
        """Update the current robot position.
        
        Args:
            x: Current X coordinate from feedback
            y: Current Y coordinate from feedback
            show: Whether to show the green dot indicator
        """
        self.current_position = (x, y)
        self.show_current_position = show
        # Note: We don't redraw here to avoid excessive updates.
        # The position will be drawn on the next scheduled redraw.
    
    def add_point(self, x, y):
        """Add a point to the live drawing.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.drawn_points.append((x, y))
    
    def add_points(self, points):
        """Add multiple points to the live drawing (more efficient).
        
        Args:
            points: List of (x, y) tuples
        """
        self.drawn_points.extend(points)
        self._redraw()
    
    def _redraw(self):
        """Redraw the canvas with current points."""
        self.axes.clear()
        
        # Draw the square boundary
        half_size = self.square_size / 2
        square_x = [
            self.center_x - half_size, 
            self.center_x + half_size,
            self.center_x + half_size, 
            self.center_x - half_size,
            self.center_x - half_size
        ]
        square_y = [
            self.center_y - half_size, 
            self.center_y - half_size,
            self.center_y + half_size, 
            self.center_y + half_size,
            self.center_y - half_size
        ]
        self.axes.plot(square_x, square_y, 'w--', linewidth=1.5, alpha=0.7)
        
        # Draw points if any - use scatter for performance
        if self.drawn_points:
            x_coords = [p[0] for p in self.drawn_points]
            y_coords = [p[1] for p in self.drawn_points]
            self.axes.scatter(x_coords, y_coords, c='cyan', s=0.5, alpha=0.8)
        
        # Draw current robot position as a green dot (only when actively drawing)
        if self.current_position is not None and self.show_current_position:
            self.axes.scatter(
                self.current_position[0], 
                self.current_position[1], 
                c='lime', 
                s=50, 
                alpha=1.0, 
                marker='o',
                edgecolors='white',
                linewidths=1.5,
                zorder=10  # Draw on top of other elements
            )
        
        self.axes.set_aspect('equal')
        self.axes.axis('off')  # Hide axes, labels, and ticks
        self.axes.margins(0.05)
        
        # Update canvas
        self.figure.tight_layout()
        self.canvas.draw()
    
    def clear(self):
        """Clear all drawn points."""
        self.drawn_points = []
        self.current_position = None
        self.show_current_position = False
        self.axes.clear()
        self.axes.set_facecolor('#333333')
        self.axes.axis('off')  # Hide axes
        self.canvas.draw()
