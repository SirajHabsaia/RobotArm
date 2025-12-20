from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QWheelEvent, QMouseEvent
import math


class CoordinateSystemWidget(QWidget):
    """
    A 2D coordinate system widget with zoom, pan, grid, and axis features.
    Similar to GeoGebra and other plotting tools.
    """
    
    # Signal emitted when coordinates change (e.g., user clicks on the plot)
    coordinatesChanged = Signal(float, float)
    
    def __init__(self, xmin=-350, xmax=350, ymin=-350, ymax=350, Rmin=150, Rmax=350, parent=None):
        super().__init__(parent)
        
        # Coordinate bounds
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        
        # Radius bounds for the stripe region
        self.Rmin = Rmin
        self.Rmax = Rmax
        
        # Current view bounds (can change with zoom/pan)
        self.view_xmin = xmin
        self.view_xmax = xmax
        self.view_ymin = ymin
        self.view_ymax = ymax
        
        # Panning state
        self.is_panning = False
        self.last_pan_pos = None
        
        # Grid and axis settings
        self.show_grid = True
        self.show_axes = True
        self.show_ticks = True
        self.show_labels = True
        
        # Colors and styling (dark mode)
        self.bg_color = QColor(51, 51, 51)  # #333333
        self.grid_color = QColor(80, 80, 80)  # Subtle grid lines
        self.axis_color = QColor(255, 255, 255)  # White axes
        self.tick_color = QColor(200, 200, 200)  # Light gray ticks
        self.label_color = QColor(255, 255, 255)  # White labels
        self.border_color = QColor(100, 100, 100)  # Gray border
        self.cursor_label_bg = QColor(40, 40, 40, 220)  # Semi-transparent dark background
        self.cursor_label_border = QColor(150, 150, 150)  # Light gray border for label
        self.ellipse_color = QColor(0, 150, 255)  # Blue ellipse
        self.excluded_region_color = QColor(255, 0, 0, 80)  # Semi-transparent red
        self.boundary_circle_color = QColor(255, 0, 0)  # Red boundary circles
        self.waypoint_color = QColor(0, 255, 0)  # Green waypoint dots
        self.temporary_waypoint_color = QColor(255, 255, 0)  # Yellow for temporary waypoint
        self.waypoint_line_color = QColor(0, 200, 0)  # Green lines between waypoints
        self.temporary_line_color = QColor(255, 255, 0)  # Yellow line to temporary waypoint
        self.selected_waypoint_color = QColor(0, 255, 255)  # Cyan for selected waypoint
        
        # Ellipse settings
        self.show_ellipse = True
        self.show_excluded_regions = True
        self.show_boundary_circles = True
        
        # Waypoint storage
        self.waypoints = []  # List of (x, y) tuples for committed waypoint coordinates
        self.temporary_waypoint = None  # Temporary waypoint (x, y) before it's committed
        self.waypoint_radius = 5  # Radius of waypoint dots in pixels
        self.selected_waypoint_index = None  # Index of selected waypoint for highlighting
        
        # Cursor tracking
        self.cursor_x = None
        self.cursor_y = None
        self.show_cursor_coords = False
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
        # Minimum widget size
        self.setMinimumSize(160, 160)
    
    def paintEvent(self, event):
        """Draw the coordinate system"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.bg_color)
        
        # Draw grid
        if self.show_grid:
            self._draw_grid(painter)
        
        # Draw axes
        if self.show_axes:
            self._draw_axes(painter)
        
        # Draw ticks and labels
        if self.show_ticks:
            self._draw_ticks(painter)
        
        if self.show_labels:
            self._draw_labels(painter)
        
        # Draw ellipse
        if self.show_ellipse:
            self._draw_ellipse(painter)
        
        # Draw excluded regions (inside Rmin and outside Rmax)
        if self.show_excluded_regions:
            self._draw_excluded_regions(painter)
        
        # Draw boundary circles at Rmin and Rmax
        if self.show_boundary_circles:
            self._draw_boundary_circles(painter)
        
        # Draw waypoints
        self._draw_waypoints(painter)
        
        # Draw border
        self._draw_border(painter)
        
        # Draw cursor coordinates if hovering
        if self.show_cursor_coords and self.cursor_x is not None and self.cursor_y is not None:
            self._draw_cursor_label(painter)
    
    def _draw_grid(self, painter):
        """Draw the background grid"""
        painter.setPen(QPen(self.grid_color, 1, Qt.SolidLine))
        
        # Calculate grid spacing
        grid_x_spacing = self._calculate_grid_spacing(self.view_xmin, self.view_xmax)
        grid_y_spacing = self._calculate_grid_spacing(self.view_ymin, self.view_ymax)
        
        # Draw vertical grid lines
        x = math.ceil(self.view_xmin / grid_x_spacing) * grid_x_spacing
        while x <= self.view_xmax:
            px = self._to_pixel_x(x)
            painter.drawLine(int(px), 0, int(px), self.height())
            x += grid_x_spacing
        
        # Draw horizontal grid lines
        y = math.ceil(self.view_ymin / grid_y_spacing) * grid_y_spacing
        while y <= self.view_ymax:
            py = self._to_pixel_y(y)
            painter.drawLine(0, int(py), self.width(), int(py))
            y += grid_y_spacing
    
    def _draw_axes(self, painter):
        """Draw X and Y axes"""
        painter.setPen(QPen(self.axis_color, 2, Qt.SolidLine))
        
        # Draw Y-axis (vertical line at x=0)
        if self.view_xmin <= 0 <= self.view_xmax:
            px = self._to_pixel_x(0)
            painter.drawLine(int(px), 0, int(px), self.height())
        
        # Draw X-axis (horizontal line at y=0)
        if self.view_ymin <= 0 <= self.view_ymax:
            py = self._to_pixel_y(0)
            painter.drawLine(0, int(py), self.width(), int(py))
    
    def _draw_ticks(self, painter):
        """Draw tick marks on the axes"""
        painter.setPen(QPen(self.tick_color, 1, Qt.SolidLine))
        
        tick_length = 3  # Smaller ticks for compact view
        
        # Calculate tick spacing - match grid spacing
        tick_x_spacing = self._calculate_grid_spacing(self.view_xmin, self.view_xmax)
        tick_y_spacing = self._calculate_grid_spacing(self.view_ymin, self.view_ymax)
        
        # Only draw ticks if widget is large enough
        if self.width() < 100 or self.height() < 100:
            return
        
        # Draw X-axis ticks (if y=0 is visible)
        if self.view_ymin <= 0 <= self.view_ymax:
            py = self._to_pixel_y(0)
            x = math.ceil(self.view_xmin / tick_x_spacing) * tick_x_spacing
            while x <= self.view_xmax:
                if abs(x) > 1e-10:  # Skip origin
                    px = self._to_pixel_x(x)
                    painter.drawLine(int(px), int(py - tick_length), int(px), int(py + tick_length))
                x += tick_x_spacing
        
        # Draw Y-axis ticks (if x=0 is visible)
        if self.view_xmin <= 0 <= self.view_xmax:
            px = self._to_pixel_x(0)
            y = math.ceil(self.view_ymin / tick_y_spacing) * tick_y_spacing
            while y <= self.view_ymax:
                if abs(y) > 1e-10:  # Skip origin
                    py = self._to_pixel_y(y)
                    painter.drawLine(int(px - tick_length), int(py), int(px + tick_length), int(py))
                y += tick_y_spacing
    
    def _draw_ellipse(self, painter):
        """Draw an ellipse with center at origin, radius xmax on x-axis, and radius ymax on y-axis"""
        painter.setPen(QPen(self.ellipse_color, 2, Qt.SolidLine))
        
        # Center of the ellipse at origin (0, 0)
        center_x = 0
        center_y = 0
        
        # Radii from the initial bounds
        radius_x = self.xmax
        radius_y = self.ymax
        
        # Convert center to pixel coordinates
        center_px = self._to_pixel_x(center_x)
        center_py = self._to_pixel_y(center_y)
        
        # Convert radii to pixel sizes
        # Calculate width and height in pixels
        width_pixels = abs(self._to_pixel_x(radius_x) - self._to_pixel_x(0)) * 2
        height_pixels = abs(self._to_pixel_y(0) - self._to_pixel_y(radius_y)) * 2
        
        # Draw the ellipse
        # drawEllipse takes top-left corner, width, and height
        top_left_x = center_px - width_pixels / 2
        top_left_y = center_py - height_pixels / 2
        
        painter.drawEllipse(
            int(top_left_x),
            int(top_left_y),
            int(width_pixels),
            int(height_pixels)
        )
    
    def _draw_excluded_regions(self, painter):
        """Draw semi-transparent red regions inside Rmin and outside Rmax"""
        from PySide6.QtGui import QPainterPath
        
        # Center at origin (0, 0)
        center_x = 0
        center_y = 0
        center_px = self._to_pixel_x(center_x)
        center_py = self._to_pixel_y(center_y)
        
        # Calculate radii in pixels
        rmin_radius_x = abs(self._to_pixel_x(self.Rmin) - self._to_pixel_x(0))
        rmin_radius_y = abs(self._to_pixel_y(0) - self._to_pixel_y(self.Rmin))
        rmax_radius_x = abs(self._to_pixel_x(self.Rmax) - self._to_pixel_x(0))
        rmax_radius_y = abs(self._to_pixel_y(0) - self._to_pixel_y(self.Rmax))
        
        # Set up painter for excluded regions
        painter.setPen(Qt.NoPen)
        painter.setBrush(self.excluded_region_color)
        
        # Draw outer region (outside Rmax)
        outer_path = QPainterPath()
        
        # Add the whole widget area
        outer_path.addRect(0, 0, self.width(), self.height())
        
        # Subtract the Rmax circle (this creates the outer excluded region)
        rmax_circle = QPainterPath()
        rmax_circle.addEllipse(
            int(center_px - rmax_radius_x),
            int(center_py - rmax_radius_y),
            int(rmax_radius_x * 2),
            int(rmax_radius_y * 2)
        )
        outer_region = outer_path.subtracted(rmax_circle)
        
        # Draw the outer region
        painter.drawPath(outer_region)
        
        # Draw inner circle (inside Rmin)
        inner_circle = QPainterPath()
        inner_circle.addEllipse(
            int(center_px - rmin_radius_x),
            int(center_py - rmin_radius_y),
            int(rmin_radius_x * 2),
            int(rmin_radius_y * 2)
        )
        painter.drawPath(inner_circle)
        
        # Reset brush to avoid affecting subsequent drawings
        painter.setBrush(Qt.NoBrush)
    
    def _draw_boundary_circles(self, painter):
        """Draw red circles at Rmin and Rmax radii"""
        painter.setPen(QPen(self.boundary_circle_color, 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        
        # Center at origin (0, 0)
        center_x = 0
        center_y = 0
        center_px = self._to_pixel_x(center_x)
        center_py = self._to_pixel_y(center_y)
        
        # Calculate radii in pixels
        rmin_radius_x = abs(self._to_pixel_x(self.Rmin) - self._to_pixel_x(0))
        rmin_radius_y = abs(self._to_pixel_y(0) - self._to_pixel_y(self.Rmin))
        rmax_radius_x = abs(self._to_pixel_x(self.Rmax) - self._to_pixel_x(0))
        rmax_radius_y = abs(self._to_pixel_y(0) - self._to_pixel_y(self.Rmax))
        
        # Draw Rmin circle
        painter.drawEllipse(
            int(center_px - rmin_radius_x),
            int(center_py - rmin_radius_y),
            int(rmin_radius_x * 2),
            int(rmin_radius_y * 2)
        )
        
        # Draw Rmax circle
        painter.drawEllipse(
            int(center_px - rmax_radius_x),
            int(center_py - rmax_radius_y),
            int(rmax_radius_x * 2),
            int(rmax_radius_y * 2)
        )
    
    def _draw_waypoints(self, painter):
        """Draw waypoint dots and lines on the graph"""
        # Draw lines between committed waypoints
        if len(self.waypoints) > 1:
            painter.setPen(QPen(self.waypoint_line_color, 2, Qt.SolidLine))
            for i in range(len(self.waypoints) - 1):
                x1, y1 = self.waypoints[i]
                x2, y2 = self.waypoints[i + 1]
                
                px1 = self._to_pixel_x(x1)
                py1 = self._to_pixel_y(y1)
                px2 = self._to_pixel_x(x2)
                py2 = self._to_pixel_y(y2)
                
                painter.drawLine(int(px1), int(py1), int(px2), int(py2))
        
        # Draw temporary yellow line from last committed waypoint to temporary waypoint
        if self.temporary_waypoint is not None and len(self.waypoints) > 0:
            painter.setPen(QPen(self.temporary_line_color, 2, Qt.DashLine))
            
            # Get last committed waypoint
            last_x, last_y = self.waypoints[-1]
            temp_x, temp_y = self.temporary_waypoint
            
            px1 = self._to_pixel_x(last_x)
            py1 = self._to_pixel_y(last_y)
            px2 = self._to_pixel_x(temp_x)
            py2 = self._to_pixel_y(temp_y)
            
            painter.drawLine(int(px1), int(py1), int(px2), int(py2))
        
        # Draw committed waypoint dots
        for i, (x, y) in enumerate(self.waypoints):
            # Check if this waypoint is selected
            if i == self.selected_waypoint_index:
                painter.setPen(QPen(self.selected_waypoint_color, 3, Qt.SolidLine))
                painter.setBrush(self.selected_waypoint_color)
            else:
                painter.setPen(QPen(self.waypoint_color, 2, Qt.SolidLine))
                painter.setBrush(self.waypoint_color)
            
            # Convert coordinates to pixels
            px = self._to_pixel_x(x)
            py = self._to_pixel_y(y)
            
            # Draw a filled circle for the waypoint
            painter.drawEllipse(
                int(px - self.waypoint_radius),
                int(py - self.waypoint_radius),
                self.waypoint_radius * 2,
                self.waypoint_radius * 2
            )
        
        # Draw temporary waypoint (if exists) in different color
        if self.temporary_waypoint is not None:
            painter.setPen(QPen(self.temporary_waypoint_color, 2, Qt.SolidLine))
            painter.setBrush(self.temporary_waypoint_color)
            
            x, y = self.temporary_waypoint
            px = self._to_pixel_x(x)
            py = self._to_pixel_y(y)
            
            # Draw a filled circle for the temporary waypoint
            painter.drawEllipse(
                int(px - self.waypoint_radius),
                int(py - self.waypoint_radius),
                self.waypoint_radius * 2,
                self.waypoint_radius * 2
            )
    
    def add_temporary_waypoint(self, x, y):
        """Add or replace a temporary waypoint on the graph (yellow dot)"""
        self.temporary_waypoint = (x, y)
        self.update()  # Trigger repaint
    
    def remove_temporary_waypoint(self, x, y):
        """Remove the temporary waypoint from the graph"""
        self.temporary_waypoint = None
        self.update()  # Trigger repaint
    
    def commit_temporary_waypoint(self):
        """Commit the temporary waypoint to the permanent waypoints list (green dot)"""
        if self.temporary_waypoint is not None:
            self.waypoints.append(self.temporary_waypoint)
            self.temporary_waypoint = None
            self.update()  # Trigger repaint
    
    def add_waypoint(self, x, y):
        """Add a waypoint directly to the permanent list (for backwards compatibility)"""
        self.waypoints.append((x, y))
        self.update()  # Trigger repaint
    
    def remove_waypoint(self, x, y):
        """Remove a waypoint from the graph"""
        # Find and remove the waypoint (with some tolerance for floating point comparison)
        tolerance = 0.1
        self.waypoints = [(wx, wy) for wx, wy in self.waypoints 
                         if not (abs(wx - x) < tolerance and abs(wy - y) < tolerance)]
        self.update()  # Trigger repaint
    
    def clear_waypoints(self):
        """Clear all waypoints from the graph"""
        self.waypoints.clear()
        self.temporary_waypoint = None
        self.update()  # Trigger repaint
    
    def set_selected_waypoint(self, index):
        """Set the selected waypoint index for highlighting"""
        self.selected_waypoint_index = index
        self.update()  # Trigger repaint
    
    def _draw_border(self, painter):
        """Draw border around the widget"""
        painter.setPen(QPen(self.border_color, 2, Qt.SolidLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(1, 1, self.width() - 2, self.height() - 2)
    
    def _draw_cursor_label(self, painter):
        """Draw floating label with cursor coordinates"""
        # Format the coordinates
        coord_text = f"({self.cursor_x:.1f}, {self.cursor_y:.1f})"
        
        # Set up font and calculate text size
        font = QFont("Arial", 8, QFont.Bold)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        text_width = metrics.horizontalAdvance(coord_text)
        text_height = metrics.height()
        
        # Add padding
        padding = 4
        label_width = text_width + 2 * padding
        label_height = text_height + 2 * padding
        
        # Get cursor pixel position
        cursor_px = self._to_pixel_x(self.cursor_x)
        cursor_py = self._to_pixel_y(self.cursor_y)
        
        # Position label near cursor, but keep it inside widget bounds
        offset_x = 10
        offset_y = -20
        label_x = cursor_px + offset_x
        label_y = cursor_py + offset_y
        
        # Keep label inside widget
        if label_x + label_width > self.width() - 5:
            label_x = cursor_px - label_width - offset_x
        if label_y < 5:
            label_y = cursor_py + 25
        if label_y + label_height > self.height() - 5:
            label_y = self.height() - label_height - 5
        
        # Draw background with border
        painter.setPen(QPen(self.cursor_label_border, 1, Qt.SolidLine))
        painter.setBrush(self.cursor_label_bg)
        painter.drawRoundedRect(int(label_x), int(label_y), label_width, label_height, 3, 3)
        
        # Draw text
        painter.setPen(QPen(self.label_color, 1, Qt.SolidLine))
        painter.drawText(int(label_x + padding), int(label_y + padding + metrics.ascent()), coord_text)
    
    def _draw_labels(self, painter):
        """Draw numeric labels on the axes"""
        painter.setPen(QPen(self.label_color, 1, Qt.SolidLine))
        font = QFont("Arial", 7)  # Smaller font for compact view
        painter.setFont(font)
        
        # Calculate label spacing - use 2x grid spacing to reduce label density
        label_x_spacing = self._calculate_grid_spacing(self.view_xmin, self.view_xmax) * 2
        label_y_spacing = self._calculate_grid_spacing(self.view_ymin, self.view_ymax) * 2
        
        # Minimum pixel spacing between labels to avoid overlap
        min_pixel_spacing = 30
        
        # Draw X-axis labels (only if there's enough space)
        if self.view_ymin <= 0 <= self.view_ymax and self.height() > 80:
            py = self._to_pixel_y(0)
            x = math.ceil(self.view_xmin / label_x_spacing) * label_x_spacing
            last_px = None
            while x <= self.view_xmax:
                if abs(x) > 1e-10:  # Skip origin
                    px = self._to_pixel_x(x)
                    # Check spacing from last label
                    if last_px is None or abs(px - last_px) >= min_pixel_spacing:
                        label = self._format_label(x)
                        # Position label below the axis
                        label_y = min(py + 12, self.height() - 5)
                        painter.drawText(int(px - 15), int(label_y), 30, 15, 
                                       Qt.AlignCenter, label)
                        last_px = px
                x += label_x_spacing
        
        # Draw Y-axis labels (only if there's enough space)
        if self.view_xmin <= 0 <= self.view_xmax and self.width() > 80:
            px = self._to_pixel_x(0)
            y = math.ceil(self.view_ymin / label_y_spacing) * label_y_spacing
            last_py = None
            while y <= self.view_ymax:
                if abs(y) > 1e-10:  # Skip origin
                    py = self._to_pixel_y(y)
                    # Check spacing from last label
                    if last_py is None or abs(py - last_py) >= min_pixel_spacing:
                        label = self._format_label(y)
                        # Position label to the right of the axis to avoid clutter
                        label_x = min(px + 3, self.width() - 30)
                        painter.drawText(int(label_x), int(py - 7), 28, 14, 
                                       Qt.AlignLeft, label)
                        last_py = py
                y += label_y_spacing
        
        # Draw origin label (only if widget is large enough)
        if self.view_xmin <= 0 <= self.view_xmax and self.view_ymin <= 0 <= self.view_ymax and self.width() > 60 and self.height() > 60:
            px = self._to_pixel_x(0)
            py = self._to_pixel_y(0)
            painter.drawText(int(px + 2), int(py + 10), 15, 12, 
                           Qt.AlignLeft, "0")
    
    def _calculate_grid_spacing(self, min_val, max_val):
        """Calculate appropriate grid spacing based on the view range"""
        range_val = max_val - min_val
        
        # Target: approximately 4-6 grid lines for compact view
        raw_spacing = range_val / 5
        
        # Round to a "nice" number (1, 2, 5, 10, 20, 50, 100, etc.)
        magnitude = 10 ** math.floor(math.log10(raw_spacing))
        normalized = raw_spacing / magnitude
        
        if normalized < 1.5:
            nice_spacing = 1 * magnitude
        elif normalized < 3:
            nice_spacing = 2 * magnitude
        elif normalized < 7:
            nice_spacing = 5 * magnitude
        else:
            nice_spacing = 10 * magnitude
        
        return nice_spacing
    
    def _format_label(self, value):
        """Format a numeric value for display as a label"""
        if abs(value) < 1e-10:
            return "0"
        elif abs(value) >= 10000:
            # Use 'k' notation for thousands
            return f"{int(value/1000)}k"
        elif abs(value) >= 1000:
            return f"{value/1000:.1f}k"
        elif abs(value) < 0.01 and abs(value) > 1e-10:
            return f"{value:.1e}"
        elif abs(value - round(value)) < 1e-10:
            return f"{int(round(value))}"
        else:
            return f"{value:.0f}"
    
    def _to_pixel_x(self, x):
        """Convert coordinate X to pixel X"""
        return (x - self.view_xmin) / (self.view_xmax - self.view_xmin) * self.width()
    
    def _to_pixel_y(self, y):
        """Convert coordinate Y to pixel Y (inverted because screen Y goes down)"""
        return (self.view_ymax - y) / (self.view_ymax - self.view_ymin) * self.height()
    
    def _to_coord_x(self, px):
        """Convert pixel X to coordinate X"""
        return self.view_xmin + (px / self.width()) * (self.view_xmax - self.view_xmin)
    
    def _to_coord_y(self, py):
        """Convert pixel Y to coordinate Y (inverted because screen Y goes down)"""
        return self.view_ymax - (py / self.height()) * (self.view_ymax - self.view_ymin)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming"""
        # Get zoom factor
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        
        # Get mouse position in coordinates
        mouse_x = self._to_coord_x(event.position().x())
        mouse_y = self._to_coord_y(event.position().y())
        
        # Calculate new view bounds (zoom centered on mouse)
        x_range = self.view_xmax - self.view_xmin
        y_range = self.view_ymax - self.view_ymin
        
        new_x_range = x_range * zoom_factor
        new_y_range = y_range * zoom_factor
        
        # Calculate how much of the range is on each side of the mouse
        left_ratio = (mouse_x - self.view_xmin) / x_range
        right_ratio = (self.view_xmax - mouse_x) / x_range
        top_ratio = (self.view_ymax - mouse_y) / y_range
        bottom_ratio = (mouse_y - self.view_ymin) / y_range
        
        # Apply zoom
        self.view_xmin = mouse_x - new_x_range * left_ratio
        self.view_xmax = mouse_x + new_x_range * right_ratio
        self.view_ymin = mouse_y - new_y_range * bottom_ratio
        self.view_ymax = mouse_y + new_y_range * top_ratio
        
        self.update()
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning"""
        if event.button() == Qt.RightButton:
            self.is_panning = True
            self.last_pan_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning and cursor tracking"""
        # Update cursor coordinates
        self.cursor_x = self._to_coord_x(event.position().x())
        self.cursor_y = self._to_coord_y(event.position().y())
        self.show_cursor_coords = True
        
        if self.is_panning and self.last_pan_pos is not None:
            # Calculate delta in pixels
            delta_px = event.position() - self.last_pan_pos
            
            # Convert to coordinate delta
            delta_x = -delta_px.x() / self.width() * (self.view_xmax - self.view_xmin)
            delta_y = delta_px.y() / self.height() * (self.view_ymax - self.view_ymin)
            
            # Update view bounds
            self.view_xmin += delta_x
            self.view_xmax += delta_x
            self.view_ymin += delta_y
            self.view_ymax += delta_y
            
            self.last_pan_pos = event.position()
        
        self.update()
        event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.RightButton:
            self.is_panning = False
            self.last_pan_pos = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        elif event.button() == Qt.LeftButton:
            # Emit coordinates at click position for left click
            coord_x = self._to_coord_x(event.position().x())
            coord_y = self._to_coord_y(event.position().y())
            self.coordinatesChanged.emit(coord_x, coord_y)
            event.accept()
    
    def leaveEvent(self, event):
        """Handle mouse leaving the widget"""
        self.show_cursor_coords = False
        self.update()
        super().leaveEvent(event)
    
    def reset_view(self):
        """Reset the view to the original bounds"""
        self.view_xmin = self.xmin
        self.view_xmax = self.xmax
        self.view_ymin = self.ymin
        self.view_ymax = self.ymax
        self.update()
    
    def set_bounds(self, xmin, xmax, ymin, ymax):
        """Set new coordinate bounds"""
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.reset_view()
    
    def toggle_grid(self, show=None):
        """Toggle grid visibility"""
        if show is None:
            self.show_grid = not self.show_grid
        else:
            self.show_grid = show
        self.update()
    
    def toggle_axes(self, show=None):
        """Toggle axes visibility"""
        if show is None:
            self.show_axes = not self.show_axes
        else:
            self.show_axes = show
        self.update()
    
    def toggle_labels(self, show=None):
        """Toggle label visibility"""
        if show is None:
            self.show_labels = not self.show_labels
        else:
            self.show_labels = show
        self.update()
    
    def toggle_ellipse(self, show=None):
        """Toggle ellipse visibility"""
        if show is None:
            self.show_ellipse = not self.show_ellipse
        else:
            self.show_ellipse = show
        self.update()
    
    def toggle_excluded_regions(self, show=None):
        """Toggle excluded regions visibility"""
        if show is None:
            self.show_excluded_regions = not self.show_excluded_regions
        else:
            self.show_excluded_regions = show
        self.update()
    
    def toggle_boundary_circles(self, show=None):
        """Toggle boundary circles visibility"""
        if show is None:
            self.show_boundary_circles = not self.show_boundary_circles
        else:
            self.show_boundary_circles = show
        self.update()
    
    def set_radius_bounds(self, Rmin, Rmax):
        """Set new radius bounds for the stripe region"""
        self.Rmin = Rmin
        self.Rmax = Rmax
        self.update()

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    widget = CoordinateSystemWidget()
    widget.resize(600, 600)
    widget.show()
    sys.exit(app.exec())