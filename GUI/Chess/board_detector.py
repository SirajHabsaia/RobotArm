"""
Chess Board Detector using ArUco markers and CNN-based piece classification.

This module provides chess board detection with:
- ArUco marker-based board detection and perspective correction
- Hand detection using Canny edge detection on the stripe between markers
- PyTorch CNN for piece classification (empty/white/black)
- Support for video, camera, and IP camera input streams

Usage:
    from board_detector import BoardDetector
    from config import BoardAnalyzerConfig
    
    config = BoardAnalyzerConfig()
    detector = BoardDetector(config)
    
    for result in detector.process_stream():
        if result is not None:
            board_state = result['board_state']
            display_big = result['display_big_cropped']
            display_small = result['display_small_cropped']
"""

import cv2
import numpy as np
import onnxruntime as ort
from typing import Optional, Dict, Any, Tuple, List
import time
import os
from functools import wraps
from collections import defaultdict


def _softmax(x: np.ndarray, axis: int = 1) -> np.ndarray:
    """Numerically stable softmax over the given axis."""
    x = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(x)
    return e / np.sum(e, axis=axis, keepdims=True)

try:
    # When imported as part of GUI package
    from .config import get_aruco_detector, BoardAnalyzerConfig
except ImportError:
    # When run as standalone script from Chess folder
    from config import get_aruco_detector, BoardAnalyzerConfig


# ======================== BOARD DETECTOR ========================
#
# Inference uses ONNX Runtime (onnxruntime) on the exported models:
#   GUI/Chess/model.onnx           - square classifier (black/empty/white logits)
#   GUI/Chess/model_position.onnx  - piece-centre regressor (x, y in [0,1])
# Both take input (N, 3, 32, 32) float32 in [0,1], RGB. Regenerate them from the
# trained .pth weights with: python AI/export_onnx.py

def performance_metric(func):
    """
    Decorator to measure function execution time for performance profiling.
    Only active if the instance has performance_metrics enabled.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not getattr(self, 'performance_metrics', False):
            # Performance tracking disabled, just call the function
            return func(self, *args, **kwargs)
        
        # Measure execution time
        start_time = time.perf_counter()
        result = func(self, *args, **kwargs)
        elapsed_time = time.perf_counter() - start_time
        
        # Record timing
        func_name = func.__name__
        self._perf_times[func_name].append(elapsed_time)
        self._perf_call_counts[func_name] += 1
        
        return result
    return wrapper


class BoardDetector:
    """
    Main class for detecting chess pieces on a board using ArUco markers and CNN.
    
    Workflow:
    1. Detect ArUco markers to get board perspective
    2. Extract big_cropped (outer rectangle) and small_cropped (inner board)
    3. Analyze stripe (area between big and small) for hand detection using Canny
    4. If no hand detected, extract 64 squares and classify with CNN
    5. Return board state and display images
    """

    # Dev-overlay text colour per class label (BGR)
    DEV_CLASS_COLORS = {
        "white": (0, 255, 0),     # green
        "black": (0, 0, 255),     # red
        "empty": (0, 255, 255),   # yellow
    }

    def __init__(self, config: Optional[BoardAnalyzerConfig] = None, side: str = "white", performance_metrics: bool = False, dev_mode: bool = False):
        """
        Initialize the BoardDetector.

        Args:
            config: BoardAnalyzerConfig instance, or None to use defaults
            side: Which side the user is playing from ('white' or 'black').
                  If 'white', robot arm is on black's side (top).
                  If 'black', robot arm is on white's side (bottom).
            performance_metrics: If True, track and report performance metrics
            dev_mode: If True, overlay per-square inference confidence on the
                      hand-contour (big cropped) stream.
        """
        if config is None:
            config = BoardAnalyzerConfig()

        self.config = config
        self.side = side.lower()  # Normalize to lowercase
        self.performance_metrics = performance_metrics
        self.dev_mode = dev_mode

        # Dev overlay state: latest analysed confidences/positions and the board's
        # interior corners mapped into the full_cropped frame (for placing overlays).
        self._last_board_state = None
        self._last_position_state = None
        self._last_board_tensor = None  # cached (3,256,256) board for on-demand localization
        self._board_corners_in_full = None

        # When True (mirrored from the thread's pause_detection), classification is
        # frozen (the robot is executing its move). The last analysed board/positions
        # are kept so the dev overlay can keep showing the piece-centre dots.
        self.classification_paused = False
        
        # Initialize performance tracking
        if self.performance_metrics:
            self._perf_times = defaultdict(list)  # func_name -> list of execution times
            self._perf_call_counts = defaultdict(int)  # func_name -> call count
        
        if self.side not in ["white", "black"]:
            raise ValueError(f"side must be 'white' or 'black', got '{side}'")
        
        # Initialize ArUco detector
        self.detector = get_aruco_detector()
        
        # Corner points storage (buffer for failed detections)
        self.pts_interior: Optional[np.ndarray] = None
        self.pts_exterior: Optional[np.ndarray] = None
        
        # Initialize CNN model
        self._init_model()
        
        # Initialize video capture
        self._init_capture()
        
        # Timing for video mode
        self.last_frame_time = time.time()
        
        # Hand detection cooldown tracking
        self.cooldown_counter = 0  # Counts down from cooldown_frames to 0
        self.hand_was_detected = False  # Track if hand was detected in previous frame
        
    @staticmethod
    def _onnx_path_for(model_path: str) -> str:
        """Resolve the .onnx path next to this module for a configured model name.

        Accepts a .pth or .onnx name; always returns an absolute .onnx path.
        """
        if model_path.endswith(".pth"):
            model_path = model_path[:-4] + ".onnx"
        elif not model_path.endswith(".onnx"):
            model_path = model_path + ".onnx"
        if not os.path.isabs(model_path):
            model_path = os.path.join(os.path.dirname(__file__), model_path)
        return model_path

    @performance_metric
    def _init_model(self):
        """Load the ONNX inference sessions for classification and localization."""
        providers = ["CPUExecutionProvider"]

        # Square classifier (required)
        model_path = self._onnx_path_for(self.config.model_path)
        if os.path.exists(model_path):
            self.session = ort.InferenceSession(model_path, providers=providers)
            self.input_name = self.session.get_inputs()[0].name
            print(f"[BoardDetector] Classifier model loaded: {model_path}")
        else:
            self.session = None
            self.input_name = None
            print(f"Warning: Model file '{model_path}' not found. Classification disabled.")

        # Position regressor (optional): if missing, the robot falls back to aiming
        # at the geometric square centre.
        position_model_path = self._onnx_path_for(
            getattr(self.config, "position_model_path", "model_position.pth"))

        self.position_session = None
        self.position_input_name = None
        if os.path.exists(position_model_path):
            try:
                self.position_session = ort.InferenceSession(position_model_path, providers=providers)
                self.position_input_name = self.position_session.get_inputs()[0].name
                print(f"[BoardDetector] Position model loaded: {position_model_path}")
            except Exception as e:
                self.position_session = None
                print(f"[BoardDetector] Warning: failed to load position model ({e}); using square centres.")
        else:
            print(f"[BoardDetector] Position model '{position_model_path}' not found; using square centres.")

    @performance_metric
    def _init_capture(self):
        """Initialize video capture based on mode."""
        mode = self.config.mode
        
        if mode == "video":
            video_path = os.path.expanduser(os.path.expandvars(self.config.video_path))
            if not os.path.isabs(video_path):
                video_path = os.path.join(os.path.dirname(__file__), video_path)
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                raise FileNotFoundError(f"Could not open video: {video_path}")
        elif mode == "camera":
            self.cap = cv2.VideoCapture(self.config.camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open camera at index {self.config.camera_index}")
        elif mode == "ip_camera":
            if not self.config.camera_ip:
                raise ValueError("camera_ip must be specified for ip_camera mode")
            self.cap = cv2.VideoCapture(self.config.camera_ip)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not connect to IP camera: {self.config.camera_ip}")
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'video', 'camera', or 'ip_camera'")
    
    @performance_metric
    def _detect_aruco_markers(self, frame: np.ndarray) -> bool:
        """
        Detect ArUco markers and update corner points.
        
        Marker layout (same as CV folder):
        - Marker 0: Top-left (corner[2] is interior, corner[0] is exterior)
        - Marker 1: Top-right (corner[3] is interior, corner[1] is exterior)
        - Marker 2: Bottom-right (corner[0] is interior, corner[2] is exterior)
        - Marker 3: Bottom-left (corner[1] is interior, corner[3] is exterior)
        
        Returns:
            True if all 4 markers detected successfully
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        
        if ids is None or len(ids) < 4:
            return False
        
        ids = ids.flatten()
        sorted_idx = np.argsort(ids)
        sorted_ids = ids[sorted_idx]
        sorted_corners = [corners[i] for i in sorted_idx]
        
        if not np.array_equal(sorted_ids, [0, 1, 2, 3]):
            return False
        
        # Extract interior corners (chess board corners)
        new_pts_interior = np.array([
            sorted_corners[0][0][2],  # Marker 0, corner 2 (top-left)
            sorted_corners[1][0][3],  # Marker 1, corner 3 (top-right)
            sorted_corners[2][0][0],  # Marker 2, corner 0 (bottom-right)
            sorted_corners[3][0][1]   # Marker 3, corner 1 (bottom-left)
        ], dtype=np.float32)
        
        # Extract exterior corners (including markers)
        new_pts_exterior = np.array([
            sorted_corners[0][0][0],  # Marker 0, corner 0 (top-left outer)
            sorted_corners[1][0][1],  # Marker 1, corner 1 (top-right outer)
            sorted_corners[2][0][2],  # Marker 2, corner 2 (bottom-right outer)
            sorted_corners[3][0][3]   # Marker 3, corner 3 (bottom-left outer)
        ], dtype=np.float32)
        
        # Update corners if this is first detection or if movement is significant
        if self.pts_interior is None:
            self.pts_interior = new_pts_interior
            self.pts_exterior = new_pts_exterior
        else:
            point_diffs = np.linalg.norm(new_pts_interior - self.pts_interior, axis=1)
            max_movement = np.max(point_diffs)
            
            if max_movement > self.config.aruco_pts_movement_threshold:
                self.pts_interior = new_pts_interior
                self.pts_exterior = new_pts_exterior
        
        return True
    
    @performance_metric
    def _get_cropped_images(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Get perspective-corrected cropped images at original resolution.
        
        Returns:
            Tuple of (small_cropped, big_cropped, full_cropped) where:
            - small_cropped: The chess board interior (original resolution)
            - big_cropped: The board including ArUco markers (original resolution)
            - full_cropped: Extended region beyond big_cropped for hand detection (original resolution)
        """
        # Calculate the size based on the actual marker distances
        # Use the interior points to determine board size
        width_top = np.linalg.norm(self.pts_interior[1] - self.pts_interior[0])
        width_bottom = np.linalg.norm(self.pts_interior[2] - self.pts_interior[3])
        height_left = np.linalg.norm(self.pts_interior[3] - self.pts_interior[0])
        height_right = np.linalg.norm(self.pts_interior[2] - self.pts_interior[1])
        
        # Use average dimensions
        avg_width_interior = int((width_top + width_bottom) / 2)
        avg_height_interior = int((height_left + height_right) / 2)
        size_small = max(avg_width_interior, avg_height_interior)  # Use square for board
        
        # Calculate exterior size similarly
        width_top_ext = np.linalg.norm(self.pts_exterior[1] - self.pts_exterior[0])
        width_bottom_ext = np.linalg.norm(self.pts_exterior[2] - self.pts_exterior[3])
        height_left_ext = np.linalg.norm(self.pts_exterior[3] - self.pts_exterior[0])
        height_right_ext = np.linalg.norm(self.pts_exterior[2] - self.pts_exterior[1])
        
        avg_width_exterior = int((width_top_ext + width_bottom_ext) / 2)
        avg_height_exterior = int((height_left_ext + height_right_ext) / 2)
        size_big = max(avg_width_exterior, avg_height_exterior)
        
        # Define destination points for perspective transform
        dst_small = np.array([
            [0, 0],
            [size_small - 1, 0],
            [size_small - 1, size_small - 1],
            [0, size_small - 1]
        ], dtype=np.float32)
        
        dst_big = np.array([
            [0, 0],
            [size_big - 1, 0],
            [size_big - 1, size_big - 1],
            [0, size_big - 1]
        ], dtype=np.float32)
        
        # Get perspective transforms
        M_small = cv2.getPerspectiveTransform(self.pts_interior, dst_small)
        M_big = cv2.getPerspectiveTransform(self.pts_exterior, dst_big)
        
        # Warp images at original resolution
        small_cropped = cv2.warpPerspective(frame, M_small, (size_small, size_small))
        big_cropped = cv2.warpPerspective(frame, M_big, (size_big, size_big))
        
        # Calculate full region (extended beyond big_cropped for hand detection)
        margin = self.config.hand_detection_outer_margin
        size_full = int(size_big * (1.0 + margin))
        
        # Calculate full region corners by extending pts_exterior outward
        # Find center of the board
        center = np.mean(self.pts_exterior, axis=0)
        
        # Extend each exterior point away from center
        pts_full = []
        for pt in self.pts_exterior:
            direction = pt - center
            extended_pt = center + direction * (1.0 + margin)
            pts_full.append(extended_pt)
        pts_full = np.array(pts_full, dtype=np.float32)
        
        dst_full = np.array([
            [0, 0],
            [size_full - 1, 0],
            [size_full - 1, size_full - 1],
            [0, size_full - 1]
        ], dtype=np.float32)
        
        M_full = cv2.getPerspectiveTransform(pts_full, dst_full)
        full_cropped = cv2.warpPerspective(frame, M_full, (size_full, size_full))

        # For the dev overlay: map the interior board corners into the
        # full_cropped frame so per-square confidence can be placed correctly.
        if self.dev_mode:
            self._board_corners_in_full = cv2.perspectiveTransform(
                self.pts_interior.reshape(-1, 1, 2), M_full
            ).reshape(-1, 2)

        return small_cropped, big_cropped, full_cropped
    
    @performance_metric
    def _detect_hand_in_stripe(self, big_cropped: np.ndarray, full_cropped: np.ndarray) -> Tuple[bool, np.ndarray, float]:
        """
        Detect if a hand is present in the stripe between full_cropped and big_cropped.
        
        Uses Canny edge detection on the stripe area and counts contours.
        Only analyzes the outer portion of the stripe (defined by hand_detection_stripe_usage).
        Excludes the opponent's stripe segment where the robot arm will be.
        
        Returns:
            Tuple of (hand_detected, contour_image, contour_density) where:
            - hand_detected: True if contour density exceeds threshold
            - contour_image: full_cropped with contours drawn for visualization
            - contour_density: Total contour length (float)
        """
        # Get actual sizes
        big_size = big_cropped.shape[0]  # Should be square
        full_size = full_cropped.shape[0]  # Should be square
        
        # Convert full_cropped to grayscale for edge detection
        gray = cv2.cvtColor(full_cropped, cv2.COLOR_BGR2GRAY)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, self.config.hand_canny_low, self.config.hand_canny_high)
        
        # Calculate stripe dimensions
        total_stripe_width = (full_size - big_size) // 2  # Width of stripe on each side
        
        # Calculate how much of the stripe to actually use (from outer edge inward)
        stripe_usage = self.config.hand_detection_stripe_usage
        used_stripe_width = int(total_stripe_width * stripe_usage)
        
        # Calculate the size of the excluded inner region
        # We exclude big_cropped PLUS the unused inner portion of the stripe
        excluded_size = big_size + 2 * (total_stripe_width - used_stripe_width)
        excluded_offset = (full_size - excluded_size) // 2
        
        # Create mask for stripe region (exclude the inner region close to the board)
        mask = np.ones(edges.shape, dtype=np.uint8) * 255
        mask[excluded_offset:excluded_offset+excluded_size, excluded_offset:excluded_offset+excluded_size] = 0
        
        # Exclude opponent's stripe segment (where robot arm will be)
        # If user plays white, exclude top stripe (black's side / row 0)
        # If user plays black, exclude bottom stripe (white's side / row 7)
        if self.side == "white":
            # Exclude top stripe
            mask[0:excluded_offset, :] = 0
        else:  # side == "black"
            # Exclude bottom stripe
            mask[full_size - excluded_offset:full_size, :] = 0
        
        # Apply mask to edges
        stripe_edges = cv2.bitwise_and(edges, edges, mask=mask)
        
        # Find contours
        contours, _ = cv2.findContours(stripe_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Calculate contour density (total contour length)
        total_contour_length = sum(cv2.arcLength(cnt, True) for cnt in contours)
        
        # Create visualization image (use full_cropped)
        contour_image = full_cropped.copy()
        
        # Draw the region where edge detection is being applied
        # Create a semi-transparent overlay showing the active detection region
        overlay = contour_image.copy()
        # Draw the active region in blue
        overlay[mask > 0] = [255, 100, 0]  # BGR: Orange/blue color for active region
        # Blend with original image (30% overlay, 70% original)
        cv2.addWeighted(overlay, 0.3, contour_image, 0.7, 0, contour_image)
        
        # Draw contours on top
        cv2.drawContours(contour_image, contours, -1, (0, 255, 0), 2)
        
        # Check if hand is detected
        hand_detected = total_contour_length > self.config.hand_contour_threshold
        
        return hand_detected, contour_image, total_contour_length
    
    @performance_metric
    def _extract_squares(self, small_cropped: np.ndarray) -> List[Tuple[int, int, np.ndarray]]:
        """
        Extract 64 squares from the chess board.
        
        Args:
            small_cropped: Chess board image (any resolution, square)
        
        Returns:
            List of (row, col, square_image) tuples where:
            - row: 0-7 (0 is rank 8, 7 is rank 1)
            - col: 0-7 (0 is file a, 7 is file h)
            - square_image: Cropped square image (at original resolution, scaled by square_scale)
        """
        board_size = small_cropped.shape[0]  # Get actual board size
        square_size = board_size / 8.0  # Use float for precise calculation
        scale = self.config.square_scale
        
        squares = []
        
        for row in range(8):
            for col in range(8):
                # Calculate square boundaries (full square)
                x1 = col * square_size
                y1 = row * square_size
                x2 = x1 + square_size
                y2 = y1 + square_size
                
                # Apply scaling to extract center portion of square
                # square_scale defines what percentage of the square to use
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                scaled_size = square_size * scale
                
                x1_scaled = int(center_x - scaled_size / 2)
                y1_scaled = int(center_y - scaled_size / 2)
                x2_scaled = int(center_x + scaled_size / 2)
                y2_scaled = int(center_y + scaled_size / 2)
                
                # Ensure boundaries are within image
                x1_scaled = max(0, x1_scaled)
                y1_scaled = max(0, y1_scaled)
                x2_scaled = min(board_size, x2_scaled)
                y2_scaled = min(board_size, y2_scaled)
                
                # Extract square at original resolution
                square = small_cropped[y1_scaled:y2_scaled, x1_scaled:x2_scaled]
                
                squares.append((row, col, square))
        
        return squares
    
    @performance_metric
    def _classify_square(self, square_image: np.ndarray) -> Tuple[str, float]:
        """
        Classify a square using the CNN model.
        
        Args:
            square_image: Square image (BGR format, any resolution)
        
        Returns:
            Tuple of (class_label, confidence) where:
            - class_label: One of the class names (e.g., "empty", "white", "black")
            - confidence: Confidence score (0-1)
        """
        # Resize to model input size (32x32), BGR->RGB, CHW, [0,1], batch of 1
        square_resized = cv2.resize(square_image, (32, 32))
        rgb_image = cv2.cvtColor(square_resized, cv2.COLOR_BGR2RGB)
        inp = rgb_image.transpose(2, 0, 1).astype(np.float32)[None] / 255.0  # (1,3,32,32)

        # Run inference
        logits = self.session.run(None, {self.input_name: inp})[0]
        probs = _softmax(logits, axis=1)[0]
        predicted_idx = int(np.argmax(probs))
        confidence = float(probs[predicted_idx])
        predicted_class = self.config.class_names[predicted_idx]

        return predicted_class, confidence
    
    @performance_metric
    def _analyze_board(self, small_cropped: np.ndarray) -> Dict[str, Any]:
        """
        Analyze all 64 squares and return board state.
        
        Maximum performance batch inference:
        - Single resize to 256x256 (32px per square for new lightweight CNN)
        - BGR→RGB conversion on full board
        - Direct numpy→tensor conversion
        - Tensor slicing to extract 64 squares
        - Single batch forward pass
        
        Args:
            small_cropped: Chess board image (any resolution, square)
        
        Returns:
            Dictionary containing:
            - board_state: 8x8 list of (class, confidence) tuples
            - display_image: small_cropped with predictions overlaid

        Note: piece-centre localization is NOT run here. It is computed on
        demand for only the squares a move needs, right before the trajectory
        (see ``predict_square_positions``). The board tensor is cached so that
        on-demand inference can reuse it without re-warping.
        """
        # Initialize board state (8x8 grid)
        board_state = [[None for _ in range(8)] for _ in range(8)]

        # Create display image
        display_image = small_cropped.copy()
        
        # Get board size for text placement
        board_size = small_cropped.shape[0]
        square_size_display = board_size / 8.0
        
        # MAXIMUM PERFORMANCE BATCH INFERENCE
        # Step 1: Single resize to 256x256 (32px per square * 8)
        board_resized = cv2.resize(small_cropped, (256, 256))
        
        # Step 2: BGR→RGB conversion (numpy, very fast)
        board_rgb = cv2.cvtColor(board_resized, cv2.COLOR_BGR2RGB)
        
        # Step 3: HWC -> CHW, normalize to [0,1] (numpy, float32)
        board_chw = board_rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
        # Shape: (3, 256, 256)

        # Step 4: Extract 64 squares via array slicing
        batch_squares = []
        for row in range(8):
            for col in range(8):
                y1 = row * 32
                x1 = col * 32
                batch_squares.append(board_chw[:, y1:y1 + 32, x1:x1 + 32])

        # Step 5: Stack into batch (64, 3, 32, 32)
        batch_input = np.stack(batch_squares).astype(np.float32)

        # Cache the board array so piece-centre localization can be run on demand
        # later (for just the squares a move touches) without re-warping the board.
        self._last_board_tensor = board_chw

        # Step 6: Run batch inference ONCE (classification only)
        batch_logits = self.session.run(None, {self.input_name: batch_input})[0]
        batch_probabilities = _softmax(batch_logits, axis=1)
        predicted_indices = np.argmax(batch_probabilities, axis=1)
        confidences = batch_probabilities[np.arange(len(predicted_indices)), predicted_indices]

        # Step 7: Extract results and draw visualizations
        idx = 0
        for row in range(8):
            for col in range(8):
                confidence = float(confidences[idx])
                class_label = self.config.class_names[int(predicted_indices[idx])]

                board_state[row][col] = (class_label, confidence)

                idx += 1

                # Draw prediction on display image (original resolution)
                center_x = int(col * square_size_display + square_size_display / 2)
                center_y = int(row * square_size_display + square_size_display / 2)
                
                # Format text: first letter + confidence
                letter = class_label[0].upper()  # 'E', 'W', or 'B'
                conf_str = f"{confidence:.{self.config.display_confidence_decimals}f}"
                text = f"{letter}:{conf_str}"
                
                # Draw text (scale based on display square size, not model input size)
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = self.config.display_font_scale * (square_size_display / 100.0)
                thickness = max(1, int(self.config.display_font_thickness * (square_size_display / 100.0)))
                color = self.config.display_text_color
                
                # Get text size for centering
                (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
                text_x = center_x - text_width // 2
                text_y = center_y + text_height // 2
                
                cv2.putText(display_image, text, (text_x, text_y), font,
                           font_scale, color, thickness, cv2.LINE_AA)

        # In dev mode only, localize every occupied piece so the overlay can show
        # the predicted centres. Normal operation skips this and localizes on
        # demand (just the squares a move needs) right before the trajectory.
        if self.dev_mode:
            occupied = [(r, c) for r in range(8) for c in range(8)
                        if board_state[r][c][0] != "empty"]
            preds = self._run_position_model(occupied, board_chw)
            pos_grid = [[None for _ in range(8)] for _ in range(8)]
            for (r, c), xy in preds.items():
                pos_grid[r][c] = xy
            self._last_position_state = pos_grid

        return {
            'board_state': board_state,
            'display_image': display_image
        }

    def _run_position_model(self, square_indices, board_tensor=None):
        """Run the position model on the given ``(row, col)`` squares.

        Args:
            square_indices: iterable of (row, col) with row 0 = rank 8, col 0 = file a.
            board_tensor: (3, 256, 256) board tensor to crop from; defaults to the
                last analysed board (``self._last_board_tensor``).

        Returns:
            ``{(row, col): (x_pct, y_pct)}`` (bottom-left origin, percent).
            Empty dict if the model or board tensor is unavailable.
        """
        if self.position_session is None:
            return {}
        if board_tensor is None:
            board_tensor = self._last_board_tensor
        if board_tensor is None:
            return {}

        crops, valid = [], []
        for (row, col) in square_indices:
            if 0 <= row < 8 and 0 <= col < 8:
                y1, x1 = row * 32, col * 32
                crops.append(board_tensor[:, y1:y1 + 32, x1:x1 + 32])
                valid.append((row, col))
        if not crops:
            return {}

        batch = np.stack(crops).astype(np.float32)
        out = self.position_session.run(None, {self.position_input_name: batch})[0] * 100.0
        return {rc: (float(out[i, 0]), float(out[i, 1])) for i, rc in enumerate(valid)}

    def predict_square_positions(self, square_names):
        """Predict piece centres for the given square names (e.g. ``['e2', 'h1']``).

        Localizes only the requested squares using the most recently analysed
        board image. Intended to be called right before generating a trajectory.

        Returns:
            ``{square_name: (x_pct, y_pct)}`` for squares where a prediction is
            available (bottom-left origin, percent). Empty if no position model
            or no analysed board yet.
        """
        if not square_names:
            return {}
        indices, index_to_name = [], {}
        for name in square_names:
            col = ord(name[0]) - ord('a')      # file a..h -> 0..7
            row = 7 - (int(name[1]) - 1)        # rank 1..8 -> row 7..0
            indices.append((row, col))
            index_to_name[(row, col)] = name
        preds = self._run_position_model(indices)
        return {index_to_name[rc]: xy for rc, xy in preds.items()}

    def _draw_dev_confidence_overlay(self, image: np.ndarray):
        """
        Dev mode: overlay the latest per-square inference confidence on top of
        the board region of the hand-contour (full_cropped) image.

        Uses the board's interior corners mapped into the full_cropped frame
        (``self._board_corners_in_full``) and bilinearly interpolates each
        square's centre, so it stays aligned even if the warped board isn't a
        perfect axis-aligned square. Confidences come from the most recent board
        analysis (``self._last_board_state``); during hand/cooldown frames the
        last analysed values are shown.
        """
        board_state = self._last_board_state
        position_state = self._last_position_state
        corners = self._board_corners_in_full
        if board_state is None or corners is None:
            return

        tl, tr, br, bl = corners  # each np.array([x, y]) in full_cropped pixels

        def board_point(u, v):
            """Bilinearly interpolate a board point; u=left->right, v=top->bottom (0..1)."""
            top = tl + u * (tr - tl)
            bottom = bl + u * (br - bl)
            return top + v * (bottom - top)

        # Font scaling based on the on-screen square size
        square_px = float(np.linalg.norm(tr - tl)) / 8.0
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.45, self.config.display_font_scale * (square_px / 65.0))
        thickness = max(1, int(square_px / 32))
        dot_radius = max(2, int(square_px / 10))

        # While classification is paused (robot executing its move), hide the
        # confidence labels so the frozen piece-centre dots stay clearly visible.
        show_labels = not self.classification_paused

        for row in range(8):
            for col in range(8):
                cell = board_state[row][col]
                if cell is None:
                    continue
                class_label, confidence = cell

                center = board_point((col + 0.5) / 8.0, (row + 0.5) / 8.0)
                cx, cy = int(center[0]), int(center[1])

                # Per-class colour (BGR); fall back to yellow for unknown labels
                color = self.DEV_CLASS_COLORS.get(class_label, (0, 255, 255))

                # Marker at the predicted piece centre (where the arm will aim).
                if position_state is not None and position_state[row][col] is not None:
                    x_pct, y_pct = position_state[row][col]
                    # x_pct: left->right within the square; y_pct: bottom->top, so
                    # the vertical fraction from the top of the square is 1 - y_pct.
                    pu = (col + x_pct / 100.0) / 8.0
                    pv = (row + (1.0 - y_pct / 100.0)) / 8.0
                    ppt = board_point(pu, pv)
                    px, py = int(ppt[0]), int(ppt[1])
                    cv2.circle(image, (px, py), dot_radius, color, -1)
                    cv2.circle(image, (px, py), dot_radius, (255, 255, 255), 1, cv2.LINE_AA)

                if not show_labels:
                    continue

                letter = class_label[0].upper()  # 'E', 'W', or 'B'
                conf_str = f"{confidence:.{self.config.display_confidence_decimals}f}"
                text = f"{letter}:{conf_str}"

                (tw, th), _ = cv2.getTextSize(text, font, font_scale, thickness)
                tx = cx - tw // 2
                ty = cy + th // 2

                # Dark background box for readability over the live image
                cv2.rectangle(image, (tx - 5, ty - th - 6), (tx + tw + 5, ty + 6), (0, 0, 0), -1)
                cv2.putText(image, text, (tx, ty), font, font_scale, color, thickness, cv2.LINE_AA)

    def process_frame(self, frame: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Process a single frame.
        
        Args:
            frame: Input frame (BGR). If None, captures from video source.
        
        Returns:
            Dictionary containing:
            - board_state: 8x8 grid of (class, confidence) tuples, or None if skipped
            - display_big_cropped: Big cropped image with contours
            - display_small_cropped: Small cropped with predictions, or None if skipped
            - hand_detected: Boolean indicating if hand was detected
            - skipped: Boolean indicating if frame was skipped due to hand
            
            Returns None if frame cannot be processed (e.g., no valid ArUco detection yet)
        """
        # Capture frame if not provided
        if frame is None:
            ret, frame = self.cap.read()
            if not ret:
                return None
        
        # Try to detect ArUco markers
        detection_success = self._detect_aruco_markers(frame)
        
        # If detection failed and we don't have buffered corners, skip frame
        if not detection_success and self.pts_interior is None:
            return None
        
        # Get cropped images using buffered corners
        small_cropped, big_cropped, full_cropped = self._get_cropped_images(frame)
        
        # Detect hand in stripe
        hand_detected, contour_image, contour_density = self._detect_hand_in_stripe(big_cropped, full_cropped)

        # Classification paused (robot is executing its move): keep the video
        # stream live but don't re-classify, so the last good board / piece
        # positions stay frozen. In dev mode the overlay then shows just the
        # piece-centre dots (labels are hidden while paused).
        if self.classification_paused:
            if self.dev_mode:
                self._draw_dev_confidence_overlay(contour_image)
            return {
                'board_state': None,
                'display_big_cropped': contour_image,
                'display_small_cropped': None,
                'hand_detected': hand_detected,
                'skipped': True,
                'contour_density': contour_density
            }

        # Handle cooldown logic
        if hand_detected:
            # Hand is detected: reset cooldown counter
            self.cooldown_counter = self.config.hand_detection_cooldown_frames
            self.hand_was_detected = True

            if self.dev_mode:
                self._draw_dev_confidence_overlay(contour_image)

            return {
                'board_state': None,
                'display_big_cropped': contour_image,
                'display_small_cropped': None,
                'hand_detected': True,
                'skipped': True,
                'contour_density': contour_density
            }
        else:
            # No hand detected
            if self.cooldown_counter > 0:
                # Still in cooldown period: skip board analysis
                self.cooldown_counter -= 1

                if self.dev_mode:
                    self._draw_dev_confidence_overlay(contour_image)

                return {
                    'board_state': None,
                    'display_big_cropped': contour_image,
                    'display_small_cropped': None,
                    'hand_detected': False,
                    'skipped': True,
                    'contour_density': contour_density,
                    'cooldown_remaining': self.cooldown_counter
                }

        # No hand and no cooldown: analyze board
        analysis_result = self._analyze_board(small_cropped)

        # Cache the latest board state and refresh the dev overlay. In dev mode,
        # _analyze_board has already populated self._last_position_state.
        self._last_board_state = analysis_result['board_state']
        if self.dev_mode:
            self._draw_dev_confidence_overlay(contour_image)

        return {
            'board_state': analysis_result['board_state'],
            'display_big_cropped': contour_image,
            'display_small_cropped': analysis_result['display_image'],
            'hand_detected': False,
            'skipped': False,
            'contour_density': contour_density
        }
    
    def process_stream(self):
        """
        Generator that yields processed frames from the video stream.
        
        Handles timing for different modes:
        - video: Processes at controlled FPS (video_input_speed)
        - camera/ip_camera: Processes latest frame, skips if falling behind
        
        Yields:
            Result dictionary from process_frame()
        """
        mode = self.config.mode
        
        # For video mode, calculate frame interval
        if mode == "video":
            frame_interval = 1.0 / self.config.video_input_speed
        
        while True:
            # For camera modes, always grab latest frame
            if mode in ["camera", "ip_camera"]:
                # Grab all pending frames to get the latest
                for _ in range(10):  # Limit to avoid infinite loop
                    ret = self.cap.grab()
                    if not ret:
                        return
                
                # Retrieve the latest frame
                ret, frame = self.cap.retrieve()
                if not ret:
                    return
                
                result = self.process_frame(frame)
                if result is not None:
                    yield result
            
            # For video mode, control playback speed
            elif mode == "video":
                current_time = time.time()
                elapsed = current_time - self.last_frame_time
                
                # If we're ahead of schedule, wait
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                
                ret, frame = self.cap.read()
                if not ret:
                    # Loop video or exit
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                self.last_frame_time = time.time()
                
                result = self.process_frame(frame)
                if result is not None:
                    yield result
    
    def _print_performance_metrics(self):
        """Print performance metrics summary."""
        if not self.performance_metrics or not self._perf_times:
            return
        
        print("\n" + "="*70)
        print("BOARD DETECTOR PERFORMANCE METRICS")
        print("="*70)
        
        # Calculate and display metrics for each function
        total_rows = []
        for func_name in sorted(self._perf_times.keys()):
            times = self._perf_times[func_name]
            call_count = self._perf_call_counts[func_name]
            
            if times:
                min_time = min(times) * 1000  # Convert to ms
                max_time = max(times) * 1000
                avg_time = (sum(times) / len(times)) * 1000
                total_time = sum(times) * 1000
                
                total_rows.append({
                    'name': func_name,
                    'calls': call_count,
                    'min': min_time,
                    'avg': avg_time,
                    'max': max_time,
                    'total': total_time
                })
        
        # Print header
        print(f"{'Function':<30} {'Calls':>8} {'Min(ms)':>10} {'Avg(ms)':>10} {'Max(ms)':>10} {'Total(ms)':>12}")
        print("-"*70)
        
        # Print each function's metrics
        for row in total_rows:
            print(f"{row['name']:<30} {row['calls']:>8} {row['min']:>10.3f} {row['avg']:>10.3f} {row['max']:>10.3f} {row['total']:>12.2f}")
        
        # Calculate total
        grand_total = sum(row['total'] for row in total_rows)
        print("-"*70)
        print(f"{'TOTAL':<30} {'':<8} {'':<10} {'':<10} {'':<10} {grand_total:>12.2f}")
        print("="*70 + "\n")
    
    def release(self):
        """Release video capture resources."""
        # Print performance metrics before releasing
        self._print_performance_metrics()
        
        if hasattr(self, 'cap'):
            self.cap.release()
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.release()
