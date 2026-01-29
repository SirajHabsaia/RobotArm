from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
import math

class RingSlider(QWidget):
    """
    Ring slider widget with dual-knob feedback system.
    
    - Blue knob: Current actual value (from Arduino feedback)
    - Green knob: Target value (from user input)
    
    User interactions (click, drag, scroll, text input) set the target value (green knob).
    Arduino feedback updates the current value (blue knob) via setValue().
    As the robot moves, the blue knob gradually approaches the green target.
    """
    valueChanged = Signal(float)
    labelChanged = Signal(str)

    def __init__(self, min_angle=135, max_angle=405, min_value=0, max_value=100, label="θ", value=None, use_target=True, parent=None):
        super().__init__(parent)
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_value = min_value
        self.max_value = max_value
        self.prohibited_start = -1  # Start angle of prohibited zone 1 (-1 means disabled)
        self.prohibited_end = -1    # End angle of prohibited zone 1 (-1 means disabled)
        self.prohibited_start2 = -1  # Start angle of prohibited zone 2 (-1 means disabled)
        self.prohibited_end2 = -1    # End angle of prohibited zone 2 (-1 means disabled)
        self._value = min_value if value is None else value
        self._target_value = None  # Target value set by user (None means no target)
        self._hover_value = None  # Value that mouse is hovering over (None means no hover)
        self.use_target = use_target  # Whether to use two-knob target system
        self.setMinimumSize(80, 80)
        self._dragging = False
        self._wheel_delta_accum = 0  # Accumulate wheel deltas for smooth scrolling

        # Create label and value widgets
        self.label = QLabel(label, self)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 11pt; background: transparent;")
        self.value_edit = QLineEdit(f"{self._value:.1f}", self)
        self.value_edit.setAlignment(Qt.AlignCenter)
        self.value_edit.setStyleSheet("color: white; font-size: 9pt; background: transparent; border: none;")
        self.value_edit.setReadOnly(True)
        self.value_edit.setFixedWidth(40)
        self.value_edit.setFixedHeight(18)

        # Group label and value in a transparent widget
        self.center_group = QWidget(self)
        self.center_group.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.center_group.setStyleSheet("background: transparent;")
        self.center_layout = QVBoxLayout(self.center_group)
        self.center_layout.setSpacing(0)  # Reduced from 3 to 1
        self.center_layout.setContentsMargins(0, 0, 0, 0)
        self.center_layout.addWidget(self.label)
        self.center_layout.addWidget(self.value_edit)

        # Connect signals
        self.value_edit.editingFinished.connect(self._on_value_edit)

    def setValue(self, value):
        """Set current value (blue knob) - typically from feedback."""
        value = max(self.min_value, min(self.max_value, value))
        if value != self._value:
            self._value = value
            self.value_edit.setText(f"{self._value:.1f}")
            # Emit signal if not using target system (direct control)
            if not self.use_target:
                self.valueChanged.emit(self._value)
            self.update()

    def setTargetValue(self, value):
        """Set target value (green knob) - from user input."""
        if not self.use_target:
            # If target system is disabled, directly set value instead
            self.setValue(value)
            self.valueChanged.emit(value)
            return
        
        value = max(self.min_value, min(self.max_value, value))
        if value != self._target_value:
            self._target_value = value
            self.valueChanged.emit(self._target_value)
            self.update()

    def clearTarget(self):
        """Clear the target value (remove green knob)."""
        self._target_value = None
        self.update()

    def value(self):
        return self._value
    
    def targetValue(self):
        return self._target_value

    def angle_for_value(self, value):
        # Map value to angle
        ratio = (value - self.min_value) / (self.max_value - self.min_value)
        return self.min_angle + ratio * (self.max_angle - self.min_angle)

    def value_for_angle(self, angle):
        # Map angle to value
        angle = max(self.min_angle, min(self.max_angle, angle))
        ratio = (angle - self.min_angle) / (self.max_angle - self.min_angle)
        return self.min_value + ratio * (self.max_value - self.min_value)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        size = min(rect.width(), rect.height())
        margin = 8
        ring_rect = QRectF(margin, margin, size - 2*margin, size - 2*margin)
        center = ring_rect.center()
        radius = ring_rect.width() / 2

        # Draw background ring
        pen = QPen(QColor(220, 220, 220), 8)
        painter.setPen(pen)
        painter.drawArc(ring_rect, int(self.min_angle*16), int((self.max_angle-self.min_angle)*16))

        # Draw active arc
        pen.setColor(QColor(70, 130, 180))
        painter.setPen(pen)
        angle_span = self.angle_for_value(self._value) - self.min_angle
        painter.drawArc(ring_rect, int(self.min_angle*16), int(angle_span*16))

        # Draw prohibited zones in red ON TOP (only if enabled)
        if self.prohibited_start >= 0 and self.prohibited_end >= 0:
            pen.setColor(QColor(220, 50, 50))  # Red color for prohibited zone
            painter.setPen(pen)
            prohibited_span = self.prohibited_end - self.prohibited_start
            painter.drawArc(ring_rect, int(self.prohibited_start*16), int(prohibited_span*16))
        
        # Draw second prohibited zone if enabled
        if self.prohibited_start2 >= 0 and self.prohibited_end2 >= 0:
            pen.setColor(QColor(220, 50, 50))  # Red color for prohibited zone
            painter.setPen(pen)
            prohibited_span2 = self.prohibited_end2 - self.prohibited_start2
            painter.drawArc(ring_rect, int(self.prohibited_start2*16), int(prohibited_span2*16))

        # Draw target value knob (green - user's desired position) if set and using target system
        if self.use_target and self._target_value is not None:
            target_angle = math.radians(self.angle_for_value(self._target_value))
            target_x = center.x() + radius * math.cos(target_angle)
            target_y = center.y() - radius * math.sin(target_angle)
            painter.setBrush(QBrush(QColor(50, 220, 80)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(target_x, target_y), 7, 7)

        # Draw current value knob (blue - actual position from feedback) on top
        knob_angle = math.radians(self.angle_for_value(self._value))
        knob_x = center.x() + radius * math.cos(knob_angle)
        knob_y = center.y() - radius * math.sin(knob_angle)
        painter.setBrush(QBrush(QColor(70, 130, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(knob_x, knob_y), 7, 7)

        # Draw hover preview knob (cyan) on top of everything if hovering
        if self._hover_value is not None:
            hover_angle = math.radians(self.angle_for_value(self._hover_value))
            hover_x = center.x() + radius * math.cos(hover_angle)
            hover_y = center.y() - radius * math.sin(hover_angle)
            painter.setBrush(QBrush(QColor(0, 255, 255)))  # Cyan
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(hover_x, hover_y), 6, 6)

        # Center the group widget
        group_width = self.center_group.sizeHint().width()
        group_height = self.center_group.sizeHint().height()
        group_x = int(center.x() - group_width / 2)
        group_y = int(center.y() - group_height / 2)
        self.center_group.setGeometry(group_x, group_y, group_width, group_height)

        painter.end()

    def _is_in_prohibited_zone(self, angle):
        """Check if an angle is in any prohibited zone."""
        if self.prohibited_start >= 0 and self.prohibited_end >= 0:
            if self.prohibited_start <= angle <= self.prohibited_end:
                return True
        
        if self.prohibited_start2 >= 0 and self.prohibited_end2 >= 0:
            if self.prohibited_start2 <= angle <= self.prohibited_end2:
                return True
        
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            # Use hover value if available, otherwise calculate from position
            if self._hover_value is not None:
                if self.use_target:
                    self.setTargetValue(self._hover_value)
                else:
                    self.setValue(self._hover_value)
                    self.valueChanged.emit(self._hover_value)
            else:
                self.set_slider_target_from_pos(event.position())
        elif event.button() == Qt.RightButton:
            # Enable editing of value
            self.value_edit.setReadOnly(False)
            self.value_edit.setFocus()
            self.value_edit.selectAll()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.set_slider_target_from_pos(event.position())
        else:
            # Update hover preview when not dragging
            self._update_hover_from_pos(event.position())

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def leaveEvent(self, event):
        """Clear hover preview when mouse leaves widget."""
        self._hover_value = None
        self.update()
        super().leaveEvent(event)

    def _update_hover_from_pos(self, pos):
        """Update hover value from mouse position, respecting prohibited zones."""
        rect = self.rect()
        center = QPointF(rect.width()/2, rect.height()/2)
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        
        # Check if angle is in slider range and not in prohibited zone
        if self.min_angle <= angle <= self.max_angle:
            if not self._is_in_prohibited_zone(angle):
                value = self.value_for_angle(angle)
                if value != self._hover_value:
                    self._hover_value = value
                    self.update()
                return
        
        # Invalid position - clear hover
        if self._hover_value is not None:
            self._hover_value = None
            self.update()

    def set_slider_target_from_pos(self, pos):
        """Set target value (green knob) from mouse position."""
        rect = self.rect()
        center = QPointF(rect.width()/2, rect.height()/2)
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        
        # Check if angle is in prohibited zones using shared method
        if self._is_in_prohibited_zone(angle):
            return
        
        # Clamp angle to slider range
        if self.min_angle <= angle <= self.max_angle:
            value = self.value_for_angle(angle)
            self.setTargetValue(value)

    def wheelEvent(self, event):
        """Wheel scrolling sets target value (green knob)."""
        # Each wheel step is 120 units; one step = 1 degree
        angle_step = 1
        self._wheel_delta_accum += event.angleDelta().y()
        num_steps = int(self._wheel_delta_accum // 120)
        if num_steps != 0:
            self._wheel_delta_accum -= num_steps * 120
            
            # Use target value if set, otherwise use current value
            base_value = self._target_value if self._target_value is not None else self._value
            current_angle = self.angle_for_value(base_value)
            new_angle = current_angle + angle_step * num_steps
            
            # Check if this is a 360-degree slider (0 to 360)
            is_360_slider = (self.min_angle == 0 and self.max_angle == 360)
            
            if is_360_slider:
                # Wrap around for 360-degree sliders
                if new_angle < self.min_angle:
                    new_angle = self.max_angle + (new_angle - self.min_angle)
                elif new_angle > self.max_angle:
                    new_angle = self.min_angle + (new_angle - self.max_angle)
            else:
                # Clamp to range for other sliders
                new_angle = max(self.min_angle, min(self.max_angle, new_angle))
            
            # Check if new angle would be in prohibited zones (only if enabled)
            if self.prohibited_start >= 0 and self.prohibited_end >= 0:
                if self.prohibited_start <= new_angle <= self.prohibited_end:
                    # Don't change value if it would enter prohibited zone
                    event.accept()
                    return
            
            if self.prohibited_start2 >= 0 and self.prohibited_end2 >= 0:
                if self.prohibited_start2 <= new_angle <= self.prohibited_end2:
                    # Don't change value if it would enter prohibited zone
                    event.accept()
                    return
            
            new_value = self.value_for_angle(new_angle)
            self.setTargetValue(new_value)
            event.accept()
        else:
            event.ignore()

    def sizeHint(self):
        return self.minimumSize()

    def _on_value_edit(self):
        """Manual text input sets target value (green knob)."""
        text = self.value_edit.text()
        try:
            val = float(text)
            
            # Check if this is a 360-degree slider (0 to 360)
            is_360_slider = (self.min_angle == 0 and self.max_angle == 360 and 
                           self.min_value == 0 and self.max_value == 360)
            
            if is_360_slider:
                # Normalize to 0-360 range
                val = val % 360
                if val < 0:
                    val += 360
                self.setTargetValue(val)
            elif self.min_value <= val <= self.max_value:
                self.setTargetValue(val)
            else:
                self.value_edit.setText(f"{self._value:.1f}")
        except ValueError:
            self.value_edit.setText(f"{self._value:.1f}")
        self.value_edit.setReadOnly(True)

if __name__ == "__main__":
    app = QApplication([])

    window = QWidget()
    layout = QVBoxLayout(window)

    slider = RingSlider(label="a", min_value=60, max_value=300, min_angle=60, max_angle=300)

    layout.addWidget(slider)

    window.show()
    app.exec()