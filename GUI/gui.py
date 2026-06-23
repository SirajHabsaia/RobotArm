from Designer.ui_gui import Ui_MainWindow
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QFileDialog, QAbstractItemView, QMessageBox
from PySide6.QtCore import Qt, QPoint, QRect, QUrl, QTimer, QThread, Signal
from PySide6.QtGui import QDesktopServices, QImage, QPixmap
from home import AspectRatioLabel
from ThreeD import RobotVTKWidget
from ring_slider import RingSlider
from graph import CoordinateSystemWidget
from Chess.widget import ChessWidget
from Chess.board_detector import BoardDetector
from Chess.config import BoardAnalyzerConfig
from Chess.chess_manager import ChessManager
from Chess.chess_engine import ChessEngine
from Draw.draw_widgets import ImageDisplayWidget, PolylineDisplayWidget, LiveDrawingWidget, ManualDrawingWidget
from Draw.poly_extract import ImageToPolylines
from planner import TrajectoryPlanner
from sound_player import play_sound
import chess
from pathlib import Path
import json
import math
import serial
import serial.tools.list_ports
import numpy as np
import cv2
import os
import sys
from kinematics import direct_kinematics, inverse_kinematics, gamma_to_mu, mu_to_gamma


def _bundle_base_dir() -> Path:
    """Root directory for bundled runtime assets (e.g. the .stockfish binary).

    Frozen (PyInstaller onedir): the unpacked bundle dir (sys._MEIPASS).
    Dev run: the repo root, i.e. the parent of the GUI/ package.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


class BoardDetectorThread(QThread):
    """Worker thread for running board detector stream processing."""
    frame_ready = Signal(np.ndarray)  # Signal to emit processed frames
    board_state_ready = Signal(object)  # Signal to emit board state (8x8 matrix)
    error_occurred = Signal(str)  # Signal to emit errors
    
    def __init__(self, config, side, dev_mode=False):
        super().__init__()
        self.config = config
        self.side = side
        self.dev_mode = dev_mode
        self.detector = None
        self._running = False
        self.pause_detection = False  # Flag to pause piece detection during robot's turn

    def run(self):
        """Run the detector stream processing."""
        try:
            self.detector = BoardDetector(self.config, self.side, dev_mode=self.dev_mode)
            self._running = True
            
            for result in self.detector.process_stream():
                if not self._running:
                    break

                # Mirror the pause state into the detector so it freezes
                # classification while the robot executes its move (next frame).
                self.detector.classification_paused = self.pause_detection

                if result is not None:
                    # Emit the full region (hand detection) frame
                    display_frame = result['display_big_cropped']
                    self.frame_ready.emit(display_frame)

                    # Emit board state if available (not skipped and not paused)
                    if not result['skipped'] and result['board_state'] is not None and not self.pause_detection:
                        self.board_state_ready.emit(result['board_state'])
        
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self.cleanup()
    
    def stop(self):
        """Stop the detector thread."""
        self._running = False
    
    def cleanup(self):
        """Clean up resources."""
        if self.detector is not None:
            self.detector.release()
            self.detector = None


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, dev_mode=False):
        super().__init__()
        self.dev_mode = dev_mode  # Enables developer overlays (e.g. per-square confidence)
        if dev_mode:
            print("[Dev] Developer mode enabled (--dev): per-square confidence overlay on")
        self.setupUi(self)
        self.setWindowTitle("Interface graphique")
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        
        self.icon_name_widget.setHidden(True)
        self.execWidget.setHidden(True)
        self.importBtn.setHidden(True)
        self.fileLabel.setHidden(True)
        
        # Flag to prevent recursive prohibited zone updates
        self._updating_prohibited_zones = False
        
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
        
        # Setup the chess board widget
        self._setup_chess_widget()
        
        # Chess board detector (chess_manager is initialized in _setup_chess_widget)
        self.detector_thread = None
        self.detector_running = False
        
        # Chess game state
        self.currently_playing_chess = False
        self.chess_engine = None
        self.waiting_for_arduino = False  # Flag to indicate waiting for 'D' response
        self.verifying_robot_move = False  # Flag to indicate we're verifying robot's move (not user's)
        self.chess_illegal_move = False  # True after the user makes an illegal/invalid placement
        self.chess_result_text = None  # Holds the final "Gameover - ..." text after a game ends
        self._offline_chess_engine = None  # Lazy Stockfish-free engine for test moves
        self._sounds_dir = Path(__file__).resolve().parent / "Sounds"  # Game sound effects
        self._illegal_sound_played_this_turn = False  # Play the illegal-move sound at most once per turn
        self._pending_robot_arrows = []  # Arrows for the robot move currently being verified
        
        # Initialize trajectory planner (used for chess moves)
        self._setup_trajectory_planner()
        
        # Setup chess detector controls
        self._setup_chess_detector_controls()
        
        # Setup drawing page
        self._setup_draw_page()

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
        
        # Connect reset and home command buttons
        self.resetLeftBtn.clicked.connect(self._on_reset_left)
        self.resetRightBtn.clicked.connect(self._on_reset_right)
        self.HomeCmdBtn.clicked.connect(self._on_home_command)

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
        
        # Track if we're currently executing a trajectory
        self.executing_trajectory = False
        
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
        
        # Connect play, pause, stop buttons for Execute mode
        self.playExec.clicked.connect(self._on_play_exec)
        self.pauseExec.clicked.connect(self._on_pause_exec)
        self.stopExec.clicked.connect(self._on_stop_exec)
        self.flushExec.clicked.connect(self._on_flush_exec)
        self.restartExec.clicked.connect(self._on_restart_exec)
        
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
        
        # Gripper command debouncing - separate timer
        self.gripper_debounce_timer = QTimer()
        self.gripper_debounce_timer.setSingleShot(True)
        self.gripper_debounce_timer.setInterval(100)  # 100ms debounce
        self.gripper_debounce_timer.timeout.connect(self._send_gripper_command)
        
        # Store pending gripper value
        self.pending_gripper = None
        
        # Gamma command debouncing - separate timer
        self.gamma_debounce_timer = QTimer()
        self.gamma_debounce_timer.setSingleShot(True)
        self.gamma_debounce_timer.setInterval(100)  # 100ms debounce
        self.gamma_debounce_timer.timeout.connect(self._send_gamma_command)
        
        # Store pending gamma value
        self.pending_gamma = None
        
        # Serial reading timer for feedback
        self.serial_read_timer = QTimer()
        self.serial_read_timer.setInterval(20)  # Read every 20ms
        self.serial_read_timer.timeout.connect(self._read_serial_feedback)
        self.serial_buffer = ""  # Buffer for incomplete serial data
        
        # Current actual position from Arduino feedback
        self.current_x = 200.0
        self.current_y = 0.0
        self.current_z = 250.0
        
        # Current joint angles from Arduino feedback
        self.current_alpha = 0.0
        self.current_gamma = 0.0
        self.current_mu = 0.0
        
        # Flag to track whether we're controlling mu (True) or gamma (False)
        self.controlling_mu = True
        
        # Last sent gripper percentage (0-100)
        self.last_gripper_percentage = 50
        
        # Developer mode flag
        self.devmode = True
        
        # Connect developer buttons
        self.abortBtn.clicked.connect(self._on_abort)
        self.devBtn.clicked.connect(self._on_dev_send)
        
        # Set visibility based on devmode
        self.abortBtn.setVisible(self.devmode)
        self.devBtn.setVisible(self.devmode)
        self.devLineEdit.setVisible(self.devmode)
    
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
        self.muBtn.clicked.connect(self._send_mu_command)
        
        # Connect send all button
        self.sendallBtn.clicked.connect(self._send_all_cartesian_command)
        
        # Setup gripper slider for Manip page
        self._setup_gripper_slider()
        
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
    
    def _setup_gripper_slider(self):
        """Setup gripper slider for Manip page"""
        gripper_min = self.params.get("grippermin", 0)
        gripper_max = self.params.get("grippermax", 180)
        gripper_def = self.params.get("gripperdef", 90)
        
        # Setup slider range and default value
        self.griperSlider.setMinimum(0)
        self.griperSlider.setMaximum(100)
        
        # Calculate default percentage (normalize from angle range to 0-100)
        default_percentage = int(((gripper_def - gripper_min) / (gripper_max - gripper_min)) * 100)
        self.griperSlider.setValue(default_percentage)
        
        # Connect slider to debounced handler
        self.griperSlider.valueChanged.connect(self._on_gripper_slider_changed)
    
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
        """Calculate inverse kinematics and update ring sliders when individual axis button is pressed"""
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
        else:
            return
        
        try:
            value = int(lineedit.text())
            # Validate range
            if slider.minimum() <= value <= slider.maximum():
                slider.setValue(value)
            else:
                lineedit.setText(str(slider.value()))
                return
        except ValueError:
            lineedit.setText(str(slider.value()))
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
        
        # Calculate inverse kinematics to get joint angles
        try:
            # Use correct mu value based on control mode
            if self.controlling_mu:
                mu_rad = np.radians(self.current_mu)
            else:
                # Convert gamma to mu for inverse kinematics
                mu_rad = gamma_to_mu(np.radians(self.current_gamma), np.radians(self.current_alpha))
            
            angles = inverse_kinematics(x, y, z, mu=mu_rad)
            
            # Validate that angles are valid numbers
            if not all(np.isfinite(angle) for angle in angles):
                raise ValueError("Inverse kinematics returned invalid angles (NaN or Inf)")
            
            # Convert radians to degrees
            theta_deg = np.degrees(angles[0])
            alpha_deg = np.degrees(angles[1])
            beta_deg = np.degrees(angles[2])
            
            # Validate converted angles
            if not all(np.isfinite(angle) for angle in [theta_deg, alpha_deg, beta_deg]):
                raise ValueError("Angle conversion resulted in invalid values")
            
            # Normalize theta to 0-360 range
            theta_deg = theta_deg % 360
            
            # Check alpha - beta constraint
            diff = alpha_deg - beta_deg
            diffmin = self.params.get('diffmin', -62)
            diffmax = self.params.get('diffmax', 56)
            
            if not (diffmin <= diff <= diffmax):
                # Show constraint warning
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Constraint Violation")
                msg.setText(f"Position ({x:.2f}, {y:.2f}, {z:.2f}) violates joint constraints!\n\n"
                           f"α - β = {diff:.1f}°\n"
                           f"Must be between {diffmin}° and {diffmax}°")
                msg.setInformativeText("This configuration may damage the robot or be unreachable.")
                
                # Add buttons
                proceed_btn = msg.addButton("Proceed Anyway", QMessageBox.AcceptRole)
                cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
                msg.setDefaultButton(cancel_btn)
                
                # Show dialog and get result
                msg.exec()
                
                if msg.clickedButton() != proceed_btn:
                    # User cancelled
                    print(f"Movement cancelled: constraint violation (α - β = {diff:.1f}°)")
                    return
            
            # Update current_alpha and recalculate gamma if needed
            self.current_alpha = alpha_deg
            if self.controlling_mu:
                # Recalculate gamma from mu with new alpha
                gamma_value = mu_to_gamma(np.radians(self.current_mu), np.radians(alpha_deg))
                gamma_degrees = np.degrees(gamma_value)
                self.current_gamma = gamma_degrees
                # Update gamma slider without triggering its change event
                self.gamma_slider.blockSignals(True)
                self.gamma_slider.setValue(gamma_degrees)
                self.gamma_slider.blockSignals(False)
            
            # Update ring sliders with calculated angles as targets (green dots)
            # This will automatically trigger the angular command to be sent
            self.theta_slider.setTargetValue(theta_deg)
            self.alpha_slider.setTargetValue(alpha_deg)
            self.beta_slider.setTargetValue(beta_deg)
            
            print(f"Calculated angles: θ={theta_deg:.2f}° α={alpha_deg:.2f}° β={beta_deg:.2f}°")
            
        except Exception as e:
            # Show error dialog
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Inverse Kinematics Error")
            msg.setText(f"Position ({x:.2f}, {y:.2f}, {z:.2f}) is unreachable")
            msg.setInformativeText(f"The inverse kinematics calculation failed:\n{str(e)}\n\nAborting movement.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            print(f"Inverse kinematics error: {e}")
    
    def _send_mu_command(self):
        """Send mu command when mu button is pressed"""
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        # Get mu value from lineEdit
        try:
            mu_value = int(self.mulineEdit.text())
            # Validate range
            if self.muSlider.minimum() <= mu_value <= self.muSlider.maximum():
                # Update slider to match lineEdit
                self.muSlider.setValue(mu_value)
            else:
                print(f"Mu value {mu_value} out of range")
                return
        except ValueError:
            print("Invalid mu value in line edit")
            return
        
        # Send mu command: m<mu>
        command = f"m{mu_value}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")
            
            # Instantly update the mu label with the sent value
            self.muLabel.setText(str(mu_value))
            
            # Set flag to indicate we're controlling mu
            self.controlling_mu = True
            self.current_mu = mu_value
            
            # Calculate gamma from mu using current alpha and update gamma slider
            gamma_value = mu_to_gamma(np.radians(mu_value), np.radians(self.current_alpha))
            gamma_degrees = np.degrees(gamma_value)
            self.current_gamma = gamma_degrees
            
            # Update gamma slider without triggering its change event
            self.gamma_slider.blockSignals(True)
            self.gamma_slider.setValue(gamma_degrees)
            self.gamma_slider.blockSignals(False)
            
            # Calculate and update XYZ position using direct kinematics
            theta_rad = np.radians(self.theta_slider.value())
            alpha_rad = np.radians(self.alpha_slider.value())
            beta_rad = np.radians(self.beta_slider.value())
            gamma_rad = gamma_value
            
            position = direct_kinematics(theta_rad, alpha_rad, beta_rad, gamma_rad)
            self.current_x = position[0]
            self.current_y = position[1]
            self.current_z = position[2]
            
            # Update XYZ labels
            self.xLabel.setText(f"{self.current_x:.1f}")
            self.yLabel.setText(f"{self.current_y:.1f}")
            self.zLabel.setText(f"{self.current_z:.1f}")
            
            # Update 3D viewer with new mu value
            if self.robot_viewer:
                self.robot_viewer.set_mu(mu_value)
            
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
        
        # Calculate inverse kinematics to get joint angles
        try:
            # Use correct mu value based on control mode
            if self.controlling_mu:
                mu_rad = np.radians(self.current_mu)
            else:
                # Convert gamma to mu for inverse kinematics
                mu_rad = gamma_to_mu(np.radians(self.current_gamma), np.radians(self.current_alpha))
            
            angles = inverse_kinematics(x, y, z, mu=mu_rad)
            
            # Validate that angles are valid numbers
            if not all(np.isfinite(angle) for angle in angles):
                raise ValueError("Inverse kinematics returned invalid angles (NaN or Inf)")
            
            # Convert radians to degrees
            theta_deg = np.degrees(angles[0])
            alpha_deg = np.degrees(angles[1])
            beta_deg = np.degrees(angles[2])
            
            # Validate converted angles
            if not all(np.isfinite(angle) for angle in [theta_deg, alpha_deg, beta_deg]):
                raise ValueError("Angle conversion resulted in invalid values")
            
            # Normalize theta to 0-360 range
            theta_deg = theta_deg % 360
            
            # Check alpha - beta constraint
            diff = alpha_deg - beta_deg
            diffmin = self.params.get('diffmin', -62)
            diffmax = self.params.get('diffmax', 56)
            
            if not (diffmin <= diff <= diffmax):
                # Show constraint warning
                from PySide6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle("Constraint Violation")
                msg.setText(f"Position ({x:.2f}, {y:.2f}, {z:.2f}) violates joint constraints!\n\n"
                           f"α - β = {diff:.1f}°\n"
                           f"Must be between {diffmin}° and {diffmax}°")
                msg.setInformativeText("This configuration may damage the robot or be unreachable.")
                
                # Add buttons
                proceed_btn = msg.addButton("Proceed Anyway", QMessageBox.AcceptRole)
                cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
                msg.setDefaultButton(cancel_btn)
                
                # Show dialog and get result
                msg.exec()
                
                if msg.clickedButton() != proceed_btn:
                    # User cancelled
                    print(f"Movement cancelled: constraint violation (α - β = {diff:.1f}°)")
                    return
            
            # Update current_alpha and recalculate gamma if needed
            self.current_alpha = alpha_deg
            if self.controlling_mu:
                # Recalculate gamma from mu with new alpha
                gamma_value = mu_to_gamma(np.radians(self.current_mu), np.radians(alpha_deg))
                gamma_degrees = np.degrees(gamma_value)
                self.current_gamma = gamma_degrees
                # Update gamma slider without triggering its change event
                self.gamma_slider.blockSignals(True)
                self.gamma_slider.setValue(gamma_degrees)
                self.gamma_slider.blockSignals(False)
            
            # Update ring sliders with calculated angles as targets (green dots)
            # This will automatically trigger the angular command to be sent
            self.theta_slider.setTargetValue(theta_deg)
            self.alpha_slider.setTargetValue(alpha_deg)
            self.beta_slider.setTargetValue(beta_deg)
            
            print(f"Calculated angles: θ={theta_deg:.2f}° α={alpha_deg:.2f}° β={beta_deg:.2f}°")
            
        except Exception as e:
            # Show error dialog
            from PySide6.QtWidgets import QMessageBox
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Inverse Kinematics Error")
            msg.setText(f"Position ({x:.2f}, {y:.2f}, {z:.2f}) is unreachable")
            msg.setInformativeText(f"The inverse kinematics calculation failed:\n{str(e)}\n\nAborting movement.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            print(f"Inverse kinematics error: {e}")
    
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
        
        # Create gamma slider (no target system - direct control)
        gamma_layout = QVBoxLayout(self.gammaWidget)
        gamma_layout.setContentsMargins(0, 0, 0, 0)
        self.gamma_slider = RingSlider(min_angle=60, max_angle=300, min_value=self.params['gammamin'], max_value=self.params['gammamax'], label="γ", value=0, use_target=False, parent=self.gammaWidget)
        gamma_layout.addWidget(self.gamma_slider)
        
        # Connect validation for alpha and beta line edits
        self._connect_ring_slider_validation()
    
    def _connect_ring_slider_validation(self):
        """Connect validation to ring slider line edit inputs"""
        # Disconnect the default editingFinished connections
        self.alpha_slider.value_edit.editingFinished.disconnect()
        self.beta_slider.value_edit.editingFinished.disconnect()
        
        # Connect to our validation methods
        self.alpha_slider.value_edit.editingFinished.connect(lambda: self._validate_alpha_input())
        self.beta_slider.value_edit.editingFinished.connect(lambda: self._validate_beta_input())
    
    def _validate_alpha_input(self):
        """Validate alpha input from line edit and check constraint with beta"""
        text = self.alpha_slider.value_edit.text()
        try:
            val = float(text)
            
            # Check if value is in range
            if not (self.alpha_slider.min_value <= val <= self.alpha_slider.max_value):
                self.alpha_slider.value_edit.setText(f"{self.alpha_slider._value:.1f}")
                self.alpha_slider.value_edit.setReadOnly(True)
                self.alpha_slider.value_edit.clearFocus()
                return
            
            # Get current target beta (or actual value if no target set)
            target_beta = self.beta_slider._target_value if self.beta_slider._target_value is not None else self.beta_slider._value
            
            # Calculate difference
            diff = val - target_beta
            diffmin = self.params.get('diffmin', -62)
            diffmax = self.params.get('diffmax', 56)
            
            # Check if difference is within allowed range
            if diffmin <= diff <= diffmax:
                # Valid - proceed
                self.alpha_slider.setTargetValue(val)
            else:
                # Invalid - show warning dialog
                self._show_constraint_warning('alpha', val, target_beta, diff, diffmin, diffmax)
        except ValueError:
            self.alpha_slider.value_edit.setText(f"{self.alpha_slider._value:.1f}")
        
        # Always clear focus and set readonly after processing
        self.alpha_slider.value_edit.setReadOnly(True)
        self.alpha_slider.value_edit.clearFocus()
        self.setFocus()  # Move focus to main window
    
    def _validate_beta_input(self):
        """Validate beta input from line edit and check constraint with alpha"""
        text = self.beta_slider.value_edit.text()
        try:
            val = float(text)
            
            # Check if value is in range
            if not (self.beta_slider.min_value <= val <= self.beta_slider.max_value):
                self.beta_slider.value_edit.setText(f"{self.beta_slider._value:.1f}")
                self.beta_slider.value_edit.setReadOnly(True)
                self.beta_slider.value_edit.clearFocus()
                return
            
            # Get current target alpha (or actual value if no target set)
            target_alpha = self.alpha_slider._target_value if self.alpha_slider._target_value is not None else self.alpha_slider._value
            
            # Calculate difference
            diff = target_alpha - val
            diffmin = self.params.get('diffmin', -62)
            diffmax = self.params.get('diffmax', 56)
            
            # Check if difference is within allowed range
            if diffmin <= diff <= diffmax:
                # Valid - proceed
                self.beta_slider.setTargetValue(val)
            else:
                # Invalid - show warning dialog
                self._show_constraint_warning('beta', target_alpha, val, diff, diffmin, diffmax)
        except ValueError:
            self.beta_slider.value_edit.setText(f"{self.beta_slider._value:.1f}")
        
        # Always clear focus and set readonly after processing
        self.beta_slider.value_edit.setReadOnly(True)
        self.beta_slider.value_edit.clearFocus()
        self.setFocus()  # Move focus to main window
    
    def _show_constraint_warning(self, changed_slider, alpha_val, beta_val, diff, diffmin, diffmax):
        """Show warning dialog when constraint is violated"""
        from PySide6.QtWidgets import QMessageBox
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Constraint Violation")
        msg.setText(f"The entered value violates joint constraints!\n\n"
                   f"α - β = {diff:.1f}°\n"
                   f"Must be between {diffmin}° and {diffmax}°")
        msg.setInformativeText("This configuration may damage the robot or be unreachable.")
        
        # Add buttons
        proceed_btn = msg.addButton("Proceed Anyway", QMessageBox.AcceptRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.setDefaultButton(cancel_btn)
        
        # Show dialog and get result
        msg.exec()
        
        if msg.clickedButton() == proceed_btn:
            # User chose to proceed anyway
            if changed_slider == 'alpha':
                self.alpha_slider.setTargetValue(alpha_val)
            else:
                self.beta_slider.setTargetValue(beta_val)
        else:
            # User cancelled - revert to current value
            if changed_slider == 'alpha':
                self.alpha_slider.value_edit.setText(f"{self.alpha_slider._value:.1f}")
            else:
                self.beta_slider.value_edit.setText(f"{self.beta_slider._value:.1f}")

    
    def _connect_sliders_to_robot(self):
        """Connect ring sliders to debounced serial command sender"""
        # Connect sliders to debounce method instead of directly to viewer
        # Viewer will be updated from Arduino feedback
        self.theta_slider.valueChanged.connect(lambda v: self._on_ring_slider_changed('theta', v))
        self.alpha_slider.valueChanged.connect(lambda v: self._on_ring_slider_changed('alpha', v))
        self.beta_slider.valueChanged.connect(lambda v: self._on_ring_slider_changed('beta', v))
        self.gamma_slider.valueChanged.connect(lambda v: self._on_gamma_slider_changed(v))
        
        # Initialize prohibited zones (will be updated from feedback)
        self._update_alpha_prohibited_zone()
        self._update_beta_prohibited_zone()
    
    def _update_alpha_prohibited_zone(self):
        """Update alpha slider's prohibited zone based on current beta value"""
        if self._updating_prohibited_zones:
            return
        
        self._updating_prohibited_zones = True
        try:
            beta_value = self.beta_slider.value()
            diffmax = self.params.get('diffmax', 50)
            diffmin = self.params.get('diffmin', -62)
            
            # Get alpha range
            alpha_min = self.params['alphamin']
            alpha_max = self.params['alphamax']
            
            # First prohibited zone: alpha - beta > diffmax => alpha > beta + diffmax
            min_prohibited_alpha1 = beta_value + diffmax
            
            if min_prohibited_alpha1 >= alpha_max:
                # No prohibited zone 1
                self.alpha_slider.prohibited_start = -1
                self.alpha_slider.prohibited_end = -1
            elif min_prohibited_alpha1 <= alpha_min:
                # Entire range is prohibited (shouldn't happen)
                self.alpha_slider.prohibited_start = self.alpha_slider.min_angle
                self.alpha_slider.prohibited_end = self.alpha_slider.max_angle
            else:
                # Prohibited zone 1: from min_prohibited_alpha1 to max
                prohibited_start_angle = self.alpha_slider.angle_for_value(min_prohibited_alpha1)
                self.alpha_slider.prohibited_start = prohibited_start_angle
                self.alpha_slider.prohibited_end = self.alpha_slider.max_angle
            
            # Second prohibited zone: alpha - beta < diffmin => alpha < beta + diffmin
            max_prohibited_alpha2 = beta_value + diffmin
            
            if max_prohibited_alpha2 <= alpha_min:
                # No prohibited zone 2
                self.alpha_slider.prohibited_start2 = -1
                self.alpha_slider.prohibited_end2 = -1
            elif max_prohibited_alpha2 >= alpha_max:
                # Entire range is prohibited
                self.alpha_slider.prohibited_start2 = self.alpha_slider.min_angle
                self.alpha_slider.prohibited_end2 = self.alpha_slider.max_angle
            else:
                # Prohibited zone 2: from min to max_prohibited_alpha2
                prohibited_end_angle2 = self.alpha_slider.angle_for_value(max_prohibited_alpha2)
                self.alpha_slider.prohibited_start2 = self.alpha_slider.min_angle
                self.alpha_slider.prohibited_end2 = prohibited_end_angle2
            
            self.alpha_slider.update()
        finally:
            self._updating_prohibited_zones = False
    
    def _update_beta_prohibited_zone(self):
        """Update beta slider's prohibited zone based on current alpha value"""
        if self._updating_prohibited_zones:
            return
        
        self._updating_prohibited_zones = True
        try:
            alpha_value = self.alpha_slider.value()
            diffmax = self.params.get('diffmax', 50)
            diffmin = self.params.get('diffmin', -62)
            
            # Get beta range
            beta_min = self.params['betamin']
            beta_max = self.params['betamax']
            
            # First prohibited zone: alpha - beta > diffmax => beta < alpha - diffmax
            max_prohibited_beta1 = alpha_value - diffmax
            
            if max_prohibited_beta1 <= beta_min:
                # No prohibited zone 1
                self.beta_slider.prohibited_start = -1
                self.beta_slider.prohibited_end = -1
            elif max_prohibited_beta1 >= beta_max:
                # Entire range is prohibited
                self.beta_slider.prohibited_start = self.beta_slider.min_angle
                self.beta_slider.prohibited_end = self.beta_slider.max_angle
            else:
                # Prohibited zone 1: from min to max_prohibited_beta1
                prohibited_end_angle = self.beta_slider.angle_for_value(max_prohibited_beta1)
                self.beta_slider.prohibited_start = self.beta_slider.min_angle
                self.beta_slider.prohibited_end = prohibited_end_angle
            
            # Second prohibited zone: alpha - beta < diffmin => beta > alpha - diffmin
            min_prohibited_beta2 = alpha_value - diffmin
            
            if min_prohibited_beta2 >= beta_max:
                # No prohibited zone 2
                self.beta_slider.prohibited_start2 = -1
                self.beta_slider.prohibited_end2 = -1
            elif min_prohibited_beta2 <= beta_min:
                # Entire range is prohibited
                self.beta_slider.prohibited_start2 = self.beta_slider.min_angle
                self.beta_slider.prohibited_end2 = self.beta_slider.max_angle
            else:
                # Prohibited zone 2: from min_prohibited_beta2 to max
                prohibited_start_angle2 = self.beta_slider.angle_for_value(min_prohibited_beta2)
                self.beta_slider.prohibited_start2 = prohibited_start_angle2
                self.beta_slider.prohibited_end2 = self.beta_slider.max_angle
            
            self.beta_slider.update()
        finally:
            self._updating_prohibited_zones = False
    
    def _setup_3d_viewer(self):
        """Setup the 3D robot viewer and embed it in ThreeDWidget1"""
        # Create the robot viewer widget in interactive mode
        # Allows user to rotate, zoom, and pan the camera
        self.robot_viewer = RobotVTKWidget(self.ThreeDWidget1, interactive=True)
        
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
            Rmin=self.params["Rmin"],  # Default Rmin value
            Rmax=self.params["Rmax"],  # Default Rmax value
            parent=self.xyControl
        )
        
        # Add the coordinate system inside xyControl using a layout
        container_layout = QVBoxLayout(self.xyControl)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(self.coord_system)
        
        # Connect coordinate changes to handle waypoints and update sliders
        self.coord_system.coordinatesChanged.connect(self._on_graph_clicked)
    
    def _setup_trajectory_planner(self):
        """Initialize the trajectory planner with parameters from params.json"""
        joints_max_speeds = np.array([
            self.params.get('thetamaxspeed', 30.0),
            self.params.get('alphamaxspeed', 15.0),
            self.params.get('betamaxspeed', 15.0)
        ])  # deg/s
        joints_max_accel = np.array([
            self.params.get('thetamaxaccel', 100.0),
            self.params.get('alphamaxaccel', 90.0),
            self.params.get('betamaxaccel', 90.0)
        ])  # deg/s^2
        
        # IK/FK wrappers
        ik_func = lambda x, y, z, mu: [angle * 180.0/np.pi for angle in inverse_kinematics(x, y, z, mu=mu)]
        fk_func = lambda theta, alpha, beta, gamma: direct_kinematics(
            theta * np.pi/180.0, alpha * np.pi/180.0, beta * np.pi/180.0, gamma * np.pi/180.0
        )
        
        # Create planner instance
        self.trajectory_planner = TrajectoryPlanner(
            joints_max_speeds=joints_max_speeds,
            joints_max_accel=joints_max_accel,
            n_waypoints_input=100,
            dt_sample=1e-3,
            inverse_kinematics_func=ik_func,
            forward_kinematics_func=fk_func,
            mu_func=ChessEngine.mu_func,
            gripper_actions=[],  # Will be set when planning
            adaptive_sampling=False
        )
    
    def _setup_chess_widget(self):
        """Setup the chess board widget and embed it in chessWidget"""
        # Create the chess widget with default orientation (white at bottom)
        self.chess_board = ChessWidget(parent=self.chessWidget, orientation='white')
        
        # Add the chess widget inside chessWidget using a layout with center alignment
        container_layout = QVBoxLayout(self.chessWidget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self.chess_board, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        
        # Initialize chess manager with the widget
        try:
            self.chess_manager = ChessManager(self.chess_board)
        except Exception as e:
            print(f"[GUI] ERROR initializing ChessManager: {e}")
            import traceback
            traceback.print_exc()
            self.chess_manager = None
    
    def _setup_chess_detector_controls(self):
        """Setup chess board detector controls and connections."""
        # Create a label to display camera feed in camWidget
        self.cam_label = QLabel(self.camWidget)
        self.cam_label.setGeometry(0, 0, 300, 300)
        self.cam_label.setScaledContents(True)
        self.cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cam_label.setStyleSheet("background-color: rgb(21, 21, 21);")
        
        # Connect input mode buttons to update the label
        self.chess_camidBtn.toggled.connect(self._on_chess_input_mode_changed)
        self.chess_camipBtn.toggled.connect(self._on_chess_input_mode_changed)
        self.chess_videoBtn.toggled.connect(self._on_chess_input_mode_changed)
        
        # Connect initialize button
        self.chess_initializeBtn.clicked.connect(self._on_chess_initialize_toggle)
        
        # Connect play button
        self.chess_playBtn.clicked.connect(self._on_chess_play_toggle)

        # Connect test-move button (override checkable/autoexclusive from the UI
        # so it behaves as a plain push button that fires on every click)
        self.chess_testBtn.setCheckable(False)
        self.chess_testBtn.clicked.connect(self._on_chess_test_move)

        # Set default mode label
        self._update_chess_mode_label()
    
    def _update_chess_mode_label(self):
        """Update the chess mode label based on selected input mode."""
        if self.chess_camidBtn.isChecked():
            self.chess_modeLabel.setText("Camera ID:")
        elif self.chess_camipBtn.isChecked():
            self.chess_modeLabel.setText("Camera IP:")
        elif self.chess_videoBtn.isChecked():
            self.chess_modeLabel.setText("Video Path:")
        else:
            # Default to Camera ID if none selected
            self.chess_modeLabel.setText("Camera ID:")
    
    def _on_chess_input_mode_changed(self):
        """Handle input mode button toggle."""
        self._update_chess_mode_label()
    
    def _on_chess_initialize_toggle(self):
        """Handle initialize/stop button toggle."""
        if not self.detector_running:
            # Start detector
            self._start_chess_detector()
        else:
            # Stop detector
            self._stop_chess_detector()
    
    def _start_chess_detector(self):
        """Start the chess board detector."""
        # Validate inputs
        config = self._get_chess_detector_config()
        if config is None:
            return  # Error dialog already shown
        
        # Get selected side
        side = "white" if self.chess_mode_whiteBtn.isChecked() else "black"
        
        # Create and start detector thread
        self.detector_thread = BoardDetectorThread(config, side, dev_mode=self.dev_mode)
        self.detector_thread.frame_ready.connect(self._on_detector_frame_ready)
        self.detector_thread.board_state_ready.connect(self._on_board_state_ready)
        self.detector_thread.error_occurred.connect(self._on_detector_error)
        self.detector_thread.finished.connect(self._on_detector_finished)
        self.detector_thread.start()
        
        # Update button state
        self.detector_running = True
        self.chess_initializeBtn.setText("Stop")

        # Camera is now initialized; refresh the chess label
        if not self.currently_playing_chess:
            self.chess_result_text = None
        self._update_chess_label()
        self._play_chess_sound("camera_initialized.wav")

        # Disable input controls while running
        self.chess_camidBtn.setEnabled(False)
        self.chess_camipBtn.setEnabled(False)
        self.chess_videoBtn.setEnabled(False)
        self.chess_infoLineEdit.setEnabled(False)
        self.chess_mode_whiteBtn.setEnabled(False)
        self.chess_mode_blackBtn.setEnabled(False)
        self.chess_thresholdLineEdit.setEnabled(False)
    
    def _stop_chess_detector(self):
        """Stop the chess board detector."""
        if self.detector_thread is not None:
            self.detector_thread.stop()
            self.detector_thread.wait()  # Wait for thread to finish
            self.detector_thread = None
        
        # Update button state
        self.detector_running = False
        self.chess_initializeBtn.setText("Initialize")

        # Camera stopped; refresh the chess label
        if not self.currently_playing_chess:
            self.chess_result_text = None
        self._update_chess_label()

        # Re-enable input controls
        self.chess_camidBtn.setEnabled(True)
        self.chess_camipBtn.setEnabled(True)
        self.chess_videoBtn.setEnabled(True)
        self.chess_infoLineEdit.setEnabled(True)
        self.chess_mode_whiteBtn.setEnabled(True)
        self.chess_mode_blackBtn.setEnabled(True)
        self.chess_thresholdLineEdit.setEnabled(True)
        
        # Clear camera display
        self.cam_label.clear()
        self.cam_label.setStyleSheet("background-color: rgb(21, 21, 21);")
    
    def _get_chess_detector_config(self):
        """Get and validate chess detector configuration."""
        config = BoardAnalyzerConfig()
        
        # Get input mode
        if self.chess_camidBtn.isChecked():
            mode = "camera"
            input_text = self.chess_infoLineEdit.text().strip()
            
            if not input_text:
                QMessageBox.critical(self, "Invalid Input", "Please enter a camera ID (e.g., 0, 1, 2)")
                return None
            
            try:
                camera_id = int(input_text)
                config.camera_index = camera_id
            except ValueError:
                QMessageBox.critical(self, "Invalid Input", "Camera ID must be a number (e.g., 0, 1, 2)")
                return None
        
        elif self.chess_camipBtn.isChecked():
            mode = "ip_camera"
            input_text = self.chess_infoLineEdit.text().strip()
            
            if not input_text:
                QMessageBox.critical(self, "Invalid Input", "Please enter a camera IP address or URL")
                return None
            
            config.camera_ip = input_text
        
        elif self.chess_videoBtn.isChecked():
            mode = "video"
            input_text = self.chess_infoLineEdit.text().strip()
            
            if not input_text:
                QMessageBox.critical(self, "Invalid Input", "Please enter a video file path")
                return None
            
            # Expand ~ / env vars, then resolve relative paths against Chess/.
            video_path = Path(os.path.expandvars(input_text)).expanduser()
            if not video_path.is_absolute():
                video_path = Path(__file__).parent / "Chess" / video_path
            
            if not video_path.exists():
                QMessageBox.critical(self, "File Not Found", f"Video file not found:\n{video_path}")
                return None
            
            config.video_path = str(video_path)
        
        else:
            QMessageBox.critical(self, "No Mode Selected", "Please select an input mode (Camera ID, Camera IP, or Video)")
            return None
        
        config.mode = mode
        
        # Get hand detection threshold
        threshold_text = self.chess_thresholdLineEdit.text().strip()
        if threshold_text:
            try:
                threshold = float(threshold_text)
                config.hand_contour_threshold = threshold
            except ValueError:
                QMessageBox.warning(self, "Invalid Threshold", "Hand detection threshold must be a number. Using default value (200.0)")
        
        # Validate side selection
        if not self.chess_mode_whiteBtn.isChecked() and not self.chess_mode_blackBtn.isChecked():
            QMessageBox.critical(self, "No Side Selected", "Please select which side you're playing (White or Black)")
            return None
        
        return config
    
    def _on_detector_frame_ready(self, frame):
        """Handle new frame from detector."""
        # Convert frame from BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Resize to 300x300 for display
        frame_resized = cv2.resize(frame_rgb, (300, 300))
        
        # Convert to QImage
        h, w, ch = frame_resized.shape
        bytes_per_line = ch * w
        qt_image = QImage(frame_resized.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Display in label
        self.cam_label.setPixmap(QPixmap.fromImage(qt_image))
    
    def _on_board_state_ready(self, board_state):
        """Handle new board state from detector."""
        # board_state is 8x8 matrix of (class_label, confidence) tuples

        # Pass to chess manager for validation
        if not self.chess_manager:
            return

        status = self.chess_manager.process_detected_state(board_state)

        if status == 'moved':
            # A legal move was recognized; clear any pending illegal-move warning,
            # the red mismatch overlay and the tentative verification arrow, then
            # draw the confirmed arrow for the move.
            self.chess_illegal_move = False
            self._clear_board_mismatch()
            self._clear_pending_move_arrows()
            self._show_move_arrows()

            if self.verifying_robot_move:
                # Robot's move verified, now it's user's turn
                print("[Chess] Robot move verified! User's turn.")
                self.verifying_robot_move = False
                # Did the robot's move end the game?
                if not self._check_chess_game_over():
                    # New player turn: reset the per-turn illegal-sound guard
                    self._illegal_sound_played_this_turn = False
                    self._update_chess_label()
                    self._play_turn_sound(is_player_turn=True)
            elif self.currently_playing_chess and self.chess_engine and not self.waiting_for_arduino:
                # User just made a valid move
                print("[Chess] User move detected! Robot's turn.")
                # Did the user's move end the game?
                if not self._check_chess_game_over():
                    # Pause piece detection (robot's turn now) and respond
                    if self.detector_thread:
                        self.detector_thread.pause_detection = True
                    self._execute_robot_move()

        elif status == 'invalid':
            # New placement that matches no legal move. This happens either when
            # the user makes an illegal move, or when the board changes while we
            # are still verifying the robot's move (e.g. the player moved too
            # soon). In both cases, mark the differing squares in red.
            if self.currently_playing_chess:
                self._show_board_mismatch()

            # The "Illegal move" label is only meaningful on the user's turn.
            if (self.currently_playing_chess and not self.waiting_for_arduino
                    and not self.verifying_robot_move and not self.chess_illegal_move):
                self.chess_illegal_move = True
                self._update_chess_label()
                # Play the illegal-move sound at most once per turn (the label can
                # be re-shown after a revert, but the sound should not spam).
                if not self._illegal_sound_played_this_turn:
                    self._play_chess_sound("illegal_move.wav")
                    self._illegal_sound_played_this_turn = True

        elif status == 'nochange':
            # Board is back at the expected position; clear the overlay/warning.
            self._clear_board_mismatch()
            if self.chess_illegal_move:
                self.chess_illegal_move = False
                self._update_chess_label()
    
    def _on_detector_error(self, error_msg):
        """Handle detector error."""
        QMessageBox.critical(self, "Detector Error", f"An error occurred:\n{error_msg}")
        self._stop_chess_detector()
    
    def _on_detector_finished(self):
        """Handle detector thread finished."""
        # This is called when the thread finishes naturally or after stop()
        pass
    
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
        # Enable list widget for user interaction in Record mode
        self.positionlistWidget.setEnabled(True)
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
        # Disable list widget to prevent user selection (programmatic selection still works)
        self.positionlistWidget.setEnabled(False)
    
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
        if not self.record_mode or not self.recording_started:
            return
        
        # Check if we have a current waypoint from graph click
        if self.current_waypoint:
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
            
        elif len(self.waypoints) > 0:
            # No graph click, but we have previous waypoints
            # Use x,y from last waypoint and z,mu,gripper from sliders
            last_waypoint = self.waypoints[-1]
            x = last_waypoint[0]
            y = last_waypoint[1]
            
            # Get Z, mu, and gripper values from sliders
            z = self.zSliderProgram.value()
            mu = self.muSliderProgram.value()
            gripper = self.gripperSliderProgram.value()
            
            # Add to waypoints list with mu and gripper values
            self.waypoints.append((x, y, z, mu, gripper))
            
            # Add to graph (permanent waypoint - reuse same x,y position)
            self.coord_system.add_waypoint(x, y)
            
            # Add to list widget with mu and gripper values
            waypoint_text = f"({x:.1f}, {y:.1f}, {z:.1f}, mu:{mu}, g:{gripper})"
            self.positionlistWidget.addItem(waypoint_text)
            
            print(f"Added waypoint using previous x,y: ({x:.1f}, {y:.1f}) with current z={z}, mu={mu}, gripper={gripper}")
    
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
    
    # ============================================================================
    # DRAWING PAGE METHODS
    # ============================================================================
    
    def _setup_draw_page(self):
        """Setup the drawing page widgets and connections."""
        # Drawing state
        self.draw_image_path = None
        self.draw_converter = None
        self.draw_polylines = []  # List of polylines as numpy arrays
        self.draw_executing = False
        self.draw_current_polyline_index = 0
        self.draw_plotting_active = False  # Flag to track if we should plot feedback points
        self.draw_z_threshold = 0.0  # Z threshold for filtering drawing points
        self.draw_point_buffer = []  # Buffer for points to be plotted
        self.draw_manual_polylines = []  # Polylines from manual drawing (numpy arrays)
        
        # Timer for updating live drawing graph (200ms interval to avoid slowdown)
        self.draw_update_timer = QTimer()
        self.draw_update_timer.setInterval(200)  # Update every 200ms
        self.draw_update_timer.timeout.connect(self._update_live_drawing_from_buffer)
        self.draw_update_timer.start()  # Start timer immediately
        
        # Create both image and manual drawing widgets
        self.drawImageWidget = ImageDisplayWidget()
        self.drawImageWidget.setMinimumSize(240, 240)
        self.drawImageWidget.setMaximumSize(240, 240)
        
        self.drawManualWidget = ManualDrawingWidget()
        self.drawManualWidget.setMinimumSize(240, 240)
        self.drawManualWidget.setMaximumSize(240, 240)
        
        # Get layout and replace drawMainWidget with a container
        layout = self.drawMainWidget.parent().layout()
        index = layout.indexOf(self.drawMainWidget)
        layout.removeWidget(self.drawMainWidget)
        self.drawMainWidget.deleteLater()
        
        # Start with ImageDisplayWidget
        layout.insertWidget(index, self.drawImageWidget)
        self.drawManualWidget.hide()  # Hide manual widget initially
        
        # Replace drawResultWidget with PolylineDisplayWidget
        self.drawPolylineWidget = PolylineDisplayWidget()
        
        # Remove old widget and add new one
        result_layout = self.drawResultWidget.parent().layout()
        result_index = result_layout.indexOf(self.drawResultWidget)
        result_layout.removeWidget(self.drawResultWidget)
        self.drawResultWidget.deleteLater()
        result_layout.insertWidget(result_index, self.drawPolylineWidget)
        
        # Replace drawLiveWidget with LiveDrawingWidget
        self.drawLiveWidget_new = LiveDrawingWidget()
        
        # Remove old widget and add new one
        live_layout = self.drawLiveWidget.parent().layout()
        live_index = live_layout.indexOf(self.drawLiveWidget)
        live_layout.removeWidget(self.drawLiveWidget)
        self.drawLiveWidget.deleteLater()
        live_layout.insertWidget(live_index, self.drawLiveWidget_new)
        
        # Setup slider ranges and default values
        self.drawCannyLowSlider.setMinimum(0)
        self.drawCannyLowSlider.setMaximum(255)
        self.drawCannyLowSlider.setValue(50)
        self.drawCannyLowLabel.setText("50")
        
        self.drawCannyHighSlider.setMinimum(0)
        self.drawCannyHighSlider.setMaximum(255)
        self.drawCannyHighSlider.setValue(150)
        self.drawCannyHighLabel.setText("150")
        
        self.drawKernelSlider.setMinimum(0)
        self.drawKernelSlider.setMaximum(15)
        self.drawKernelSlider.setValue(3)
        self.drawKernelSlider.setSingleStep(2)
        self.drawKernelLabel.setText("3")
        
        self.drawMergeSlider.setMinimum(0)
        self.drawMergeSlider.setMaximum(50)
        self.drawMergeSlider.setValue(10)
        self.drawMergeLabel.setText("10")
        
        # Set default values for workspace parameters
        self.drawCenterXLineEdit.setText("400")
        self.drawCenterYLineEdit.setText("0")
        self.drawLengthLineEdit.setText("200")
        
        # Check ImagefileBtn by default
        self.ImagefileBtn.setChecked(True)
        
        # Connect mode buttons
        self.ImagefileBtn.toggled.connect(self._on_draw_mode_changed)
        self.DrawingBtn.toggled.connect(self._on_draw_mode_changed)
        
        # Connect signals
        self.drawImageWidget.image_dropped.connect(self._on_draw_image_loaded)
        self.drawManualWidget.drawing_updated.connect(self._on_manual_drawing_updated)
        
        self.drawCannyLowSlider.valueChanged.connect(self._on_draw_parameter_changed)
        self.drawCannyHighSlider.valueChanged.connect(self._on_draw_parameter_changed)
        self.drawKernelSlider.valueChanged.connect(self._on_draw_parameter_changed)
        self.drawMergeSlider.valueChanged.connect(self._on_draw_parameter_changed)
        
        self.drawCenterXLineEdit.textChanged.connect(self._on_draw_workspace_changed)
        self.drawCenterYLineEdit.textChanged.connect(self._on_draw_workspace_changed)
        self.drawLengthLineEdit.textChanged.connect(self._on_draw_workspace_changed)
        
        self.drawZLineEdit.textChanged.connect(self._on_draw_parameter_changed)
        self.drawZLiftLineEdit.textChanged.connect(self._on_draw_parameter_changed)
        
        self.startDrawingBtn.clicked.connect(self._on_start_drawing)
        self.undoDrawingBtn.clicked.connect(self._on_undo_drawing)
        
        print("[DrawPage] Drawing page setup complete")
    
    def _on_draw_mode_changed(self):
        """Handle switching between drawing and image file modes."""
        if self.ImagefileBtn.isChecked():
            # Switch to image mode
            # Get layout from whichever widget has a parent
            layout = None
            index = 0
            if self.drawImageWidget.parent() is not None:
                layout = self.drawImageWidget.parent().layout()
                index = layout.indexOf(self.drawImageWidget)
            elif self.drawManualWidget.parent() is not None:
                layout = self.drawManualWidget.parent().layout()
                index = layout.indexOf(self.drawManualWidget)
            
            if layout is None:
                return  # Neither widget has a parent yet, skip
            
            if self.drawManualWidget.parent() is not None:
                layout.removeWidget(self.drawManualWidget)
                self.drawManualWidget.setParent(None)
            
            if self.drawImageWidget.parent() is None:
                layout.insertWidget(index, self.drawImageWidget)
            self.drawImageWidget.show()
            
            # Process image if loaded
            if self.draw_image_path:
                self._process_draw_image()
        
        elif self.DrawingBtn.isChecked():
            # Switch to manual drawing mode
            # Get layout from whichever widget has a parent
            layout = None
            index = 0
            if self.drawManualWidget.parent() is not None:
                layout = self.drawManualWidget.parent().layout()
                index = layout.indexOf(self.drawManualWidget)
            elif self.drawImageWidget.parent() is not None:
                layout = self.drawImageWidget.parent().layout()
                index = layout.indexOf(self.drawImageWidget)
            
            if layout is None:
                return  # Neither widget has a parent yet, skip
            
            if self.drawImageWidget.parent() is not None:
                layout.removeWidget(self.drawImageWidget)
                self.drawImageWidget.setParent(None)
            
            if self.drawManualWidget.parent() is None:
                layout.insertWidget(index, self.drawManualWidget)
            self.drawManualWidget.show()
            
            # Process manual drawing if exists
            if self.drawManualWidget.has_polylines():
                self._process_manual_drawing()
    
    def _on_draw_image_loaded(self, file_path):
        """Handle image being loaded/dropped."""
        if not self.ImagefileBtn.isChecked():
            return
        
        self.draw_image_path = file_path
        print(f"[DrawPage] Image loaded: {file_path}")
        self._process_draw_image()
    
    def _on_manual_drawing_updated(self):
        """Handle manual drawing updates."""
        if not self.DrawingBtn.isChecked():
            return
        
        self._process_manual_drawing()
    
    def _on_undo_drawing(self):
        """Handle undo button click - remove last polyline."""
        self.drawManualWidget.undo_last_polyline()
    
    def _on_draw_parameter_changed(self):
        """Handle edge detection parameter changes."""
        # Update labels
        self.drawCannyLowLabel.setText(str(self.drawCannyLowSlider.value()))
        self.drawCannyHighLabel.setText(str(self.drawCannyHighSlider.value()))
        self.drawKernelLabel.setText(str(self.drawKernelSlider.value()))
        self.drawMergeLabel.setText(str(self.drawMergeSlider.value()))
        
        # Only reprocess if in image mode and image is loaded
        if self.ImagefileBtn.isChecked() and self.draw_image_path:
            self._process_draw_image()
        elif self.DrawingBtn.isChecked() and self.drawManualWidget.has_polylines():
            # Z height changes affect manual mode too
            self._process_manual_drawing()
    
    def _on_draw_workspace_changed(self):
        """Handle workspace parameter changes."""
        # Reprocess based on current mode
        if self.ImagefileBtn.isChecked() and self.draw_image_path:
            self._process_draw_image()
        elif self.DrawingBtn.isChecked() and self.drawManualWidget.has_polylines():
            self._process_manual_drawing()
    
    def _process_draw_image(self):
        """Process the current image with current settings."""
        if not self.draw_image_path:
            return
        
        try:
            # Get workspace parameters
            try:
                center_x = float(self.drawCenterXLineEdit.text())
                center_y = float(self.drawCenterYLineEdit.text())
                square_size = float(self.drawLengthLineEdit.text())
                drawing_z = float(self.drawZLineEdit.text())
                pen_lift_z = float(self.drawZLiftLineEdit.text())
            except ValueError:
                print("[DrawPage] Invalid workspace parameters")
                return
            
            # Create converter with current parameters
            self.draw_converter = ImageToPolylines(
                image_path=self.draw_image_path,
                drawing_z=drawing_z,  # Z when drawing (pen down)
                pen_lift_z=pen_lift_z,  # Z when moving between polylines (pen up)
                square_size=square_size,
                center_x=center_x,
                center_y=center_y,
                canny_threshold1=self.drawCannyLowSlider.value(),
                canny_threshold2=self.drawCannyHighSlider.value(),
                min_contour_length=10,
                closing_kernel_size=self.drawKernelSlider.value(),
                endpoint_merge_distance=float(self.drawMergeSlider.value()),
                simplification_epsilon=1.5  # Douglas-Peucker simplification tolerance
            )
            
            # Process image
            self.draw_converter.load_and_process_image()
            self.draw_converter.extract_polylines()
            self.draw_converter.scale_to_workspace()
            
            # Get polylines with pen control (3D waypoints with pen lift at start/end)
            self.draw_polylines = self.draw_converter.get_waypoints_with_pen_control()
            
            # Update visualization (use 2D scaled polylines for display)
            self.drawPolylineWidget.update_polylines(
                self.draw_converter.scaled_polylines,
                square_size,
                center_x,
                center_y
            )
            
            print(f"[DrawPage] Processed {len(self.draw_polylines)} polylines")
            
        except Exception as e:
            print(f"[DrawPage] Error processing image: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_manual_drawing(self):
        """Process manually drawn polylines with scaling and simplification."""
        if not self.drawManualWidget.has_polylines():
            print("[DrawPage] No manual polylines to process")
            return
        
        try:
            # Get workspace parameters
            try:
                center_x = float(self.drawCenterXLineEdit.text())
                center_y = float(self.drawCenterYLineEdit.text())
                square_size = float(self.drawLengthLineEdit.text())
                drawing_z = float(self.drawZLineEdit.text())
                pen_lift_z = float(self.drawZLiftLineEdit.text())
            except ValueError:
                print("[DrawPage] Invalid workspace parameters")
                return
            
            # Get raw polylines from manual widget (in widget coordinates)
            raw_polylines = self.drawManualWidget.get_polylines_as_numpy()
            
            if not raw_polylines:
                return
            
            # Get widget dimensions
            widget_width = self.drawManualWidget.width()
            widget_height = self.drawManualWidget.height()
            
            # Calculate scaling factor (maintain aspect ratio)
            scale_x = square_size / widget_width
            scale_y = square_size / widget_height
            scale = min(scale_x, scale_y)  # Use smaller scale to fit within square
            
            # Calculate the scaled dimensions
            scaled_width = widget_width * scale
            scaled_height = widget_height * scale
            
            # Calculate offset to center the scaled drawing in the square
            offset_x = center_x - scaled_width / 2
            offset_y = center_y - scaled_height / 2
            
            # Apply simplification and scaling to each polyline
            scaled_polylines = []
            original_point_count = 0
            simplified_point_count = 0
            simplification_epsilon = 1.5  # Tolerance for simplification
            
            for polyline in raw_polylines:
                # Apply Douglas-Peucker simplification
                original_point_count += len(polyline)
                if simplification_epsilon > 0:
                    simplified = cv2.approxPolyDP(polyline, simplification_epsilon, closed=False)
                    simplified = simplified.reshape(-1, 2)
                    simplified_point_count += len(simplified)
                else:
                    simplified = polyline
                    simplified_point_count += len(simplified)
                
                # Scale and flip Y (widget Y goes down, robot Y goes up)
                scaled = simplified * scale
                scaled[:, 1] = scaled_height - scaled[:, 1]
                
                # Translate to center position
                scaled[:, 0] += offset_x
                scaled[:, 1] += offset_y
                
                scaled_polylines.append(scaled)
            
            # Print simplification statistics
            if simplification_epsilon > 0 and original_point_count > 0:
                reduction = 100 * (1 - simplified_point_count / original_point_count)
                print(f"[Simplification] Reduced points from {original_point_count} to {simplified_point_count} ({reduction:.1f}% reduction)")
            
            # Convert to 3D waypoints with pen control
            self.draw_polylines = []
            for polyline in scaled_polylines:
                polyline_waypoints = []
                
                # Start with pen lifted at the first point (approach position)
                first_x, first_y = polyline[0]
                polyline_waypoints.append((first_x, first_y, pen_lift_z))
                
                # Add all points in the polyline at drawing height
                for point in polyline:
                    x, y = point
                    polyline_waypoints.append((x, y, drawing_z))
                
                # End with pen lifted at the last point
                last_x, last_y = polyline[-1]
                polyline_waypoints.append((last_x, last_y, pen_lift_z))
                
                self.draw_polylines.append(polyline_waypoints)
            
            # Update visualization
            self.drawPolylineWidget.update_polylines(
                scaled_polylines,
                square_size,
                center_x,
                center_y
            )
            
            print(f"[DrawPage] Processed {len(self.draw_polylines)} manual polylines")
            
        except Exception as e:
            print(f"[DrawPage] Error processing manual drawing: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_start_drawing(self):
        """Start executing drawing by planning and sending polylines one by one."""
        if self.draw_executing:
            print("[DrawPage] Already executing drawing")
            return
        
        if not self.draw_polylines:
            print("[DrawPage] No polylines to draw")
            return
        
        if not self.serial_connection or not self.serial_connection.is_open:
            print("[DrawPage] Serial connection not open")
            return
        
        print(f"[DrawPage] Starting drawing with {len(self.draw_polylines)} polylines")
        
        self.draw_executing = True
        self.draw_current_polyline_index = 0
        self.startDrawingBtn.setEnabled(False)
        
        # Start drawing the first polyline
        self._draw_next_polyline()
    
    def _draw_next_polyline(self):
        """Plan and send the next polyline to the robot."""
        if self.draw_current_polyline_index >= len(self.draw_polylines):
            # Finished all polylines
            print("[DrawPage] Drawing complete!")
            self.draw_executing = False
            self.startDrawingBtn.setEnabled(True)
            return
        
        # Get current polyline (already 3D with pen control)
        polyline = self.draw_polylines[self.draw_current_polyline_index]
        print(f"[DrawPage] Drawing polyline {self.draw_current_polyline_index + 1}/{len(self.draw_polylines)} ({len(polyline)} points)")
        
        # Polyline is already a list of (x, y, z) tuples with pen control
        # Extract drawing z (minimum z in the polyline, which is the pen-down position)
        z_values = [z for x, y, z in polyline]
        drawing_z = min(z_values)
        # Set threshold with some margin to account for feedback variations
        # but exclude pen lift transitions (which are at higher z)
        self.draw_z_threshold = drawing_z + 5.0  # Only plot points within 5mm of drawing height
        print(f"[DrawPage] Drawing z={drawing_z:.1f}, threshold={self.draw_z_threshold:.1f}")
        
        # Convert to list of lists for planner
        waypoint_list = [[x, y, z] for x, y, z in polyline]
        
        # Create trajectory planner (same settings as chess)
        planner = TrajectoryPlanner(
            joints_max_speeds=np.array([20.0, 15.0, 15.0]),
            joints_max_accel=np.array([60.0, 20.0, 20.0]),
            dt_sample=1e-3,
            inverse_kinematics_func=lambda x, y, z, mu: [
                angle * 180.0/np.pi for angle in inverse_kinematics(x, y, z, mu=mu)
            ],
            mu_func=lambda x, y, z: 0.0,  # Fixed mu for drawing
            gripper_actions=None,  # No gripper actions during drawing
            max_waypoint_count=100,
            min_waypoint_dt=0.02
        )
        
        try:
            # Clear live drawing widget at start of first polyline
            if self.draw_current_polyline_index == 0:
                self.drawLiveWidget_new.clear()
                # Set workspace parameters from GUI
                try:
                    center_x = float(self.drawCenterXLineEdit.text())
                    center_y = float(self.drawCenterYLineEdit.text())
                    square_size = float(self.drawLengthLineEdit.text())
                    self.drawLiveWidget_new.set_workspace(square_size, center_x, center_y)
                except ValueError:
                    pass  # Use defaults if parsing fails
            
            # Plan trajectory from waypoint list
            planner.plan_trajectory(
                waypoint_list=waypoint_list,
                use_waypoint_list=True
            )
            
            # Get Arduino command
            command = planner.get_arduino_command()
            
            # Send command
            print(f"[DrawPage] Sending waypoint command ({len(command)} chars)")
            self.serial_connection.write(f"{command}\n".encode())
            
            # Enable live plotting and clear point buffer
            self.draw_point_buffer.clear()
            self.draw_plotting_active = True
            print(f"[DrawPage] Live plotting enabled (z_threshold={self.draw_z_threshold:.1f})")
            
            # Wait for 'D' response before continuing
            # The serial reader will call _on_draw_polyline_complete when 'D' is received
            
        except Exception as e:
            print(f"[DrawPage] Error planning/sending polyline: {e}")
            import traceback
            traceback.print_exc()
            self.draw_executing = False
            self.startDrawingBtn.setEnabled(True)
    
    def _on_draw_polyline_complete(self):
        """Called when Arduino sends 'D' indicating polyline is complete."""
        if not self.draw_executing:
            return
        
        # Disable live plotting when polyline is complete
        self.draw_plotting_active = False
        
        # Flush remaining buffered points
        self._update_live_drawing_from_buffer()
        
        print(f"[DrawPage] Polyline {self.draw_current_polyline_index + 1} complete, plotting disabled")
        
        # Move to next polyline
        self.draw_current_polyline_index += 1
        self._draw_next_polyline()
    
    def _update_live_drawing_from_buffer(self):
        """Update live drawing widget with buffered points and robot position."""
        # Update robot position (green dot) only when actively drawing
        self.drawLiveWidget_new.update_robot_position(
            self.current_x, 
            self.current_y, 
            show=self.draw_executing
        )
        
        if self.draw_point_buffer:
            # Add all buffered points at once (much more efficient than one by one)
            self.drawLiveWidget_new.add_points(self.draw_point_buffer.copy())
            
            # Clear buffer
            points_added = len(self.draw_point_buffer)
            self.draw_point_buffer.clear()
            
            # Optional: print debug info
            # print(f"[DrawPage] Added {points_added} buffered points to live drawing")
        elif self.draw_executing:
            # Even if no points to add, redraw to update the robot position when drawing
            self.drawLiveWidget_new._redraw()
    

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
    
    def _on_play_exec(self):
        """Send waypoints to Arduino when play button is pressed in Execute mode"""
        # Only allow in Execute mode
        if self.record_mode:
            print("Cannot play in Record mode")
            return
        
        # Check if connected to Arduino
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        try:
            # If already executing, send resume command
            if self.executing_trajectory:
                command = "o\n"
                self.serial_connection.write(command.encode())
                print(f"Sent resume: {command.strip()}")
            else:
                # Check if we have waypoints loaded
                if not self.waypoints:
                    print("No waypoints loaded")
                    return
                
                # Format waypoints into command string
                # Format: n<count>,x<x>y<y>z<z>m<mu>g<gripper>,x<x>y<y>z<z>m<mu>g<gripper>,...
                waypoint_count = len(self.waypoints)
                command_parts = [f"n{waypoint_count}"]
                
                for x, y, z, mu, gripper in self.waypoints:
                    # Format each waypoint: x<x>y<y>z<z>m<mu>g<gripper>
                    waypoint_str = f"x{x:.1f}y{y:.1f}z{z:.1f}m{mu}g{gripper}"
                    command_parts.append(waypoint_str)
                
                # Join with commas
                command = ",".join(command_parts) + "\n"
                
                self.serial_connection.write(command.encode())
                print(f"Sent trajectory: {command.strip()}")
                
                # Set flag to indicate we're now executing
                self.executing_trajectory = True
                
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _on_pause_exec(self):
        """Send pause command to Arduino when pause button is pressed in Execute mode"""
        # Only allow in Execute mode
        if self.record_mode:
            print("Cannot pause in Record mode")
            return
        
        # Check if connected to Arduino
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        try:
            command = "p\n"
            self.serial_connection.write(command.encode())
            print(f"Sent pause: {command.strip()}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _on_stop_exec(self):
        """Send stop command to Arduino when stop button is pressed in Execute mode"""
        # Only allow in Execute mode
        if self.record_mode:
            print("Cannot stop in Record mode")
            return
        
        # Check if connected to Arduino
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        try:
            command = "s\n"
            self.serial_connection.write(command.encode())
            print(f"Sent stop: {command.strip()}")
            
            # Reset executing flag
            self.executing_trajectory = False
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _on_flush_exec(self):
        """Flush everything: send stop signal, clear graph, list, and reset flags"""
        # Send stop command to Arduino
        if self.serial_connection and self.serial_connection.is_open:
            try:
                command = "s\n"
                self.serial_connection.write(command.encode())
                print(f"Sent stop (flush): {command.strip()}")
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                self._on_disconnect_com()
        
        # Clear all waypoints
        self._clear_all_waypoints()
        
        # Reset executing flag
        self.executing_trajectory = False
        
        print("Flushed: Cleared waypoints, graph, and reset execution state")
    
    def _on_restart_exec(self):
        """Restart execution: reset pause and send waypoint list again"""
        # Only allow in Execute mode
        if self.record_mode:
            print("Cannot restart in Record mode")
            return
        
        # Check if we have waypoints loaded
        if not self.waypoints:
            print("No waypoints to restart")
            return
        
        # Check if connected to Arduino
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        try:
            # Format waypoints into command string
            # Format: n<count>,x<x>y<y>z<z>m<mu>g<gripper>,x<x>y<y>z<z>m<mu>g<gripper>,...
            waypoint_count = len(self.waypoints)
            command_parts = [f"n{waypoint_count}"]
            
            for x, y, z, mu, gripper in self.waypoints:
                # Format each waypoint: x<x>y<y>z<z>m<mu>g<gripper>
                waypoint_str = f"x{x:.1f}y{y:.1f}z{z:.1f}m{mu}g{gripper}"
                command_parts.append(waypoint_str)
            
            # Join with commas
            command = ",".join(command_parts) + "\n"
            
            self.serial_connection.write(command.encode())
            print(f"Sent restart trajectory: {command.strip()}")
            
            # Set flag to indicate we're now executing
            self.executing_trajectory = True
            
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()

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
        """Disconnect from the current COM port and reset all values to defaults"""
        # Stop timers
        self.serial_read_timer.stop()
        self.command_debounce_timer.stop()
        self.gripper_debounce_timer.stop()
        self.gamma_debounce_timer.stop()
        
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                print(f"Disconnected from {self.connected_port}")
            except Exception as e:
                print(f"Error disconnecting: {e}")
        
        self.serial_connection = None
        self.connected_port = None
        self.serial_buffer = ""  # Clear buffer
        
        # Reset executing trajectory flag
        self.executing_trajectory = False
        
        # Reset all sliders and state to defaults
        self._reset_sliders_to_defaults()
        
        # Reset gripper slider to default
        gripper_def = self.params.get("gripperdef", 90)
        gripper_min = self.params.get("grippermin", 0)
        gripper_max = self.params.get("grippermax", 180)
        default_percentage = int(((gripper_def - gripper_min) / (gripper_max - gripper_min)) * 100)
        self.griperSlider.blockSignals(True)
        self.griperSlider.setValue(default_percentage)
        self.griperSlider.blockSignals(False)
        self.last_gripper_percentage = default_percentage
        
        # Update 3D viewer to default state
        if self.robot_viewer:
            self.robot_viewer.set_theta(0)
            self.robot_viewer.set_alpha(0)
            self.robot_viewer.set_beta(0)
            self.robot_viewer.set_mu(0)
            gripper_mapped = (default_percentage / 100.0) * 85.0
            self.robot_viewer.set_gripper(gripper_mapped)
        
        self._update_com_button_states()
    
    def _on_quit_app(self):
        """Quit the application"""
        # Disconnect COM port before quitting
        self._on_disconnect_com()
        # Close the application
        QApplication.quit()
    
    def _on_abort(self):
        """Send abort command 's' to Arduino"""
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        try:
            command = "s\n"
            self.serial_connection.write(command.encode())
            print(f"Sent abort: {command.strip()}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _on_dev_send(self):
        """Send content of devLineEdit to Arduino"""
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        # Get text from line edit
        dev_text = self.devLineEdit.text().strip()
        if not dev_text:
            print("Dev line edit is empty")
            return
        
        try:
            # Add newline if not present
            if not dev_text.endswith('\n'):
                dev_text += '\n'
            self.serial_connection.write(dev_text.encode())
            print(f"Sent dev command: {dev_text.strip()}")
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _update_com_button_states(self):
        """Update button enabled/disabled states based on connection status"""
        is_connected = bool(self.serial_connection and self.serial_connection.is_open)

        self.connectBtn.setEnabled(not is_connected)
        self.disconnectBtn.setEnabled(is_connected)
        self.refreshBtn.setEnabled(not is_connected)

        # Reflect the connection change on the chess label (drop any stale result)
        if not self.currently_playing_chess:
            self.chess_result_text = None
        self._update_chess_label()
    
    def _on_reset_left(self):
        """Send reset left command and reset all sliders to default values"""
        # Send serial command 'rl'
        if self.serial_connection and self.serial_connection.is_open:
            try:
                command = "rl\n"
                self.serial_connection.write(command.encode())
                print(f"Sent: {command.strip()}")
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                self._on_disconnect_com()
        
        # Reset all sliders to default values
        self._reset_sliders_to_defaults()
    
    def _on_reset_right(self):
        """Send reset right command and reset all sliders to default values"""
        # Send serial command 'rr'
        if self.serial_connection and self.serial_connection.is_open:
            try:
                command = "rr\n"
                self.serial_connection.write(command.encode())
                print(f"Sent: {command.strip()}")
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                self._on_disconnect_com()
        
        # Reset all sliders to default values
        self._reset_sliders_to_defaults()
    
    def _on_home_command(self):
        """Send home command: it0a0b0 by setting targets on ring sliders"""
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Not connected to Arduino")
            return
        
        # Set targets to home position (0, 0, 0) - this triggers the command via valueChanged
        self.theta_slider.setTargetValue(0)
        self.alpha_slider.setTargetValue(0)
        self.beta_slider.setTargetValue(0)
        
        print("Home targets set: θ=0° α=0° β=0°")
    
    def _reset_sliders_to_defaults(self):
        """Reset all sliders to their default values from params.json"""
        # Reset Cartesian sliders (X, Y, Z)
        self.xSlider.blockSignals(True)
        self.xSlider.setValue(self.params["xdef"])
        self.xSlider.blockSignals(False)
        self.xlineEdit.setText(str(self.params["xdef"]))
        
        self.ySlider.blockSignals(True)
        self.ySlider.setValue(self.params["ydef"])
        self.ySlider.blockSignals(False)
        self.ylineEdit.setText(str(self.params["ydef"]))
        
        self.zSlider.blockSignals(True)
        self.zSlider.setValue(self.params["zdef"])
        self.zSlider.blockSignals(False)
        self.zlineEdit.setText(str(self.params["zdef"]))
        
        # Reset ring sliders (theta, alpha, beta)
        self.theta_slider.blockSignals(True)
        self.theta_slider.setValue(0)
        self.theta_slider.clearTarget()
        self.theta_slider.blockSignals(False)
        
        self.alpha_slider.blockSignals(True)
        self.alpha_slider.setValue(0)
        self.alpha_slider.clearTarget()
        self.alpha_slider.blockSignals(False)
        
        self.beta_slider.blockSignals(True)
        self.beta_slider.setValue(0)
        self.beta_slider.clearTarget()
        self.beta_slider.blockSignals(False)
        
        # Reset mu slider and line edit
        mu_default = self.params.get("mudef", 0)
        self.muSlider.blockSignals(True)
        self.muSlider.setValue(mu_default)
        self.muSlider.blockSignals(False)
        self.mulineEdit.setText(str(mu_default))
        self.muLabel.setText(str(mu_default))
        
        # Reset gamma slider
        gamma_default = self.params.get("gammadef", 0)
        self.gamma_slider.blockSignals(True)
        self.gamma_slider.setValue(gamma_default)
        self.gamma_slider.blockSignals(False)
        
        # Update internal state variables
        self.current_mu = mu_default
        self.current_gamma = gamma_default
        self.current_alpha = 0
        self.current_x = self.params["xdef"]
        self.current_y = self.params["ydef"]
        self.current_z = self.params["zdef"]
        
        # Clear pending slider values to prevent old values from being sent
        self.pending_theta = None
        self.pending_alpha = None
        self.pending_beta = None
        self.pending_gamma = None
        self.pending_gripper = None
        
        # Set control mode to mu
        self.controlling_mu = True
        
        print("All sliders reset to default values")
    
    def _on_ring_slider_changed(self, slider_name, value):
        """Handle ring slider changes with debouncing"""
        # Store the pending value for the changed slider
        if slider_name == 'theta':
            self.pending_theta = value
        elif slider_name == 'alpha':
            self.pending_alpha = value
        elif slider_name == 'beta':
            self.pending_beta = value
        
        # Update pending values for other sliders based on their targets
        # This ensures all three sliders' targets are sent together
        if slider_name != 'theta':
            if self.theta_slider.targetValue() is not None:
                self.pending_theta = self.theta_slider.targetValue()
            elif self.pending_theta is None:
                self.pending_theta = self.theta_slider.value()
        
        if slider_name != 'alpha':
            if self.alpha_slider.targetValue() is not None:
                self.pending_alpha = self.alpha_slider.targetValue()
            elif self.pending_alpha is None:
                self.pending_alpha = self.alpha_slider.value()
        
        if slider_name != 'beta':
            if self.beta_slider.targetValue() is not None:
                self.pending_beta = self.beta_slider.targetValue()
            elif self.pending_beta is None:
                self.pending_beta = self.beta_slider.value()
        
        # Restart the debounce timer (single-shot)
        self.command_debounce_timer.start()
    
    def _send_ring_slider_command(self):
        """Send ring slider command to Arduino after debounce period"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
        
        # Get values to send: use pending if set, otherwise use target (green knob), 
        # and only fall back to current value (blue knob) if no target is set
        if self.pending_theta is not None:
            theta = self.pending_theta
        elif self.theta_slider.targetValue() is not None:
            theta = self.theta_slider.targetValue()
        else:
            theta = self.theta_slider.value()
        
        if self.pending_alpha is not None:
            alpha = self.pending_alpha
        elif self.alpha_slider.targetValue() is not None:
            alpha = self.alpha_slider.targetValue()
        else:
            alpha = self.alpha_slider.value()
        
        if self.pending_beta is not None:
            beta = self.pending_beta
        elif self.beta_slider.targetValue() is not None:
            beta = self.beta_slider.targetValue()
        else:
            beta = self.beta_slider.value()
        
        # Format command: 'it<theta>a<alpha>b<beta>'
        command = f"it{theta:.2f}a{alpha:.2f}b{beta:.2f}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")  # Debug output
            
            # Update current_alpha for mu/gamma calculations
            self.current_alpha = alpha
            
            # Calculate and update XYZ position using direct kinematics
            theta_rad = np.radians(theta)
            alpha_rad = np.radians(alpha)
            beta_rad = np.radians(beta)
            
            # Calculate gamma based on control mode
            if self.controlling_mu:
                gamma_rad = mu_to_gamma(np.radians(self.current_mu), alpha_rad)
                # Update gamma slider since it depends on alpha
                gamma_degrees = np.degrees(gamma_rad)
                self.current_gamma = gamma_degrees
                self.gamma_slider.blockSignals(True)
                self.gamma_slider.setValue(gamma_degrees)
                self.gamma_slider.blockSignals(False)
            else:
                gamma_rad = np.radians(self.current_gamma)
            
            position = direct_kinematics(theta_rad, alpha_rad, beta_rad, gamma_rad)
            self.current_x = position[0]
            self.current_y = position[1]
            self.current_z = position[2]
            
            # Update XYZ labels
            self.xLabel.setText(f"{self.current_x:.1f}")
            self.yLabel.setText(f"{self.current_y:.1f}")
            self.zLabel.setText(f"{self.current_z:.1f}")
            
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _on_gripper_slider_changed(self, value):
        """Handle gripper slider changes with debouncing"""
        # Store the pending value
        self.pending_gripper = value
        
        # Restart the debounce timer (single-shot)
        self.gripper_debounce_timer.start()
    
    def _send_gripper_command(self):
        """Send gripper command to Arduino after debounce period"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
        
        # Get current value from slider (use pending if set, otherwise current)
        gripper_percentage = self.pending_gripper if self.pending_gripper is not None else self.griperSlider.value()
        
        # Format command: 'g<percentage>'
        command = f"g{gripper_percentage}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")  # Debug output
            
            # Store last sent gripper percentage
            self.last_gripper_percentage = gripper_percentage
            
            # Map gripper percentage from 0-100 to 0-85 for 3D viewer
            gripper_mapped = (gripper_percentage / 100.0) * 85.0
            
            # Update 3D viewer with mapped gripper value
            if self.robot_viewer:
                self.robot_viewer.set_gripper(gripper_mapped)
                
        except serial.SerialException as e:
            print(f"Serial error: {e}")
            self._on_disconnect_com()
    
    def _on_gamma_slider_changed(self, value):
        """Handle gamma slider changes with debouncing"""
        # Store the pending value
        self.pending_gamma = value
        
        # Restart the debounce timer (single-shot)
        self.gamma_debounce_timer.start()
    
    def _send_gamma_command(self):
        """Send gamma command to Arduino after debounce period"""
        if not self.serial_connection or not self.serial_connection.is_open:
            return
        
        # Get current value from slider (use pending if set, otherwise current)
        gamma_value = self.pending_gamma if self.pending_gamma is not None else self.gamma_slider.value()
        
        # Convert to integer and format command: 'h<gamma>'
        gamma_int = int(gamma_value)
        command = f"h{gamma_int}\n"
        
        try:
            self.serial_connection.write(command.encode())
            print(f"Sent: {command.strip()}")  # Debug output
            
            # Set flag to indicate we're controlling gamma
            self.controlling_mu = False
            self.current_gamma = gamma_int
            
            # Calculate mu from gamma using current alpha
            mu_value = gamma_to_mu(np.radians(gamma_int), np.radians(self.current_alpha))
            mu_degrees = np.degrees(mu_value)
            self.current_mu = mu_degrees
            
            # Update mu slider without triggering its change event
            self.muSlider.blockSignals(True)
            self.muSlider.setValue(int(mu_degrees))
            self.muSlider.blockSignals(False)
            
            # Update mu line edit
            self.mulineEdit.blockSignals(True)
            self.mulineEdit.setText(str(int(mu_degrees)))
            self.mulineEdit.blockSignals(False)
            
            # Update mu label
            self.muLabel.setText(str(int(mu_degrees)))
            
            # Calculate and update XYZ position using direct kinematics
            theta_rad = np.radians(self.theta_slider.value())
            alpha_rad = np.radians(self.alpha_slider.value())
            beta_rad = np.radians(self.beta_slider.value())
            gamma_rad = np.radians(gamma_int)
            
            position = direct_kinematics(theta_rad, alpha_rad, beta_rad, gamma_rad)
            self.current_x = position[0]
            self.current_y = position[1]
            self.current_z = position[2]
            
            # Update XYZ labels
            self.xLabel.setText(f"{self.current_x:.1f}")
            self.yLabel.setText(f"{self.current_y:.1f}")
            self.zLabel.setText(f"{self.current_z:.1f}")
            
            # Update 3D viewer with calculated mu
            if self.robot_viewer:
                self.robot_viewer.set_mu(mu_degrees)
                
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
                
                # Check for 'D' response during chess (case sensitive, standalone character)
                if self.waiting_for_arduino and 'D' in data:
                    print("[Chess] Received 'D' from Arduino - trajectory complete!")
                    self.waiting_for_arduino = False
                    # Resume piece detection to verify robot's move
                    if self.detector_thread:
                        self.detector_thread.pause_detection = False
                        self.verifying_robot_move = True  # We're verifying robot move, not waiting for user
                        print("[Chess] Resumed piece detection to verify robot move")
                        self._update_chess_label()
                        # Show a tentative arrow of the move the robot just made,
                        # which we are now trying to verify with the camera.
                        self._show_pending_move_arrows()
                
                # Check for 'D' response during drawing
                if self.draw_executing and 'D' in data:
                    print("[DrawPage] Received 'D' from Arduino - polyline complete!")
                    self._on_draw_polyline_complete()
                
                self.serial_buffer += data

                # Extract all complete lines this tick. The robot streams joint
                # feedback far faster than the GUI needs (or can render); every
                # intermediate line is immediately stale. Only the most recent
                # complete line carries useful state, so coalesce to it instead
                # of running the (heavy) per-line UI/3D update on every one. This
                # is what keeps the event loop responsive during a move.
                last_line = None
                while '\n' in self.serial_buffer:
                    line, self.serial_buffer = self.serial_buffer.split('\n', 1)
                    line = line.strip()
                    if line:
                        last_line = line
                if last_line is not None:
                    self._parse_feedback(last_line)
        except (serial.SerialException, UnicodeDecodeError) as e:
            # Check if this is a disconnection error (ClearCommError/PermissionError)
            if isinstance(e, serial.SerialException):
                error_msg = str(e)
                if 'ClearCommError' in error_msg or 'PermissionError' in error_msg or 'device does not recognize' in error_msg:
                    print(f"Serial device disconnected: {e}")
                    # Automatically disconnect
                    self._on_disconnect_com()
                    return
            print(f"Serial read error: {e}")
    
    def _parse_feedback(self, line):
        """Parse Arduino feedback, update 3D viewer and cartesian labels"""
        # Check for waypoint execution notification: "n<i>"
        if line.startswith('n'):
            try:
                # Extract waypoint index
                waypoint_index = int(line[1:])
                self._on_waypoint_execution(waypoint_index)
                return
            except ValueError:
                pass  # Not a valid waypoint notification, continue parsing
        
        # Feedback format: "t<theta>a<alpha>b<beta>h<gamma>g<gripper>" or "d<date>t<theta>a<alpha>b<beta>h<gamma>g<gripper>"
        try:
            # Remove optional date prefix if present
            if line.startswith('d'):
                # Find where theta starts
                t_index = line.find('t')
                if t_index == -1:
                    return
                line = line[t_index:]  # Strip everything before 't'
            
            # Now parse: t<theta>a<alpha>b<beta>h<gamma>g<gripper>
            if not line.startswith('t'):
                return
            
            # Extract theta, alpha, beta
            parts = line[1:].replace('a', ' ').replace('b', ' ').replace('h', ' ').replace('g', ' ').split()
            if len(parts) >= 3:
                theta = float(parts[0])
                alpha = float(parts[1])
                beta = float(parts[2])
                
                # Extract gamma if present
                gamma = None
                if len(parts) >= 4:
                    gamma = float(parts[3])
                
                # Extract gripper if present
                gripper = None
                if len(parts) >= 5:
                    gripper = float(parts[4])
                
                # Store current alpha for mu/gamma conversion
                self.current_alpha = alpha
                
                # Convert theta to 0-360 degree range for slider
                # Arduino may send theta in -180 to 180 range, convert to 0-360
                theta_360 = theta % 360
                if theta_360 < 0:
                    theta_360 += 360
                
                # Update ring sliders with received values
                self.theta_slider.blockSignals(True)
                self.theta_slider.setValue(theta_360)
                self.theta_slider.blockSignals(False)
                
                self.alpha_slider.blockSignals(True)
                self.alpha_slider.setValue(alpha)
                self.alpha_slider.blockSignals(False)
                
                self.beta_slider.blockSignals(True)
                self.beta_slider.setValue(beta)
                self.beta_slider.blockSignals(False)
                
                # Update prohibited zones based on feedback values
                self._update_alpha_prohibited_zone()
                self._update_beta_prohibited_zone()
                
                # Clear targets if robot has reached them (within 1 degree tolerance)
                if self.theta_slider.targetValue() is not None:
                    if abs(self.theta_slider.targetValue() - theta_360) < 1.0:
                        self.theta_slider.clearTarget()
                
                if self.alpha_slider.targetValue() is not None:
                    if abs(self.alpha_slider.targetValue() - alpha) < 1.0:
                        self.alpha_slider.clearTarget()
                
                if self.beta_slider.targetValue() is not None:
                    if abs(self.beta_slider.targetValue() - beta) < 1.0:
                        self.beta_slider.clearTarget()
                
                # Update gamma slider and internal state if received
                if gamma is not None:
                    self.current_gamma = gamma
                    self.gamma_slider.blockSignals(True)
                    self.gamma_slider.setValue(int(gamma))
                    self.gamma_slider.blockSignals(False)
                
                # Update gripper slider if received
                if gripper is not None:
                    # Convert gripper angle (0-180) to percentage (0-100)
                    gripper_min = self.params.get("grippermin", 0)
                    gripper_max = self.params.get("grippermax", 180)
                    gripper_percentage = int(((gripper - gripper_min) / (gripper_max - gripper_min)) * 100)
                    gripper_percentage = max(0, min(100, gripper_percentage))  # Clamp to 0-100
                    
                    self.griperSlider.blockSignals(True)
                    self.griperSlider.setValue(gripper_percentage)
                    self.griperSlider.blockSignals(False)
                    self.last_gripper_percentage = gripper_percentage
                    self.pending_gripper = gripper_percentage
                
                # Convert degrees to radians for kinematics
                theta_rad = np.radians(theta)
                alpha_rad = np.radians(alpha)
                beta_rad = np.radians(beta)
                
                # Use received gamma if available, otherwise calculate from mu
                if gamma is not None:
                    gamma_rad = np.radians(gamma)
                    # Update mu based on received gamma
                    mu_value = gamma_to_mu(gamma_rad, alpha_rad)
                    mu_degrees = np.degrees(mu_value)
                    self.current_mu = mu_degrees
                    # Update mu slider without triggering events
                    self.muSlider.blockSignals(True)
                    self.muSlider.setValue(int(mu_degrees))
                    self.muSlider.blockSignals(False)
                    self.mulineEdit.blockSignals(True)
                    self.mulineEdit.setText(str(int(mu_degrees)))
                    self.mulineEdit.blockSignals(False)
                    self.muLabel.setText(str(int(mu_degrees)))
                else:
                    # Calculate gamma based on control mode
                    if self.controlling_mu:
                        gamma_rad = mu_to_gamma(np.radians(self.current_mu), alpha_rad)
                    else:
                        gamma_rad = np.radians(self.current_gamma)
                
                # Calculate cartesian position using direct kinematics
                position = direct_kinematics(theta_rad, alpha_rad, beta_rad, gamma_rad)
                self.current_x = position[0]
                self.current_y = position[1]
                self.current_z = position[2]
                
                # Update cartesian labels with actual position
                self.xLabel.setText(f"{self.current_x:.1f}")
                self.yLabel.setText(f"{self.current_y:.1f}")
                self.zLabel.setText(f"{self.current_z:.1f}")
                
                # Update 3D viewer with actual positions from Arduino (single
                # pose update -> one transform rebuild + one throttled render).
                if self.robot_viewer:
                    # Map gripper angle from 0-180 to 0-85 for 3D viewer
                    gripper_mapped = (gripper / 180.0) * 85.0 if gripper is not None else None
                    self.robot_viewer.set_pose(theta=theta_360, alpha=alpha,
                                               beta=beta, mu=self.current_mu,
                                               gripper=gripper_mapped)
                
                # Buffer point for live drawing if plotting is active and z is low (pen down)
                if self.draw_plotting_active and self.current_z < self.draw_z_threshold:
                    self.draw_point_buffer.append((self.current_x, self.current_y))
                
                # print(f"Feedback: θ={theta:.2f}° α={alpha:.2f}° β={beta:.2f}° γ={gamma if gamma is not None else 'N/A'}° grip={gripper if gripper is not None else 'N/A'}° | x={self.current_x:.1f} y={self.current_y:.1f} z={self.current_z:.1f}")
        except (ValueError, IndexError) as e:
            print(f"Parse error: {e} - Line: {line}")
    
    def _on_waypoint_execution(self, waypoint_index):
        """Handle waypoint execution notification from Arduino"""
        # Check if waypoint index is valid
        if 0 <= waypoint_index < len(self.waypoints):
            # Select the waypoint in the list widget
            self.positionlistWidget.blockSignals(True)  # Prevent selection handler from firing
            self.positionlistWidget.setCurrentRow(waypoint_index)
            self.positionlistWidget.blockSignals(False)
            
            # Get the waypoint data
            x, y, z, mu, gripper = self.waypoints[waypoint_index]
            
            # Update 3D viewer with mu and gripper values (single pose update)
            if self.robot_viewer:
                # Map gripper percentage from 0-100 to 0-85 for 3D viewer
                gripper_mapped = (gripper / 100.0) * 85.0
                self.robot_viewer.set_pose(mu=mu, gripper=gripper_mapped)
            
            # Update current mu and gripper values
            self.current_mu = mu
            self.last_gripper_percentage = gripper
            
            print(f"Executing waypoint {waypoint_index}: mu={mu}°, gripper={gripper}%")
        else:
            print(f"Invalid waypoint index received: {waypoint_index}")
    
    def _on_chess_play_toggle(self):
        """Handle play/forfeit button toggle."""
        if not self.currently_playing_chess:
            # Start chess game
            self._start_chess_game()
        else:
            # Forfeit and reset
            self._forfeit_chess_game()
    
    def _start_chess_game(self):
        """Initialize and start a chess game."""
        print("\n[Chess] Starting chess game...")
        
        # Determine user color from chess_mode buttons
        if self.chess_mode_whiteBtn.isChecked():
            user_color = chess.WHITE
            robot_color = chess.BLACK
        elif self.chess_mode_blackBtn.isChecked():
            user_color = chess.BLACK
            robot_color = chess.WHITE
        else:
            # Default to white if none selected
            QMessageBox.warning(self, "Chess", "Please select your color (White/Black) first!")
            return
        
        # Check if CV is running
        if not self.detector_running:
            QMessageBox.warning(self, "Chess", "Please start the camera (Initialize button) first!")
            return
        
        # Check if serial is connected
        if not self.serial_connection or not self.serial_connection.is_open:
            QMessageBox.warning(self, "Chess", "Please connect to Arduino first!")
            return
        
        # Read Stockfish difficulty (skill level 0-20) from the line edit
        skill_level = 10  # default if missing/invalid
        difficulty_text = self.chess_difficultyLineEdit.text().strip()
        if difficulty_text:
            try:
                skill_level = int(difficulty_text)
                if not 0 <= skill_level <= 20:
                    skill_level = max(0, min(20, skill_level))
                    QMessageBox.warning(self, "Chess", f"Difficulty must be between 0 and 20. Clamped to {skill_level}.")
            except ValueError:
                QMessageBox.warning(self, "Chess", "Difficulty must be an integer between 0 and 20. Using default (10).")
                skill_level = 10

        # Initialize ChessEngine
        try:
            if sys.platform == "linux":
                stockfish_path = str(_bundle_base_dir() / ".stockfish" / "stockfish-ubuntu-x86-64")
            else:
                stockfish_path = str(_bundle_base_dir() / ".stockfish" / "stockfish-windows-x86-64-avx2")
            # Packaging can drop the executable bit on bundled binaries; restore it.
            try:
                os.chmod(stockfish_path, 0o755)
            except OSError:
                pass
            self.chess_engine = ChessEngine(
                stockfish_path=stockfish_path,
                robot_color=robot_color,
                skill_level=skill_level
            )
            print(f"[Chess] ChessEngine initialized - Robot plays: {'White' if robot_color == chess.WHITE else 'Black'} (skill={skill_level})")
        except Exception as e:
            QMessageBox.critical(self, "Chess Error", f"Failed to initialize Stockfish:\\n{e}")
            print(f"[Chess] ERROR: {e}")
            return
        
        # Start from a clean board and clear any state from a previous game
        if self.chess_manager:
            self.chess_manager.reset()
        self._clear_board_mismatch()
        self._clear_move_arrows()
        self._clear_pending_move_arrows()
        self.chess_result_text = None
        self.chess_illegal_move = False
        self._illegal_sound_played_this_turn = False

        # Update game state
        self.currently_playing_chess = True
        self.chess_playBtn.setText("Forfeit")

        print(f"[Chess] Game started! User: {'White' if user_color == chess.WHITE else 'Black'}, Robot: {'White' if robot_color == chess.WHITE else 'Black'}")

        # If robot plays white (goes first), make immediate move
        if robot_color == chess.WHITE:
            print("[Chess] Robot plays White - making first move...")
            # Pause detection during robot's move
            if self.detector_thread:
                self.detector_thread.pause_detection = True
            self._execute_robot_move()  # plays the robot_turn cue
        else:
            # User plays first
            self._update_chess_label()
            self._play_turn_sound(is_player_turn=True)
    
    def _forfeit_chess_game(self):
        """Forfeit current game and reset."""
        print("[Chess] Forfeiting game and resetting...")
        
        # Stop chess engine
        if self.chess_engine:
            self.chess_engine.close()
            self.chess_engine = None
        
        # Reset game state
        self.currently_playing_chess = False
        self.waiting_for_arduino = False
        self.verifying_robot_move = False
        self.chess_playBtn.setText("Play")
        
        # Resume piece detection
        if self.detector_thread:
            self.detector_thread.pause_detection = False
        
        # Reset chess manager and widget
        if self.chess_manager:
            self.chess_manager.reset()
        
        # Forfeiting is a manual reset, not a game result
        self.chess_result_text = None
        self.chess_illegal_move = False
        self._clear_board_mismatch()
        self._clear_move_arrows()
        self._clear_pending_move_arrows()
        self._update_chess_label()

        print("[Chess] Game reset complete")

    def _play_chess_sound(self, filename):
        """Play a sound effect from GUI/Sounds via an OS command (non-blocking)."""
        play_sound(str(self._sounds_dir / filename))

    def _play_turn_sound(self, is_player_turn):
        """Play the turn cue, choosing the in-check variant when the side to move
        is in check."""
        board = self.chess_manager.board if self.chess_manager else None
        in_check = board.is_check() if board is not None else False
        if is_player_turn:
            self._play_chess_sound("your_turn_check.wav" if in_check else "your_turn.wav")
        else:
            self._play_chess_sound("robot_turn_check.wav" if in_check else "robot_turn.wav")

    def _show_board_mismatch(self):
        """Highlight squares where the detected board differs from the last good position."""
        if not self.chess_manager:
            return
        squares = self.chess_manager.get_mismatch_squares()
        if getattr(self, 'chess_board', None):
            self.chess_board.set_highlighted_squares(squares)

    def _clear_board_mismatch(self):
        """Remove the red mismatch overlay from the virtual board."""
        if getattr(self, 'chess_board', None):
            self.chess_board.clear_highlights()

    def _show_move_arrows(self):
        """Draw arrows on the virtual board for the last verified move (both
        the king and rook arrows in the case of castling)."""
        if not self.chess_manager:
            return
        arrows = self.chess_manager.get_last_move_arrows()
        if getattr(self, 'chess_board', None):
            self.chess_board.set_move_arrows(arrows)

    def _clear_move_arrows(self):
        """Remove the move arrows from the virtual board."""
        if getattr(self, 'chess_board', None):
            self.chess_board.clear_move_arrows()

    def _show_pending_move_arrows(self):
        """Draw the tentative arrow(s) for the robot move currently being verified."""
        if self._pending_robot_arrows and getattr(self, 'chess_board', None):
            self.chess_board.set_pending_move_arrows(self._pending_robot_arrows)

    def _clear_pending_move_arrows(self):
        """Remove the tentative (being-verified) move arrows from the board."""
        self._pending_robot_arrows = []
        if getattr(self, 'chess_board', None):
            self.chess_board.clear_pending_move_arrows()

    def _get_piece_positions_for_move(self, move):
        """Localize only the squares this move picks from, on demand.

        Asks the detector to run the position model on just the pick squares
        (mover, captured/en-passant piece, castling rook) using the most recent
        board image, returning {square_name: (x_pct, y_pct)}. Returns None if the
        detector or position model is unavailable (-> fall back to square centres).
        """
        if not self.chess_engine:
            return None
        detector = self.detector_thread.detector if self.detector_thread else None
        if detector is None:
            return None
        pick_squares = self.chess_engine.get_pick_squares(move)
        positions = detector.predict_square_positions(pick_squares)
        return positions or None

    def _update_chess_label(self):
        """Update chessLabel to reflect the current connection/game state."""
        if not hasattr(self, 'chessLabel'):
            return

        # --- Idle (no game in progress) ---
        if not self.currently_playing_chess:
            if self.chess_result_text:
                self.chessLabel.setText(self.chess_result_text)
            elif not (self.serial_connection and self.serial_connection.is_open):
                self.chessLabel.setText("Not connected to Arduino")
            elif not self.detector_running:
                self.chessLabel.setText("Camera not initialized")
            else:
                self.chessLabel.setText("Press Play to start")
            return

        board = self.chess_manager.board if self.chess_manager else None

        # --- Robot is moving ---
        if self.waiting_for_arduino:
            self.chessLabel.setText("Waiting for robot")
            return
        if self.verifying_robot_move:
            self.chessLabel.setText("Waiting for robot - Verifying move")
            return

        # --- User's turn (optionally in check and/or after an illegal move) ---
        parts = ["Your turn"]
        if board is not None and board.is_check():
            parts.append("Check")
        if self.chess_illegal_move:
            parts.append("Illegal move")
        self.chessLabel.setText(" - ".join(parts))

    def _check_chess_game_over(self):
        """If the game is over, end it with the appropriate result. Returns True if ended."""
        board = self.chess_manager.board if self.chess_manager else None
        if board is None or not board.is_game_over():
            return False

        robot_won = None  # None => draw
        if board.is_checkmate():
            # The side to move has been checkmated and lost.
            robot_color = self.chess_engine.robot_color if self.chess_engine else None
            if robot_color is not None and board.turn == robot_color:
                result = "Gameover - You win"
                robot_won = False
            else:
                result = "Gameover - Robot wins"
                robot_won = True
        else:
            # Stalemate, insufficient material, repetition, 50/75-move rule, etc.
            result = "Gameover - Draw"

        self._end_chess_game(result, robot_won)
        return True

    def _end_chess_game(self, result_text, robot_won=None):
        """End the game with a result, display it, and return to idle state.

        Unlike a forfeit, the final board is left on screen and the result text
        stays on the label until a new game is started.

        Args:
            result_text: Label/dialog text, e.g. "Gameover - Robot wins".
            robot_won: True if the robot won, False if it lost, None for a draw.
                       Drives the robot's winning/losing celebration trajectory.
        """
        print(f"[Chess] {result_text}")
        self.chess_result_text = result_text

        if self.chess_engine:
            self.chess_engine.close()
            self.chess_engine = None

        self.currently_playing_chess = False
        self.waiting_for_arduino = False
        self.verifying_robot_move = False
        self.chess_illegal_move = False
        self.chess_playBtn.setText("Play")
        self._clear_board_mismatch()

        # Resume piece detection (game is no longer driving the robot)
        if self.detector_thread:
            self.detector_thread.pause_detection = False

        self._update_chess_label()

        # Game-over sound
        if robot_won is True:
            self._play_chess_sound("gameover_robot_wins.wav")
        elif robot_won is False:
            self._play_chess_sound("gameover_you_win.wav")
        else:
            self._play_chess_sound("gameover_draw.wav")

        # Send the robot a celebration (win) or consolation (loss) gesture.
        if robot_won is True:
            self._send_celebration_trajectory(won=True)
        elif robot_won is False:
            self._send_celebration_trajectory(won=False)

        # Announce the result with a dialog box.
        self._show_game_over_dialog(result_text)

    def _show_game_over_dialog(self, result_text):
        """Show a modal dialog announcing the game result."""
        if "You win" in result_text:
            message = "Checkmate — you win! \U0001F389"
        elif "Robot wins" in result_text:
            message = "Checkmate — the robot wins."
        else:
            message = "The game is a draw."
        QMessageBox.information(self, "Game Over", message)

    def _send_celebration_trajectory(self, won):
        """Send a winning/losing gesture as a Cartesian circular arc, optimized
        with TOPPRA so the motor speed/acceleration limits are respected.

        The gesture sweeps the end-effector back and forth along part of a
        circle centred on the base axis (origin), at a fixed Z and a constant
        radius (so x^2 + y^2 stays constant and only the base angle changes).
        The wrist tilt mu is fixed at +30 deg for a win or -90 deg for a loss.

        Because mu also affects the end-effector position, the circle is centred
        on the *actual* pose reached by taking the default resting arm joints
        (theta, alpha, beta) and applying the celebration mu: forward kinematics
        of that joint set gives the true (x, y, z) to oscillate around.
        """
        if not (self.serial_connection and self.serial_connection.is_open):
            print("[Chess] Cannot send celebration trajectory: no serial connection")
            return

        try:
            home = ChessEngine.HOME_POSITION
            target_mu = np.deg2rad(30.0 if won else -90.0)

            # Default resting arm joints (the pose the robot returns to between moves).
            rest_mu = ChessEngine.mu_func(*home)
            _, alpha_r, beta_r, _ = inverse_kinematics(home[0], home[1], home[2], rest_mu)

            # Keep those arm joints but apply the celebration wrist tilt, then use
            # forward kinematics to find the true centre point of the gesture.
            gamma = mu_to_gamma(target_mu, alpha_r)
            cx, cy, cz = direct_kinematics(0.0, alpha_r, beta_r, gamma)

            radius = float(np.hypot(cx, cy))   # x^2 + y^2 held constant
            phi0 = float(np.arctan2(cy, cx))   # base angle of the centre point

            amplitude = np.deg2rad(30.0)  # how far along the arc to sweep, each side
            cycles = 2                    # back-and-forth waves
            T_duration = 4.0              # arbitrary path-parameter span (TOPPRA re-times)

            def trajectory_func(t):
                # Sweep the polar angle; x, y from trigonometry on the fixed-radius
                # circle, Z held constant.
                phi = phi0 + amplitude * np.sin(2.0 * np.pi * cycles * t / T_duration)
                return [radius * np.cos(phi), radius * np.sin(phi), cz]

            # Plan through TOPPRA with a fixed wrist tilt (mu) for every waypoint.
            planner = self.trajectory_planner
            original_mu_func = planner.mu_func
            try:
                planner.mu_func = lambda x, y, z, _m=target_mu: _m
                planned_waypoints = planner.plan_trajectory(
                    trajectory_func, T_duration, gripper_actions={}
                )
            finally:
                planner.mu_func = original_mu_func

            # Build the Arduino waypoint command (same format as a chess move).
            time_us = round(planner.output_waypoint_dt * 1e6)
            output_parts = [f"wn{planner.output_waypoint_count}d{time_us}"]
            for theta, alpha, beta, mu, gripper in planned_waypoints:
                output_parts.append(
                    f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}"
                )
            command = ",".join(output_parts)

            pose = "winning" if won else "losing"
            print(f"[Chess] Sending {pose} trajectory ({planner.output_waypoint_count} waypoints, "
                  f"mu={np.rad2deg(target_mu):.0f}deg, centre=({cx:.0f},{cy:.0f},{cz:.0f}), "
                  f"T_opt={planner.total_time:.1f}s)...")
            self.serial_connection.write((command + '\n').encode('utf-8'))
        except Exception as e:
            print(f"[Chess] ERROR sending celebration trajectory: {e}")
            import traceback
            traceback.print_exc()

    # Maps the test-move piece letter to a chess piece type
    PIECE_LETTER_TO_TYPE = {
        'p': chess.PAWN,
        'r': chess.ROOK,
        'b': chess.BISHOP,
        'n': chess.KNIGHT,
        'k': chess.KING,
        'q': chess.QUEEN,
    }

    def _parse_test_move(self, text):
        """Parse a test-move string like 'r-a1h2'.

        Returns (piece_type, from_square, to_square) or None if it can't be
        parsed (unknown piece letter, bad format, or off-board squares).
        """
        if not text or '-' not in text:
            return None
        piece_part, _, move_part = text.partition('-')
        piece_part = piece_part.strip()
        move_part = move_part.strip()

        if piece_part not in self.PIECE_LETTER_TO_TYPE:
            return None
        if len(move_part) != 4:
            return None

        from_square, to_square = move_part[:2], move_part[2:]
        for sq in (from_square, to_square):
            if sq[0] not in 'abcdefgh' or sq[1] not in '12345678':
                return None
        if from_square == to_square:
            return None

        return self.PIECE_LETTER_TO_TYPE[piece_part], from_square, to_square

    def _get_offline_chess_engine(self):
        """Return a cached Stockfish-free ChessEngine for coordinate/trajectory use."""
        if self._offline_chess_engine is None:
            self._offline_chess_engine = ChessEngine.create_offline()
        return self._offline_chess_engine

    def _plan_trajectory_command(self, trajectory_data):
        """Run TOPPRA on a trajectory_data dict and return the Arduino command string."""
        self.trajectory_planner.gripper_actions = trajectory_data['gripper_actions']
        planned_waypoints = self.trajectory_planner.plan_trajectory(
            trajectory_data['trajectory_func'],
            trajectory_data['T_duration']
        )
        time_us = round(self.trajectory_planner.output_waypoint_dt * 1e6)
        output_parts = [f"wn{self.trajectory_planner.output_waypoint_count}d{time_us}"]
        for theta, alpha, beta, mu, gripper in planned_waypoints:
            output_parts.append(f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}")
        return ",".join(output_parts)

    def _on_chess_test_move(self):
        """Execute the manual test move described in chess_testLineEdit."""
        # Require a serial connection to drive the robot
        if not self.serial_connection or not self.serial_connection.is_open:
            QMessageBox.warning(self, "Test Move", "Please connect to Arduino first!")
            return

        # Avoid interfering with an in-progress game
        if self.currently_playing_chess:
            QMessageBox.warning(self, "Test Move", "Cannot run a test move during a game. Forfeit first.")
            return

        raw_text = self.chess_testLineEdit.text().strip()
        parsed = self._parse_test_move(raw_text.lower())
        if parsed is None:
            QMessageBox.critical(
                self, "Invalid Move",
                f"Could not parse '{raw_text}'.\n\n"
                "Expected format: <piece>-<from><to>, e.g. 'r-a1h2'.\n"
                "Piece letter must be one of: p (pawn), r (rook), b (bishop), "
                "n (knight), k (king), q (queen)."
            )
            return

        piece_type, from_square, to_square = parsed

        try:
            engine = self.chess_engine or self._get_offline_chess_engine()
            trajectory_data = engine.generate_simple_move_trajectory(piece_type, from_square, to_square)
            command = self._plan_trajectory_command(trajectory_data)

            print(f"[Chess] Test move: {trajectory_data['description']} ({len(command)} bytes)")
            self.serial_connection.write((command + '\n').encode('utf-8'))
        except Exception as e:
            QMessageBox.critical(self, "Test Move Error", f"Failed to execute test move:\n{e}")
            import traceback
            traceback.print_exc()

    def _execute_robot_move(self):
        """Generate and execute robot's chess move."""
        if not self.chess_engine:
            print("[Chess] ERROR: Chess engine not initialized")
            return
        
        try:
            # Update chess engine board with current state
            fen = self.chess_manager.get_fen()
            self.chess_engine.update_board(fen)
            
            # Get best move from Stockfish
            best_move = self.chess_engine.get_best_move(time_limit=0.5)
            
            if best_move is None:
                # Robot has no legal move -> game is over (checkmate or stalemate)
                print("[Chess] Game over!")
                if not self._check_chess_game_over():
                    self._end_chess_game("Gameover - Draw")
                return
            
            print(f"[Chess] Robot move: {best_move.uci()}")

            # Remember the arrow(s) for this move so we can show a tentative
            # arrow while verifying it once the robot reports completion ('D').
            # chess_engine.board is the pre-move position here, so is_castling works.
            self._pending_robot_arrows = ChessManager.move_to_arrows(
                best_move, self.chess_engine.board.is_castling(best_move)
            )

            # Localize just this move's pick squares (on demand) and aim picks at
            # the true piece centres (falls back to square centres if unavailable).
            piece_positions = self._get_piece_positions_for_move(best_move)
            trajectory_data = self.chess_engine.generate_move_trajectory(
                best_move, piece_positions=piece_positions
            )
            
            print(f"[Chess] Move: {trajectory_data['description']}")
            print(f"[Chess] Duration: {trajectory_data['T_duration']}s")
            print(f"[Chess] Gripper actions: {trajectory_data['gripper_actions']}")
            
            # Update planner's gripper actions for this move
            self.trajectory_planner.gripper_actions = trajectory_data['gripper_actions']
            
            # Plan trajectory using the existing planner
            planned_waypoints = self.trajectory_planner.plan_trajectory(
                trajectory_data['trajectory_func'],
                trajectory_data['T_duration']
            )
            
            # Generate Arduino command
            time_us = round(self.trajectory_planner.output_waypoint_dt * 1e6)
            output_parts = [f"wn{self.trajectory_planner.output_waypoint_count}d{time_us}"]
            
            for waypoint in planned_waypoints:
                theta, alpha, beta, mu, gripper = waypoint
                waypoint_str = f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}"
                output_parts.append(waypoint_str)
            
            arduino_command = ",".join(output_parts)
            
            print(f"[Chess] Sending trajectory to Arduino ({len(arduino_command)} bytes)...")
            
            # Send to Arduino
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.write((arduino_command + '\\n').encode('utf-8'))
                
                # Set flag to wait for 'D' response
                self.waiting_for_arduino = True
                print("[Chess] Waiting for Arduino to complete move (waiting for 'D')...")
                self._update_chess_label()
                self._play_turn_sound(is_player_turn=False)
            else:
                print("[Chess] ERROR: Serial connection not available")
                # Resume detection if send failed
                if self.detector_thread:
                    self.detector_thread.pause_detection = False
                self._update_chess_label()

        except Exception as e:
            print(f"[Chess] ERROR executing robot move: {e}")
            import traceback
            traceback.print_exc()

            # Resume detection on error
            if self.detector_thread:
                self.detector_thread.pause_detection = False
            self._update_chess_label()
    
    def changeEvent(self, event):
        """Handle window state changes to prevent visual freezing."""
        if event.type() == event.Type.WindowStateChange:
            # When restored from minimized, force window redraw by resizing
            if not self.isMinimized() and event.oldState() & Qt.WindowState.WindowMinimized:
                QTimer.singleShot(0, self._force_window_redraw)
        super().changeEvent(event)
    
    def _force_window_redraw(self):
        """Force Windows to redraw the frameless window by temporarily resizing."""
        # Store original geometry
        original_geo = self.geometry()
        # Resize by 1 pixel
        self.resize(original_geo.width() + 1, original_geo.height())
        # Process events to ensure resize happens
        QApplication.processEvents()
        # Restore original size
        self.resize(original_geo.width(), original_geo.height())
        # Move to original position if it changed
        self.move(original_geo.topLeft())
        # Force repaint
        self._force_repaint()
    
    def showEvent(self, event):
        """Handle show event to prevent visual freezing."""
        super().showEvent(event)
        # Force complete repaint when window becomes visible
        QTimer.singleShot(10, self._force_repaint)
        QTimer.singleShot(50, self._force_repaint)
    
    def _force_repaint(self):
        """Force a complete repaint of the window."""
        self.update()
        self.repaint()
        # Also update all child widgets (safely handle overloaded update methods)
        for widget in self.findChildren(QWidget):
            try:
                widget.update()
            except TypeError:
                # Some widgets have overloaded update() methods that require arguments
                widget.repaint()
    
    def closeEvent(self, event):
        """Handle application close event - cleanup resources."""
        # Stop chess game if playing
        if self.currently_playing_chess:
            self._forfeit_chess_game()
        
        # Stop chess detector if running
        if self.detector_running:
            self._stop_chess_detector()
        
        # Accept the close event
        event.accept()