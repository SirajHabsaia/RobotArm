from PySide6.QtWidgets import QWidget, QLabel, QLineEdit, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
import math

class RingSlider(QWidget):
    valueChanged = Signal(float)
    labelChanged = Signal(str)

    def __init__(self, min_angle=135, max_angle=405, min_value=0, max_value=100, label="θ", value=None, parent=None):
        super().__init__(parent)
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_value = min_value
        self.max_value = max_value
        self._value = min_value if value is None else value
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
        value = max(self.min_value, min(self.max_value, value))
        if value != self._value:
            self._value = value
            self.valueChanged.emit(self._value)
            self.value_edit.setText(f"{self._value:.1f}")
            self.update()

    def value(self):
        return self._value

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

        # Draw knob
        knob_angle = math.radians(self.angle_for_value(self._value))
        knob_x = center.x() + radius * math.cos(knob_angle)
        knob_y = center.y() - radius * math.sin(knob_angle)
        painter.setBrush(QBrush(QColor(70, 130, 180)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(knob_x, knob_y), 7, 7)

        # Center the group widget
        group_width = self.center_group.sizeHint().width()
        group_height = self.center_group.sizeHint().height()
        group_x = int(center.x() - group_width / 2)
        group_y = int(center.y() - group_height / 2)
        self.center_group.setGeometry(group_x, group_y, group_width, group_height)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self.set_slider_value_from_pos(event.position())
        elif event.button() == Qt.RightButton:
            # Enable editing of value
            self.value_edit.setReadOnly(False)
            self.value_edit.setFocus()
            self.value_edit.selectAll()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self.set_slider_value_from_pos(event.position())

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def set_slider_value_from_pos(self, pos):
        rect = self.rect()
        size = min(rect.width(), rect.height())
        margin = 8  # Updated to match paintEvent
        center = QPointF(rect.width()/2, rect.height()/2)
        dx = pos.x() - center.x()
        dy = center.y() - pos.y()
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        # Clamp angle to slider range
        if self.min_angle <= angle <= self.max_angle:
            value = self.value_for_angle(angle)
            self.setValue(value)

    def wheelEvent(self, event):
        # Each wheel step is 120 units; one step = 1 degree
        angle_step = 1
        self._wheel_delta_accum += event.angleDelta().y()
        num_steps = int(self._wheel_delta_accum // 120)
        if num_steps != 0:
            self._wheel_delta_accum -= num_steps * 120
            current_angle = self.angle_for_value(self._value)
            new_angle = current_angle + angle_step * num_steps
            new_angle = max(self.min_angle, min(self.max_angle, new_angle))
            new_value = self.value_for_angle(new_angle)
            self.setValue(new_value)
            event.accept()
        else:
            event.ignore()

    def sizeHint(self):
        return self.minimumSize()

    def _on_value_edit(self):
        text = self.value_edit.text()
        try:
            val = float(text)
            if self.min_value <= val <= self.max_value:
                self.setValue(val)
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