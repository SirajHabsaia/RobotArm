from Designer.ui_gui import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog
from PySide6.QtCore import Qt, QPoint, QRect, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from home import AspectRatioLabel
from ThreeD import RobotVTKWidget
from ring_slider import RingSlider
from graph import CoordinateSystemWidget
from pathlib import Path
import json
import math
import serial
import serial.tools.list_ports
import numpy as np
from kinematics import direct_kinematics

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Interface graphique")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
        self.icon_name_widget.setHidden(True)
        self.execWidget.setHidden(True)
        self.importBtn.setHidden(True)
        self.fileLabel.setHidden(True)
        
        # Load parameters from JSON
        self._load_parameters()
        
        # Replace renderLabel with AspectRatioLabel to preserve aspect ratio
        self._replace_with_aspect_ratio_label()
        
        # Setup Cartesian sliders with parameters from JSON
        self._setup_cartesian_sliders()
        
        # Setup Program page sliders
        self._setup_program_sliders()
        
        # Setup ring sliders for polar coordinates
        self._setup_ring_sliders()
        
        # Create the 3D robot viewer (only once)
        self.robot_viewer = None
        self._setup_3d_viewer()
        
        # Setup the 2D coordinate system widget
        self._setup_coordinate_system()

        self.HomeBtn1.clicked.connect(lambda: self.switch_menu(0))
        self.HomeBtn2.clicked.connect(lambda: self.switch_menu(0))
        self.ManipBtn1.clicked.connect(lambda: self.switch_menu(1))
        self.ManipBtn2.clicked.connect(lambda: self.switch_menu(1))
        self.ProgramBtn1.clicked.connect(lambda: self.switch_menu(2))
        self.ProgramBtn2.clicked.connect(lambda: self.switch_menu(2))
        self.DrawBtn1.clicked.connect(lambda: self.switch_menu(3))
        self.DrawBtn2.clicked.connect(lambda: self.switch_menu(3))
        self.ChessBtn1.clicked.connect(lambda: self.switch_menu(4))
        self.ChessBtn2.clicked.connect(lambda: self.switch_menu(4))
        self.GithubBtn1.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/SirajHabsaia/RobotArm")))
        self.GithubBtn2.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/SirajHabsaia/RobotArm")))

        self.MaximizeBtn.clicked.connect(self.toggle_window)

        # Enable dragging from title_widget
        self._drag_pos = None
        self.title_widget.mousePressEvent = self.title_mousePressEvent
        self.title_widget.mouseMoveEvent = self.title_mouseMoveEvent
        self.title_widget.mouseReleaseEvent = self.title_mouseReleaseEvent
        
        # Enable window resizing
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geometry = None
        self._edge_margin = 5  # pixels from edge to trigger resize
        self._is_resizing = False
        self.setMouseTracking(True)
        self._enable_mouse_tracking(self.centralwidget)

        # Record - Exec
        self.record_mode = True

        self.recording_started = False
        self.recording_paused = False

        self.exec_started = False
        self.exec_paused = False
        
        self.file_loaded = False
        
        # Waypoint tracking
        self.waypoints = []  # List of tuples (x, y, z, mu, gripper)
        self.current_waypoint = None  # Temporary waypoint before adding to list (x, y)
        
        # Deadzone state tracking
        self._x_in_deadzone = False
        self._y_in_deadzone = False
        self.selected_waypoint_index = None  # Index of selected waypoint in list
        
        # Connect mode buttons
        self.recordBtn.clicked.connect(self._on_record_mode)
        self.execBtn.clicked.connect(self._on_exec_mode)
        
        # Connect recording control buttons
        self.startRecording.clicked.connect(self._on_start_recording)
        self.pauseRecording.clicked.connect(self._on_pause_recording)
        self.stopRecording.clicked.connect(self._on_stop_recording)
        self.addRecording.clicked.connect(self._on_add_waypoint)
        self.deleteRecording.clicked.connect(self._on_delete_waypoint)
        
        # Connect list widget selection to highlight waypoint
        self.positionlistWidget.itemSelectionChanged.connect(self._on_waypoint_selected)
        
        # Connect import button for Execute mode
        self.importBtn.clicked.connect(self._on_import_waypoints)
        
        # COM port management
        self.serial_connection = None
        self.connected_port = None
        
        # Connect COM widget buttons
        self.refreshBtn.clicked.connect(self._on_refresh_com_ports)
        self.connectBtn.clicked.connect(self._on_connect_com)
        self.disconnectBtn.clicked.connect(self._on_disconnect_com)
        self.quitBtn.clicked.connect(self._on_quit_app)
        
        # Initialize COM port list and button states
        self._on_refresh_com_ports()
        self._update_com_button_states()
        
        # Serial command debouncing - single-shot timer
        self.command_debounce_timer = QTimer()
        self.command_debounce_timer.setSingleShot(True)
        self.command_debounce_timer.setInterval(100)  # 100ms debounce
        self.command_debounce_timer.timeout.connect(self._send_ring_slider_command)
        
        # Store pending slider values
        self.pending_theta = None
        self.pending_alpha = None
        self.pending_beta = None
        
        # Serial reading timer for feedback
        self.serial_read_timer = QTimer()
        self.serial_read_timer.setInterval(20)  # Read every 20ms
        self.serial_read_timer.timeout.connect(self._read_serial_feedback)
        self.serial_buffer = ""  # Buffer for incomplete serial data
        
        # Current actual position from Arduino feedback
        self.current_x = 0.0
        self.current_y = 0.0
        self.current_z = 0.0
    
    def _load_parameters(self):
        """Load parameters from params.json"""
        params_path = Path(__file__).parent / "params.json"
        try:
            with open(params_path, 'r') as f:
                self.params = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading params.json: {e}")
            # Default parameters if file not found
            self.params = {
                "xmin": -350, "xmax": 350, "xdef": 0,
                "ymin": -350, "ymax": 350, "ydef": 0,
                "zmin": -350, "zmax": 350, "zdef": 0,
                "mumin": -90, "mumax": 30, "mudef": 0,
                "grippermin": 0, "grippermax": 180, "gripperdef": 90
            }
    
    def _setup_cartesian_sliders(self):
        """Setup Cartesian sliders with parameters from JSON and synchronize with line edits"""
        # X slider
        self.xSlider.setMinimum(-self.params["Rmax"])
        self.xSlider.setMaximum(self.params["Rmax"])
        self.xSlider.setValue(self.params["xdef"])
        self.xminLabel.setText(str(-self.params["Rmax"]))
        self.xmaxLabel.setText(str(self.params["Rmax"]))
        self.xlineEdit.setText(str(self.params["xdef"]))
        self.xLabel.setText(str(self.params["xdef"]))
        
        # Y slider
        self.ySlider.setMinimum(-self.params["Rmax"])
        self.ySlider.setMaximum(self.params["Rmax"])
        self.ySlider.setValue(self.params["ydef"])
        self.yminLabel.setText(str(-self.params["Rmax"]))
        self.ymaxLabel.setText(str(self.params["Rmax"]))
        self.ylineEdit.setText(str(self.params["ydef"]))
        self.yLabel.setText(str(self.params["ydef"]))
        
        # Z slider
        self.zSlider.setMinimum(self.params["zmin"])
        self.zSlider.setMaximum(self.params["zmax"])
        self.zSlider.setValue(self.params["zdef"])
        self.zminLabel.setText(str(self.params["zmin"]))
        self.zmaxLabel.setText(str(self.params["zmax"]))
        self.zlineEdit.setText(str(self.params["zdef"]))
        self.zLabel.setText(str(self.params["zdef"]))
        
        # Mu slider
        self.muSlider.setMinimum(self.params["mumin"])
        self.muSlider.setMaximum(self.params["mumax"])
        self.muSlider.setValue(self.params["mudef"])
        self.muminLabel.setText(str(self.params["mumin"]))
        self.mumaxLabel.setText(str(self.params["mumax"]))
        self.mulineEdit.setText(str(self.params["mudef"]))
        self.muLabel.setText(str(self.params["mudef"]))
        
        # Connect sliders to update lineEdit only (labels are updated from Arduino feedback)
        # X and Y sliders use special deadzone handling
        self.xSlider.valueChanged.connect(lambda v: self._update_xy_slider_lineedit(v, 'x'))
        self.ySlider.valueChanged.connect(lambda v: self._update_xy_slider_lineedit(v, 'y'))
        self.zSlider.valueChanged.connect(lambda v: self.zlineEdit.setText(str(v)))
        self.muSlider.valueChanged.connect(lambda v: self.mulineEdit.setText(str(v)))
        
        # Connect buttons to send cartesian commands
        self.xBtn.clicked.connect(lambda: self._send_single_cartesian_command('x'))
        self.yBtn.clicked.connect(lambda: self._send_single_cartesian_command('y'))
        self.zBtn.clicked.connect(lambda: self._send_single_cartesian_command('z'))
        self.muBtn.clicked.connect(lambda: self._send_single_cartesian_command('mu'))
        
        # Connect send all button
        self.sendallBtn.clicked.connect(self._send_all_cartesian_command)
        
        # Store last valid x,y values for deadzone handling
        self._last_valid_x = self.params["xdef"]
        self._last_valid_y = self.params["ydef"]
        
        # Store original slider stylesheets for restoring after deadzone
        self._x_slider_original_style = self.xSlider.styleSheet()
        self._y_slider_original_style = self.ySlider.styleSheet()
        
        # Default (normal) stylesheet for sliders
        self._normal_style = """
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #d0d0d0;
                border-radius: 3px;
            }

            QSlider::sub-page:horizontal {
                background:  #d0d0d0;
                border-radius: 3px;
            }

            QSlider::add-page:horizontal {
                background: #d0d0d0;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid  rgb(33, 100, 33);
                width: 5px;
                height: 5px;
                margin: -7px 0;       /* centers the handle */
                border-radius: 9px;
            }

            QSlider::handle:horizontal:hover {
                background: #e9f1ff;
                border-color: #1a73e8;
            }

            QSlider::handle:horizontal:pressed {
                background: #cfe0ff;
                border-color: #1a73e8;
            }
        """
        
        # Deadzone stylesheet (reddish)
        self._deadzone_style = """
            QSlider::groove:horizontal {
                border: none;
                height: 4px;
                background: #d0d0d0;
                border-radius: 3px;
            }

            QSlider::sub-page:horizontal {
                background: #ff9999;
                border-radius: 3px;
            }

            QSlider::add-page:horizontal {
                background: #ff9999;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid  rgb(33, 100, 33);
                width: 5px;
                height: 5px;
                margin: -7px 0;       /* centers the handle */
                border-radius: 9px;
            }

            QSlider::handle:horizontal:hover {
                background: #e9f1ff;
                border-color: #1a73e8;
            }

            QSlider::handle:horizontal:pressed {
                background: #cfe0ff;
                border-color: #1a73e8;
            }
        """
    
    def _setup_program_sliders(self):
        """Setup sliders and line edits for Program page"""
        # Z slider for Program page
        self.zSliderProgram.setMinimum(-self.params["Rmax"])
        self.zSliderProgram.setMaximum(self.params["Rmax"])
        self.zSliderProgram.setValue(self.params["zdef"])
        self.zLineEditProgram.setText(str(self.params["zdef"]))
        
        # Connect slider to update line edit when slider moves
        self.zSliderProgram.valueChanged.connect(lambda v: self._update_program_z_from_slider(v))
        
        # Connect line edit to update slider when Return key is pressed
        self.zLineEditProgram.returnPressed.connect(lambda: self._update_program_z_from_lineedit())
        
        # Mu slider for Program page
        self.muSliderProgram.setMinimum(self.params["mumin"])
        self.muSliderProgram.setMaximum(self.params["mumax"])
        self.muSliderProgram.setValue(self.params["mudef"])
        self.muLineEditProgram.setText(str(self.params["mudef"]))
        
        # Connect mu slider to update line edit when slider moves
        self.muSliderProgram.valueChanged.connect(lambda v: self._update_program_mu_from_slider(v))
        
        # Connect mu line edit to update slider when Return key is pressed
        self.muLineEditProgram.returnPressed.connect(lambda: self._update_program_mu_from_lineedit())
        
        # Gripper slider for Program page
        gripper_min = self.params.get("grippermin", 0)
        gripper_max = self.params.get("grippermax", 180)
        gripper_def = self.params.get("gripperdef", 90)
        
        self.gripperSliderProgram.setMinimum(gripper_min)
        self.gripperSliderProgram.setMaximum(gripper_max)
        self.gripperSliderProgram.setValue(gripper_def)
        self.gripperLineEditProgram.setText(str(gripper_def))
        
        # Connect gripper slider to update line edit when slider moves
        self.gripperSliderProgram.valueChanged.connect(lambda v: self._update_program_gripper_from_slider(v))
        
        # Connect gripper line edit to update slider when Return key is pressed
        self.gripperLineEditProgram.returnPressed.connect(lambda: self._update_program_gripper_from_lineedit())
    
    def _update_program_z_from_slider(self, value):
        """Update zLineEditProgram when zSliderProgram value changes"""
        self.zLineEditProgram.setText(str(value))
    
    def _update_program_z_from_lineedit(self):
        """Update zSliderProgram when zLineEditProgram value is entered"""
        try:
            value = int(self.zLineEditProgram.text())
            if -self.params["Rmax"] <= value <= self.params["Rmax"]:
                self.zSliderProgram.blockSignals(True)  # Prevent triggering slider's valueChanged
                self.zSliderProgram.setValue(value)
                self.zSliderProgram.blockSignals(False)
            else:
                # Value out of range, revert lineEdit to current slider value
                self.zLineEditProgram.setText(str(self.zSliderProgram.value()))
        except ValueError:
            # Invalid input, revert lineEdit to current slider value
            self.zLineEditProgram.setText(str(self.zSliderProgram.value()))
    
    def _update_program_mu_from_slider(self, value):
        """Update muLineEditProgram when muSliderProgram value changes"""
        self.muLineEditProgram.setText(str(value))
    
    def _update_program_mu_from_lineedit(self):
        """Update muSliderProgram when muLineEditProgram value is entered"""
        try:
            value = int(self.muLineEditProgram.text())
            if self.params["mumin"] <= value <= self.params["mumax"]:
                self.muSliderProgram.blockSignals(True)  # Prevent triggering slider's valueChanged
                self.muSliderProgram.setValue(value)
                self.muSliderProgram.blockSignals(False)
            else:
                # Value out of range, revert lineEdit to current slider value
                self.muLineEditProgram.setText(str(self.muSliderProgram.value()))
        except ValueError:
            # Invalid input, revert lineEdit to current slider value
            self.muLineEditProgram.setText(str(self.muSliderProgram.value()))
    
    def _update_program_gripper_from_slider(self, value):
        """Update gripperLineEditProgram when gripperSliderProgram value changes"""
        self.gripperLineEditProgram.setText(str(value))
    
    def _update_program_gripper_from_lineedit(self):
        """Update gripperSliderProgram when gripperLineEditProgram value is entered"""
        try:
            value = int(self.gripperLineEditProgram.text())
            gripper_min = self.params.get("grippermin", 0)
            gripper_max = self.params.get("grippermax", 180)
            if gripper_min <= value <= gripper_max:
                self.gripperSliderProgram.blockSignals(True)  # Prevent triggering slider's valueChanged
                self.gripperSliderProgram.setValue(value)
                self.gripperSliderProgram.blockSignals(False)
            else:
                # Value out of range, revert lineEdit to current slider value
                self.gripperLineEditProgram.setText(str(self.gripperSliderProgram.value()))
        except ValueError:
            # Invalid input, revert lineEdit to current slider value
            self.gripperLineEditProgram.setText(str(self.gripperSliderProgram.value()))
    
    def _update_xy_slider_lineedit(self, value, axis):
        """Update lineEdit when x or y slider moves, respecting Rmin deadzone (label updated from feedback)"""
        # Get current values and UI elements
        if axis == 'x':
            x = value
            y = self._last_valid_y
            lineedit = self.xlineEdit
            slider = self.xSlider
            other_slider = self.ySlider
        else:  # axis == 'y'
            x = self._last_valid_x
            y = value
            lineedit = self.ylineEdit
            slider = self.ySlider
            other_slider = self.xSlider
        
        # Calculate norm
        norm = math.sqrt(x**2 + y**2)
        
        # Determine if we're in deadzone
        in_deadzone = not (self.params["Rmin"] < norm < self.params["Rmax"])
                
        # Check if we need to update the driving slider's style
        if axis == 'x':
            if in_deadzone and not self._x_in_deadzone:
                slider.setStyleSheet(self._deadzone_style)
                slider.style().unpolish(slider)
                slider.style().polish(slider)
                slider.update()
                self._x_in_deadzone = True
            elif not in_deadzone and self._x_in_deadzone:
                slider.setStyleSheet(self._normal_style)
                slider.style().unpolish(slider)
                slider.style().polish(slider)
                slider.update()
                self._x_in_deadzone = False
        else:  # axis == 'y'
            if in_deadzone and not self._y_in_deadzone:
                slider.setStyleSheet(self._deadzone_style)
                slider.style().unpolish(slider)
                slider.style().polish(slider)
                slider.update()
                self._y_in_deadzone = True
            elif not in_deadzone and self._y_in_deadzone:
                slider.setStyleSheet(self._normal_style)
                slider.style().unpolish(slider)
                slider.style().polish(slider)
                slider.update()
                self._y_in_deadzone = False
        
        # If in deadzone, don't update values
        if in_deadzone:
            return
        
        # Outside deadzone - clear the other slider's style if needed and update normally
        if axis == 'x' and self._y_in_deadzone:
            other_slider.setStyleSheet(self._normal_style)
            other_slider.style().unpolish(other_slider)
            other_slider.style().polish(other_slider)
            other_slider.update()
            self._y_in_deadzone = False
        elif axis == 'y' and self._x_in_deadzone:
            other_slider.setStyleSheet(self._normal_style)
            other_slider.style().unpolish(other_slider)
            other_slider.style().polish(other_slider)
            other_slider.update()
            self._x_in_deadzone = False
            
        lineedit.setText(str(value))
        
        if axis == 'x':
            self._last_valid_x = value
        else:
            self._last_valid_y = value
    
    def _send_single_cartesian_command(self, axis):
        """Send cartesian command when individual axis button is pressed"""
        # Synchronize lineEdit with slider first
        if axis == 'x':
            lineedit = self.xlineEdit
            slider = self.xSlider
        elif axis == 'y':
            lineedit = self.ylineEdit
            slider = self.ySlider
        elif axis == 'z':
            lineedit = self.zlineEdit
            slider = self.zSlider
        else:  # mu - not implemented yet
            return
        
        try:
            value = int(lineedit.text())
            # Validate range
            if slider.minimum() <= value <= slider.maximum():
                slider.blockSignals(True)
                slider.setValue(value)
                slider.blockSignals(False)
            else:
                lineedit.setText(str(slider.value()))
                return
        except ValueError:
            lineedit.setText(str(slider.value()))
            return
        
        # Send command using slider value and current position for other axes
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        # Get the target coordinate from the slider that was changed
        # Get other coordinates from current actual position
        if axis == 'x':
            x = self.xSlider.value()
            y = self.current_y
            z = self.current_z
        elif axis == 'y':
            x = self.current_x
            y = self.ySlider.value()
            z = self.current_z
        elif axis == 'z':
            x = self.current_x
            y = self.current_y
            z = self.zSlider.value()
        
        # Send cartesian command: ix<x>y<y>z<z>
        command = f"ix{x:.2f}y{y:.2f}z{z:.2f}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _send_all_cartesian_command(self):
        """Send cartesian command with all line edit values (synchronizes sliders first)"""
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        # Synchronize all sliders with their line edits and validate
        try:
            # X coordinate
            x = int(self.xlineEdit.text())
            if self.xSlider.minimum() <= x <= self.xSlider.maximum():
                self.xSlider.blockSignals(True)
                self.xSlider.setValue(x)
                self.xSlider.blockSignals(False)
            else:
                print(f"X value {x} out of range")
                return
            
            # Y coordinate
            y = int(self.ylineEdit.text())
            if self.ySlider.minimum() <= y <= self.ySlider.maximum():
                self.ySlider.blockSignals(True)
                self.ySlider.setValue(y)
                self.ySlider.blockSignals(False)
            else:
                print(f"Y value {y} out of range")
                return
            
            # Z coordinate
            z = int(self.zlineEdit.text())
            if self.zSlider.minimum() <= z <= self.zSlider.maximum():
                self.zSlider.blockSignals(True)
                self.zSlider.setValue(z)
                self.zSlider.blockSignals(False)
            else:
                print(f"Z value {z} out of range")
                return
                
        except ValueError:
            print("Invalid values in line edits")
            return
        
        # Send cartesian command: ix<x>y<y>z<z>
        command = f"ix{x:.2f}y{y:.2f}z{z:.2f}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _enable_mouse_tracking(self, widget):
        """Recursively enable mouse tracking for widget and all children"""
        widget.setMouseTracking(True)
        for child in widget.findChildren(QWidget):
            child.setMouseTracking(True)
    
    def _replace_with_aspect_ratio_label(self):
        """Replace the standard QLabel with AspectRatioLabel to preserve aspect ratio"""
        # Get the layout containing renderLabel
        layout = self.horizontalLayout_6  # This is the layout from ui_gui.py
        
        # Store original pixmap
        original_pixmap = self.renderLabel.pixmap()
        parent = self.renderLabel.parent()
        
        # Find and remove the original label
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget() == self.renderLabel:
                layout.removeWidget(self.renderLabel)
                self.renderLabel.deleteLater()
                
                # Create new AspectRatioLabel with the same settings
                self.renderLabel = AspectRatioLabel(parent)
                self.renderLabel.setObjectName("renderLabel")
                self.renderLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Set the pixmap (this will store it in original_pixmap)
                if original_pixmap:
                    self.renderLabel.setPixmap(original_pixmap)
                
                # Insert at the same position
                layout.insertWidget(i, self.renderLabel)
                break
    
    def _setup_ring_sliders(self):
        """Replace placeholder widgets with RingSlider instances"""
        # Create theta slider
        theta_layout = QVBoxLayout(self.thetaWidget)
        theta_layout.setContentsMargins(0, 0, 0, 0)
        self.theta_slider = RingSlider(min_angle=0, max_angle=360, min_value=self.params['thetamin'], max_value=self.params['thetamax'], label="θ", value=0, parent=self.thetaWidget)
        theta_layout.addWidget(self.theta_slider)
        
        # Create alpha slider
        alpha_layout = QVBoxLayout(self.alphaWidget)
        alpha_layout.setContentsMargins(0, 0, 0, 0)
        self.alpha_slider = RingSlider(min_angle=60, max_angle=300, min_value=self.params['alphamin'], max_value=self.params['alphamax'], label="α", value=0, parent=self.alphaWidget)
        alpha_layout.addWidget(self.alpha_slider)
        
        # Create beta slider
        beta_layout = QVBoxLayout(self.betaWidget)
        beta_layout.setContentsMargins(0, 0, 0, 0)
        self.beta_slider = RingSlider(min_angle=60, max_angle=300, min_value=self.params['betamin'], max_value=self.params['betamax'], label="β", value=0, parent=self.betaWidget)
        beta_layout.addWidget(self.beta_slider)
        
        # Create gamma slider
        gamma_layout = QVBoxLayout(self.gammaWidget)
        gamma_layout.setContentsMargins(0, 0, 0, 0)
        self.gamma_slider = RingSlider(min_angle=60, max_angle=300, min_value=self.params['gammamin'], max_value=self.params['gammamax'], label="γ", value=None, parent=self.gammaWidget)
        gamma_layout.addWidget(self.gamma_slider)
    
    def _connect_sliders_to_robot(self):
        """Connect ring sliders to debounced serial command sender"""
        # Connect sliders to debounce method instead of directly to viewer
        # Viewer will be updated from Arduino feedback
        self.theta_slider.valueChanged.connect(lambda v: self._on_ring_slider_changed('theta', v))
        self.alpha_slider.valueChanged.connect(lambda v: self._on_ring_slider_changed('alpha', v))
        self.beta_slider.valueChanged.connect(lambda v: self._on_ring_slider_changed('beta', v))
    
    def _setup_3d_viewer(self):
        """Setup the 3D robot viewer and embed it in ThreeDWidget1"""
        # Create the robot viewer widget once in non-interactive mode
        # This disables mouse controls and uses fixed camera position
        self.robot_viewer = RobotVTKWidget(self.ThreeDWidget1, interactive=False)
        
        # Load the robot models
        models_dir = Path(__file__).parent / "Models"
        if models_dir.exists():
            self.robot_viewer.load_models(models_dir)
        
        # Add the robot viewer inside ThreeDWidget1 using a layout
        # This preserves the placeholder's position and dimensions
        container_layout = QVBoxLayout(self.ThreeDWidget1)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.robot_viewer)
        
        # Connect sliders to robot after robot viewer is created
        self._connect_sliders_to_robot()
    
    def _setup_coordinate_system(self):
        """Setup the 2D coordinate system widget and embed it in xyControl"""
        # Create the coordinate system widget with bounds from params.json
        self.coord_system = CoordinateSystemWidget(
            xmin=-self.params["Rmax"],
            xmax=self.params["Rmax"],
            ymin=-self.params["Rmax"],
            ymax=self.params["Rmax"],
            Rmin=150,  # Default Rmin value
            Rmax=350,  # Default Rmax value
            parent=self.xyControl
        )
        
        # Add the coordinate system inside xyControl using a layout
        container_layout = QVBoxLayout(self.xyControl)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.coord_system)
        
        # Connect coordinate changes to handle waypoints and update sliders
        self.coord_system.coordinatesChanged.connect(self._on_graph_clicked)
    
    def _on_graph_clicked(self, x, y):
        """Handle coordinate changes from the coordinate system widget"""
        # Update X and Y sliders
        self.xSlider.setValue(int(round(x)))
        self.ySlider.setValue(int(round(y)))
        
        # Handle waypoint creation in record mode
        if self.record_mode and self.recording_started and not self.recording_paused:
            # If there's already a temporary waypoint, remove it first
            if self.current_waypoint is not None:
                old_x, old_y = self.current_waypoint
                self.coord_system.remove_temporary_waypoint(old_x, old_y)
            
            # Store new temporary waypoint
            self.current_waypoint = (x, y)
            # Add temporary waypoint dot to graph
            self.coord_system.add_temporary_waypoint(x, y)
    
    def _on_record_mode(self):
        """Switch to record mode"""
        self.record_mode = True
        self.recordBtn.setChecked(True)
        self.execBtn.setChecked(False)
        # Enable Z, mu, and gripper sliders in Record mode
        self.zSliderProgram.setEnabled(True)
        self.zLineEditProgram.setEnabled(True)
        self.muSliderProgram.setEnabled(True)
        self.muLineEditProgram.setEnabled(True)
        self.gripperSliderProgram.setEnabled(True)
        self.gripperLineEditProgram.setEnabled(True)
        # Clear all waypoints when switching to Record mode
        self._clear_all_waypoints()
        # Clear file label
        self.fileLabel.setText("")
        self.file_loaded = False
    
    def _on_exec_mode(self):
        """Switch to exec mode"""
        self.record_mode = False
        self.recordBtn.setChecked(False)
        self.execBtn.setChecked(True)
        # Disable Z, mu, and gripper sliders in Execute mode (they will follow selected waypoint)
        self.zSliderProgram.setEnabled(False)
        self.zLineEditProgram.setEnabled(False)
        self.muSliderProgram.setEnabled(False)
        self.muLineEditProgram.setEnabled(False)
        self.gripperSliderProgram.setEnabled(False)
        self.gripperLineEditProgram.setEnabled(False)
    
    def _on_start_recording(self):
        """Start or resume recording waypoints"""
        if not self.recording_started:
            self.recording_started = True
            self.recording_paused = False
        elif self.recording_paused:
            self.recording_paused = False
    
    def _on_pause_recording(self):
        """Pause recording waypoints"""
        if self.recording_started and not self.recording_paused:
            self.recording_paused = True
    
    def _on_stop_recording(self):
        """Stop recording waypoints and optionally save to file"""
        if self.recording_started:
            self.recording_started = False
            self.recording_paused = False
            self.current_waypoint = None
            
            # Show save file dialog if there are waypoints to save
            if self.waypoints:
                file_path, _ = QFileDialog.getSaveFileName(
                    self,
                    "Save Waypoints",
                    "",
                    "Text Files (*.txt);;All Files (*)"
                )
                
                # If user selected a path, save the waypoints
                if file_path:
                    self._save_waypoints_to_file(file_path)
                
                # Clear waypoints whether saved or cancelled
                self._clear_all_waypoints()
    
    def _on_add_waypoint(self):
        """Add current waypoint to the list"""
        if self.current_waypoint and self.record_mode and self.recording_started:
            x, y = self.current_waypoint
            # Get Z, mu, and gripper values from sliders
            z = self.zSliderProgram.value()
            mu = self.muSliderProgram.value()
            gripper = self.gripperSliderProgram.value()
            
            # Add to waypoints list with mu and gripper values
            self.waypoints.append((x, y, z, mu, gripper))
            
            # Commit the temporary waypoint to permanent waypoints in graph
            self.coord_system.commit_temporary_waypoint()
            
            # Add to list widget with mu and gripper values
            waypoint_text = f"({x:.1f}, {y:.1f}, {z:.1f}, mu:{mu}, g:{gripper})"
            self.positionlistWidget.addItem(waypoint_text)
            
            # Clear current waypoint to allow selecting next point
            self.current_waypoint = None
    
    def _on_delete_waypoint(self):
        """Delete selected waypoint from list and graph"""
        # Get selected item
        selected_items = self.positionlistWidget.selectedItems()
        if not selected_items:
            return
        
        # Get the index of the selected item
        selected_item = selected_items[0]
        row = self.positionlistWidget.row(selected_item)
        
        # Remove from waypoints list
        if 0 <= row < len(self.waypoints):
            x, y, z, mu, gripper = self.waypoints[row]
            # Remove waypoint from graph
            self.coord_system.remove_waypoint(x, y)
            # Remove from list
            del self.waypoints[row]
            # Remove from list widget
            self.positionlistWidget.takeItem(row)
    
    def _on_waypoint_selected(self):
        """Handle waypoint selection from list widget"""
        selected_items = self.positionlistWidget.selectedItems()
        if selected_items:
            # Get the index of the selected item
            selected_item = selected_items[0]
            row = self.positionlistWidget.row(selected_item)
            self.selected_waypoint_index = row
            # Update graph to highlight selected waypoint
            self.coord_system.set_selected_waypoint(row)
            
            # In Execute mode, update Z, mu, and gripper sliders with selected waypoint's values
            if not self.record_mode and 0 <= row < len(self.waypoints):
                x, y, z, mu, gripper = self.waypoints[row]
                self.zSliderProgram.setValue(int(z))
                self.zLineEditProgram.setText(str(int(z)))
                self.muSliderProgram.setValue(int(mu))
                self.muLineEditProgram.setText(str(int(mu)))
                self.gripperSliderProgram.setValue(int(gripper))
                self.gripperLineEditProgram.setText(str(int(gripper)))
        else:
            self.selected_waypoint_index = None
            self.coord_system.set_selected_waypoint(None)
    
    def _save_waypoints_to_file(self, file_path):
        """Save waypoints to a file in the format x<value>y<value>z<value>m<value>g<value>"""
        try:
            with open(file_path, 'w') as f:
                for x, y, z, mu, gripper in self.waypoints:
                    # Format: x<value>y<value>z<value>m<value>g<value>
                    line = f"x{x:.1f}y{y:.1f}z{z:.1f}m{mu}g{gripper}\n"
                    f.write(line)
        except Exception as e:
            print(f"Error saving waypoints: {e}")
    
    def _on_import_waypoints(self):
        """Open file dialog to import waypoints in Execute mode"""
        # Only allow import in Execute mode
        if self.record_mode:
            return
        
        # Show file open dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Waypoints",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        # If user selected a file, load it
        if file_path:
            self._load_waypoints_from_file(file_path)
    
    def _load_waypoints_from_file(self, file_path):
        """Load waypoints from a file with format x<value>y<value>z<value>"""
        try:
            # Clear existing waypoints first
            self._clear_all_waypoints()
            
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse line format: x<value>y<value>z<value>m<value>g<value>
                    try:
                        # Find x, y, z, m, g values
                        x_start = line.find('x') + 1
                        y_start = line.find('y')
                        y_value_start = y_start + 1
                        z_start = line.find('z')
                        z_value_start = z_start + 1
                        m_start = line.find('m')
                        m_value_start = m_start + 1
                        g_start = line.find('g')
                        g_value_start = g_start + 1
                        
                        x = float(line[x_start:y_start])
                        y = float(line[y_value_start:z_start])
                        z = float(line[z_value_start:m_start])
                        mu = int(line[m_value_start:g_start])
                        gripper = int(line[g_value_start:])
                        
                        # Add waypoint to list
                        self.waypoints.append((x, y, z, mu, gripper))
                        
                        # Add to graph (permanent waypoint)
                        self.coord_system.add_waypoint(x, y)
                        
                        # Add to list widget
                        waypoint_text = f"({x:.1f}, {y:.1f}, {z:.1f}, mu:{mu}, g:{gripper})"
                        self.positionlistWidget.addItem(waypoint_text)
                        
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing line '{line}': {e}")
                        continue
            
            # Update file label with loaded filename
            file_name = Path(file_path).name
            self.fileLabel.setText(file_name)
            self.file_loaded = True
            
        except Exception as e:
            print(f"Error loading waypoints: {e}")
            self.fileLabel.setText("Error loading file")
            self.file_loaded = False
    
    def _clear_all_waypoints(self):
        """Clear all waypoints from list, graph, and memory"""
        # Clear waypoints list
        self.waypoints.clear()
        # Clear list widget
        self.positionlistWidget.clear()
        # Clear graph waypoints
        self.coord_system.clear_waypoints()
        # Reset selection
        self.selected_waypoint_index = None

    def switch_menu(self, idx):
        self.stackedWidget.setCurrentIndex(idx)
        
        # Switch VTK widget parent between ThreeDWidget1 (manip) and ThreeDWidget2 (program)
        if self.robot_viewer and idx in [1, 2]:
            if idx == 1:  # Manip page
                # Move to ThreeDWidget1
                self._reparent_vtk_widget(self.ThreeDWidget1)
            elif idx == 2:  # Program page
                # Move to ThreeDWidget2
                self._reparent_vtk_widget(self.ThreeDWidget2)
    
    def _reparent_vtk_widget(self, new_parent):
        """Reparent the VTK widget to a new container"""
        if not self.robot_viewer:
            return
        
        # Remove from current parent's layout
        current_parent = self.robot_viewer.parent()
        if current_parent and current_parent.layout():
            current_parent.layout().removeWidget(self.robot_viewer)
        
        # Set new parent
        self.robot_viewer.setParent(new_parent)
        
        # Create or get layout for new parent
        if not new_parent.layout():
            container_layout = QVBoxLayout(new_parent)
            container_layout.setContentsMargins(0, 0, 0, 0)
        else:
            container_layout = new_parent.layout()
        
        # Add widget to new parent's layout
        container_layout.addWidget(self.robot_viewer)
        
        # Show the widget
        self.robot_viewer.show()

    def toggle_window(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def title_mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def title_mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def title_mouseReleaseEvent(self, event):
        self._drag_pos = None
        # Update cursor based on current position after title drag
        pos = self.mapFromGlobal(event.globalPosition().toPoint())
        edge = self._get_resize_edge(pos)
        self._update_cursor(edge)
        event.accept()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.isMaximized():
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self._resize_edge = edge
                self._is_resizing = True
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geometry = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self._is_resizing and self._resize_edge:
            # Currently resizing
            self._perform_resize(event.globalPosition().toPoint())
            event.accept()
        else:
            # Not resizing, update cursor based on position
            edge = self._get_resize_edge(event.position().toPoint())
            self._update_cursor(edge)
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self._is_resizing:
            self._is_resizing = False
            self._resize_edge = None
            self._resize_start_pos = None
            self._resize_start_geometry = None
            # Update cursor based on current position after resize
            edge = self._get_resize_edge(event.position().toPoint())
            self._update_cursor(edge)
            event.accept()
        super().mouseReleaseEvent(event)
    
    def leaveEvent(self, event):
        """Reset cursor when mouse leaves the window"""
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)
    
    def _get_resize_edge(self, pos):
        """Determine which edge/corner is near the mouse position"""
        if self.isMaximized():
            return None
            
        rect = self.rect()
        margin = self._edge_margin
        
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin
        
        if top and left:
            return 'top_left'
        elif top and right:
            return 'top_right'
        elif bottom and left:
            return 'bottom_left'
        elif bottom and right:
            return 'bottom_right'
        elif top:
            return 'top'
        elif bottom:
            return 'bottom'
        elif left:
            return 'left'
        elif right:
            return 'right'
        return None
    
    def _update_cursor(self, edge):
        """Update cursor shape based on resize edge"""
        cursor_map = {
            'top': Qt.SizeVerCursor,
            'bottom': Qt.SizeVerCursor,
            'left': Qt.SizeHorCursor,
            'right': Qt.SizeHorCursor,
            'top_left': Qt.SizeFDiagCursor,
            'bottom_right': Qt.SizeFDiagCursor,
            'top_right': Qt.SizeBDiagCursor,
            'bottom_left': Qt.SizeBDiagCursor,
        }
        if edge:
            self.setCursor(cursor_map.get(edge, Qt.ArrowCursor))
        else:
            self.setCursor(Qt.ArrowCursor)
    
    def _perform_resize(self, global_pos):
        """Resize window based on mouse movement"""
        if not self._resize_start_geometry or not self._resize_start_pos:
            return
        
        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geometry)
        
        edge = self._resize_edge
        
        if 'left' in edge:
            geo.setLeft(geo.left() + delta.x())
        if 'right' in edge:
            geo.setRight(geo.right() + delta.x())
        if 'top' in edge:
            geo.setTop(geo.top() + delta.y())
        if 'bottom' in edge:
            geo.setBottom(geo.bottom() + delta.y())
        
        # Enforce minimum size
        min_width = self.minimumWidth() or 200
        min_height = self.minimumHeight() or 100
        
        if geo.width() >= min_width and geo.height() >= min_height:
            self.setGeometry(geo)
    
    def _on_refresh_com_ports(self):
        """Refresh the list of available COM ports"""
        self.listCOM.clear()
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            self.listCOM.addItem("No COM ports found")
        else:
            for port in ports:
                self.listCOM.addItem(f"{port.device} - {port.description}")
    
    def _on_connect_com(self):
        """Connect to the selected COM port"""
        selected_items = self.listCOM.selectedItems()
        
        if not selected_items:
            print("No COM port selected")
            return
        
        selected_text = selected_items[0].text()
        
        if selected_text == "No COM ports found":
            print("Cannot connect: No COM ports available")
            return
        
        # Extract port name (e.g., "COM3" from "COM3 - USB Serial Port")
        port_name = selected_text.split(" - ")[0]
        
        try:
            # Close existing connection if any
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.close()
            
            # Open new connection
            self.serial_connection = serial.Serial(port_name, baudrate=115200, timeout=1)
            self.connected_port = port_name
            print(f"Connected to {port_name}")
            
            # Start serial reading timer
            self.serial_read_timer.start()
            
            self._update_com_button_states()
            
        except serial.SerialException as e:
            print(f"Failed to connect to {port_name}: {e}")
            self.serial_connection = None
            self.connected_port = None
    
    def _on_disconnect_com(self):
        """Disconnect from the current COM port"""
        # Stop timers
        self.serial_read_timer.stop()
        self.command_debounce_timer.stop()
        
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                print(f"Disconnected from {self.connected_port}")
            except Exception as e:
                print(f"Error disconnecting: {e}")
        
        self.serial_connection = None
        self.connected_port = None
        self.serial_buffer = ""  # Clear buffer
        self._update_com_button_states()
    
    def _on_quit_app(self):
        """Quit the application"""
        # Disconnect COM port before quitting
        self._on_disconnect_com()
        # Close the application
        QApplication.quit()
    
    def _update_com_button_states(self):
        """Update button enabled/disabled states based on connection status"""
        is_connected = bool(self.serial_connection and self.serial_connection.is_open)
        
        self.connectBtn.setEnabled(not is_connected)
        self.disconnectBtn.setEnabled(is_connected)
        self.refreshBtn.setEnabled(not is_connected)
    
    def _on_ring_slider_changed(self, slider_name, value):
        """Handle ring slider changes with debouncing"""
        # Store the pending value
        if slider_name == 'theta':
            self.pending_theta = value
        elif slider_name == 'alpha':
            self.pending_alpha = value
        elif slider_name == 'beta':
            self.pending_beta = value
        
        # Restart the debounce timer (single-shot)
        self.command_debounce_timer.start()
    
    def _send_ring_slider_command(self):
        """Send ring slider command to Arduino after debounce period"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
        
        # Get current values from sliders (use pending if set, otherwise current)
        theta = self.pending_theta if self.pending_theta is not None else self.theta_slider.value()
        alpha = self.pending_alpha if self.pending_alpha is not None else self.alpha_slider.value()
        beta = self.pending_beta if self.pending_beta is not None else self.beta_slider.value()
        
        # Format command: 'it<theta>a<alpha>b<beta>'
        command = f"it{theta:.2f}a{alpha:.2f}b{beta:.2f}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")  # Debug output
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _read_serial_feedback(self):
        """Read and parse feedback from Arduino"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
        
        try:
            # Read available bytes
            if self.serial_connection.in_waiting > 0:
                data = self.serial_connection.read(self.serial_connection.in_waiting).decode('utf-8', errors='ignore')
                self.serial_buffer += data
                
                # Process complete lines
                while '\n' in self.serial_buffer:
                    line, self.serial_buffer = self.serial_buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        self._parse_feedback(line)
        except (serial.SerialException, UnicodeDecodeError) as e:
            print(f"Serial read error: {e}")
    
    def _parse_feedback(self, line):
        """Parse Arduino feedback, update 3D viewer and cartesian labels"""
        # Feedback format: "t<theta>a<alpha>b<beta>" or "d<date>t<theta>a<alpha>b<beta>"
        try:
            # Remove optional date prefix if present
            if line.startswith('d'):
                # Find where theta starts
                t_index = line.find('t')
                if t_index == -1:
                    return
                line = line[t_index:]  # Strip everything before 't'
            
            # Now parse: t<theta>a<alpha>b<beta>
            if not line.startswith('t'):
                return
            
            # Extract values
            parts = line[1:].replace('a', ' ').replace('b', ' ').split()
            if len(parts) >= 3:
                theta = float(parts[0])
                alpha = float(parts[1])
                beta = float(parts[2])
                
                # Convert degrees to radians for kinematics
                theta_rad = np.radians(theta)
                alpha_rad = np.radians(alpha)
                beta_rad = np.radians(beta)
                gamma_rad = 0.0  # Assume gamma = 0 for now (can be calculated if needed)
                
                # Calculate cartesian position using direct kinematics
                position = direct_kinematics(theta_rad, alpha_rad, beta_rad, gamma_rad)
                self.current_x = position[0]
                self.current_y = position[1]
                self.current_z = position[2]
                
                # Update cartesian labels with actual position
                self.xLabel.setText(f"{self.current_x:.1f}")
                self.yLabel.setText(f"{self.current_y:.1f}")
                self.zLabel.setText(f"{self.current_z:.1f}")
                
                # Update 3D viewer with actual positions from Arduino
                if self.robot_viewer:
                    self.robot_viewer.set_theta(theta)
                    self.robot_viewer.set_alpha(alpha)
                    self.robot_viewer.set_beta(beta)
                
                print(f"Feedback: θ={theta:.2f}° α={alpha:.2f}° β={beta:.2f}° | x={self.current_x:.1f} y={self.current_y:.1f} z={self.current_z:.1f}")  # Debug output
        except (ValueError, IndexError) as e:
            print(f"Parse error: {e} - Line: {line}")