"""
Utility functions for chess board detection and CNN-based piece recognition.
Contains functions for:
- ArUco-based board cropping with time-based updates
- CNN inference for individual square classification
- Hand detection logic with time-based cooldowns
"""

import cv2
import numpy as np
import time
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image
from typing import Tuple, List, Optional, Dict, Any
import os

from aruco_config import get_aruco_detector


# ======================== CNN MODEL DEFINITION ========================

class ChessCNN(nn.Module):
    """CNN model for classifying chess squares as black piece, white piece, or empty."""
    
    def __init__(self, img_size: int = 100, num_classes: int = 3):
        super().__init__()
        self.img_size = img_size
        
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),
        )
        
        # Calculate the feature size after convolutions
        # Input: img_size -> /2 -> /2 -> /2 = img_size/8
        feature_size = img_size // 8
        
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * feature_size * feature_size, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


# ======================== CROPPING UTILITIES ========================

class BoardCropper:
    """
    Handles ArUco marker detection and perspective transformation for cropping
    the chess board from camera frames.
    
    Uses time-based updates: runs every frame until valid detection, then
    updates only when update_interval has passed.
    """
    
    def __init__(self, update_interval: float = 1.0, pts_movement_threshold: float = 3.0):
        """
        Initialize the BoardCropper.
        
        Args:
            update_interval: Minimum seconds between ArUco updates after initial detection
            pts_movement_threshold: Minimum pixel movement to trigger corner point update
        """
        self.detector = get_aruco_detector()
        self.update_interval = update_interval
        self.pts_movement_threshold = pts_movement_threshold
        
        # Corner points (interior = chess board corners, exterior = including ArUco markers)
        self.pts_interior: Optional[np.ndarray] = None
        self.pts_exterior: Optional[np.ndarray] = None
        
        # Timing
        self.last_update_time: Optional[float] = None
        self.has_valid_detection = False
        
        # Cached cropped images
        self.cropped: Optional[np.ndarray] = None
        self.big_cropped: Optional[np.ndarray] = None
    
    def update(self, frame: np.ndarray, force_update: bool = False) -> bool:
        """
        Attempt to update ArUco detection and crop the board.
        
        During initialization (no valid detection yet), runs every frame.
        After valid detection, only updates if update_interval has passed.
        
        Args:
            frame: Input BGR frame from camera/video
            force_update: If True, force ArUco detection regardless of timing
            
        Returns:
            True if cropping was successful (either new or cached), False otherwise
        """
        current_time = time.time()
        
        # Determine if we should run ArUco detection
        should_detect = force_update or not self.has_valid_detection
        
        if not should_detect and self.last_update_time is not None:
            elapsed = current_time - self.last_update_time
            should_detect = elapsed >= self.update_interval
        
        if should_detect:
            success = self._detect_and_update_corners(frame)
            if success:
                self.last_update_time = current_time
                self.has_valid_detection = True
                # Update cropped images
                self._update_cropped_images(frame)
                return True
            elif not self.has_valid_detection:
                # Still initializing, no valid corners yet
                return False
        
        # Use cached corners if we have them
        if self.has_valid_detection and self.pts_interior is not None:
            self._update_cropped_images(frame)
            return True
        
        return False
    
    def _detect_and_update_corners(self, frame: np.ndarray) -> bool:
        """
        Detect ArUco markers and update corner points.
        
        Marker layout expected:
        - Marker 0: Top-left (corner[2] is interior, corner[0] is exterior)
        - Marker 1: Top-right (corner[3] is interior, corner[1] is exterior)
        - Marker 2: Bottom-right (corner[0] is interior, corner[2] is exterior)
        - Marker 3: Bottom-left (corner[1] is interior, corner[3] is exterior)
        
        Returns:
            True if all 4 markers detected and corners updated
        """
        corners, ids, _ = self.detector.detectMarkers(frame)
        
        if ids is None or len(ids) < 4:
            return False
        
        ids = ids.flatten()
        
        # Check if we have markers 0, 1, 2, 3
        if not all(marker_id in ids for marker_id in [0, 1, 2, 3]):
            return False
        
        # Sort by ID
        sorted_idx = np.argsort(ids)
        sorted_ids = ids[sorted_idx]
        sorted_corners = [corners[i] for i in sorted_idx]
        
        # Extract only markers 0-3 if there are more
        marker_corners = {}
        for i, marker_id in enumerate(sorted_ids):
            if marker_id in [0, 1, 2, 3]:
                marker_corners[marker_id] = sorted_corners[i]
        
        # Interior corners (chess board boundaries)
        # Marker 0 (top-left): corner[2] is bottom-right of marker = top-left of board
        # Marker 1 (top-right): corner[3] is bottom-left of marker = top-right of board  
        # Marker 2 (bottom-right): corner[0] is top-left of marker = bottom-right of board
        # Marker 3 (bottom-left): corner[1] is top-right of marker = bottom-left of board
        new_pts_interior = np.array([
            marker_corners[0][0][2],  # Top-left of board
            marker_corners[1][0][3],  # Top-right of board
            marker_corners[2][0][0],  # Bottom-right of board
            marker_corners[3][0][1]   # Bottom-left of board
        ], dtype=np.float32)
        
        # Exterior corners (outside ArUco markers)
        new_pts_exterior = np.array([
            marker_corners[0][0][0],  # Top-left exterior
            marker_corners[1][0][1],  # Top-right exterior
            marker_corners[2][0][2],  # Bottom-right exterior
            marker_corners[3][0][3]   # Bottom-left exterior
        ], dtype=np.float32)
        
        # Check if we should update (significant movement or first detection)
        if self.pts_interior is None:
            self.pts_interior = new_pts_interior
            self.pts_exterior = new_pts_exterior
            return True
        
        # Check point movement
        point_diffs = np.linalg.norm(new_pts_interior - self.pts_interior, axis=1)
        max_movement = np.max(point_diffs)
        
        if max_movement > self.pts_movement_threshold:
            self.pts_interior = new_pts_interior
            self.pts_exterior = new_pts_exterior
        
        return True
    
    def _update_cropped_images(self, frame: np.ndarray):
        """Apply perspective transform to get cropped images."""
        if self.pts_interior is None or self.pts_exterior is None:
            return
        
        # Calculate interior dimensions
        width_top = np.linalg.norm(self.pts_interior[1] - self.pts_interior[0])
        width_bottom = np.linalg.norm(self.pts_interior[2] - self.pts_interior[3])
        width = int(max(width_top, width_bottom))
        
        height_left = np.linalg.norm(self.pts_interior[3] - self.pts_interior[0])
        height_right = np.linalg.norm(self.pts_interior[2] - self.pts_interior[1])
        height = int(max(height_left, height_right))
        
        # Calculate exterior dimensions
        width_top_ext = np.linalg.norm(self.pts_exterior[1] - self.pts_exterior[0])
        width_bottom_ext = np.linalg.norm(self.pts_exterior[2] - self.pts_exterior[3])
        width_ext = int(max(width_top_ext, width_bottom_ext))
        
        height_left_ext = np.linalg.norm(self.pts_exterior[3] - self.pts_exterior[0])
        height_right_ext = np.linalg.norm(self.pts_exterior[2] - self.pts_exterior[1])
        height_ext = int(max(height_left_ext, height_right_ext))
        
        # Interior crop (chess board only)
        dst_pts = np.array([
            [0, 0], 
            [width - 1, 0], 
            [width - 1, height - 1], 
            [0, height - 1]
        ], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(self.pts_interior, dst_pts)
        self.cropped = cv2.warpPerspective(frame, M, (width, height))
        
        # Exterior crop (including ArUco markers for hand detection)
        dst_pts_ext = np.array([
            [0, 0], 
            [width_ext - 1, 0], 
            [width_ext - 1, height_ext - 1], 
            [0, height_ext - 1]
        ], dtype=np.float32)
        
        M_ext = cv2.getPerspectiveTransform(self.pts_exterior, dst_pts_ext)
        self.big_cropped = cv2.warpPerspective(frame, M_ext, (width_ext, height_ext))
    
    def get_cropped(self) -> Optional[np.ndarray]:
        """Get the cropped chess board image (interior only)."""
        return self.cropped
    
    def get_big_cropped(self) -> Optional[np.ndarray]:
        """Get the cropped image including ArUco marker areas."""
        return self.big_cropped
    
    def is_initialized(self) -> bool:
        """Check if we have a valid ArUco detection."""
        return self.has_valid_detection


# ======================== CNN INFERENCE ========================

class SquareClassifier:
    """
    CNN-based classifier for individual chess squares.
    Loads the trained model and provides inference for cropped square images.
    """
    
    # Class name mapping (must match training order)
    CLASS_NAMES = ['black', 'empty', 'white']
    
    def __init__(self, model_path: str, img_size: int = 100, device: Optional[str] = None):
        """
        Initialize the classifier.
        
        Args:
            model_path: Path to the trained .pth model file
            img_size: Input image size for the model
            device: 'cuda', 'cpu', or None for auto-detection
        """
        self.img_size = img_size
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        
        # Load model
        self.model = ChessCNN(img_size=img_size, num_classes=len(self.CLASS_NAMES))
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        
        # Image transform
        self.transform = transforms.Compose([
            transforms.Resize((img_size, img_size)),
            transforms.ToTensor()
        ])
    
    def predict_single(self, square_img: np.ndarray) -> Dict[str, float]:
        """
        Predict the class of a single square image.
        
        Args:
            square_img: BGR image of the square (from OpenCV)
            
        Returns:
            Dictionary mapping class names to confidence scores
        """
        # Convert BGR to RGB and then to PIL
        rgb_img = cv2.cvtColor(square_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        
        # Transform and add batch dimension
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            output = self.model(tensor)
            probs = torch.softmax(output, dim=1).squeeze().cpu().tolist()
        
        return dict(zip(self.CLASS_NAMES, probs))
    
    def predict_batch(self, square_images: List[np.ndarray]) -> List[Dict[str, float]]:
        """
        Predict classes for a batch of square images.
        
        Args:
            square_images: List of BGR images of squares
            
        Returns:
            List of dictionaries mapping class names to confidence scores
        """
        if not square_images:
            return []
        
        # Prepare batch tensor
        tensors = []
        for img in square_images:
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_img)
            tensors.append(self.transform(pil_img))
        
        batch_tensor = torch.stack(tensors).to(self.device)
        
        # Inference
        with torch.no_grad():
            outputs = self.model(batch_tensor)
            probs = torch.softmax(outputs, dim=1).cpu().numpy()
        
        results = []
        for prob in probs:
            results.append(dict(zip(self.CLASS_NAMES, prob.tolist())))
        
        return results


def extract_squares(cropped_board: np.ndarray, square_scale: float = 0.9) -> List[Tuple[np.ndarray, int, int]]:
    """
    Extract individual square images from a cropped chess board.
    
    Args:
        cropped_board: Perspective-corrected chess board image
        square_scale: Scale factor for the extracted square (0.9 = 90% of square size)
        
    Returns:
        List of tuples: (square_image, col_index, row_index)
        where indices are 0-7 (0,0 = top-left)
    """
    height, width = cropped_board.shape[:2]
    square_width = width / 8
    square_height = height / 8
    
    squares = []
    
    for row in range(8):
        for col in range(8):
            # Calculate center of square
            center_x = (col + 0.5) * square_width
            center_y = (row + 0.5) * square_height
            
            # Calculate scaled region
            scaled_w = square_width * square_scale
            scaled_h = square_height * square_scale
            
            x1 = int(center_x - scaled_w / 2)
            y1 = int(center_y - scaled_h / 2)
            x2 = int(center_x + scaled_w / 2)
            y2 = int(center_y + scaled_h / 2)
            
            # Clamp to image bounds
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(width, x2)
            y2 = min(height, y2)
            
            square_img = cropped_board[y1:y2, x1:x2]
            squares.append((square_img, col, row))
    
    return squares


def predict_board(cropped_board: np.ndarray, classifier: SquareClassifier, 
                  square_scale: float = 0.9) -> np.ndarray:
    """
    Run CNN inference on all 64 squares and return a prediction matrix.
    
    Args:
        cropped_board: Perspective-corrected chess board image
        classifier: Initialized SquareClassifier instance
        square_scale: Scale factor for extracting squares
        
    Returns:
        8x8x3 numpy array where [row, col, :] contains [black_conf, empty_conf, white_conf]
    """
    squares = extract_squares(cropped_board, square_scale)
    
    # Extract just the images for batch prediction
    images = [sq[0] for sq in squares]
    predictions = classifier.predict_batch(images)
    
    # Build the 8x8x3 matrix
    result = np.zeros((8, 8, 3), dtype=np.float32)
    
    for i, (img, col, row) in enumerate(squares):
        pred = predictions[i]
        result[row, col, 0] = pred['black']
        result[row, col, 1] = pred['empty']
        result[row, col, 2] = pred['white']
    
    return result


def get_board_state(prediction_matrix: np.ndarray) -> np.ndarray:
    """
    Convert prediction matrix to board state.
    
    Args:
        prediction_matrix: 8x8x3 array from predict_board()
        
    Returns:
        8x8 array where each cell is 'B' (black), 'W' (white), or None (empty)
    """
    board_state = np.empty((8, 8), dtype=object)
    
    for row in range(8):
        for col in range(8):
            probs = prediction_matrix[row, col]
            class_idx = np.argmax(probs)
            
            if class_idx == 0:  # black
                board_state[row, col] = 'B'
            elif class_idx == 2:  # white
                board_state[row, col] = 'W'
            else:  # empty
                board_state[row, col] = None
    
    return board_state


# ======================== HAND DETECTION ========================

class HandDetector:
    """
    Detects hands over the chess board by analyzing contour changes in the
    border regions (between interior chess board and exterior ArUco markers).
    
    Uses time-based cooldowns instead of frame counts.
    """
    
    def __init__(self, 
                 contour_threshold: float = 500.0,
                 canny_low: int = 50,
                 canny_high: int = 150,
                 cooldown_duration: float = 0.3,
                 history_duration: float = 0.5,
                 initialization_duration: float = 1.0):
        """
        Initialize hand detector.
        
        Args:
            contour_threshold: Minimum total contour area increase to detect hand
            canny_low: Lower threshold for Canny edge detection
            canny_high: Higher threshold for Canny edge detection
            cooldown_duration: Seconds to wait after hand leaves before processing
            history_duration: Seconds of history to maintain for reference
            initialization_duration: Seconds to wait at startup before enabling detection
        """
        self.contour_threshold = contour_threshold
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.cooldown_duration = cooldown_duration
        self.history_duration = history_duration
        self.initialization_duration = initialization_duration
        
        # State
        self.reference_contours: Optional[np.ndarray] = None
        self.contour_history: List[Tuple[float, np.ndarray]] = []  # (timestamp, contour_metrics)
        
        self.is_frozen = False
        self.cooldown_start_time: Optional[float] = None
        self.start_time: Optional[float] = None
        
        self.last_contour_diff = 0.0
        
        # Debug visualization
        self.last_edges: Optional[np.ndarray] = None
        self.last_stripe_masks: List[np.ndarray] = []
    
    def _calculate_stripe_contours(self, cropped_interior: np.ndarray, 
                                     cropped_exterior: np.ndarray) -> np.ndarray:
        """
        Calculate contour metrics for 8 stripe regions between interior and exterior crops.
        
        Uses edge detection and contour analysis to detect hand presence.
        
        Regions:
        0: Top stripe, 1: Bottom stripe, 2: Left stripe, 3: Right stripe
        4: Top-left corner, 5: Top-right corner, 6: Bottom-left corner, 7: Bottom-right corner
        
        Returns:
            Array of shape (8,) containing contour area for each region
        """
        h_ext, w_ext = cropped_exterior.shape[:2]
        h_int, w_int = cropped_interior.shape[:2]
        
        offset_x = (w_ext - w_int) // 2
        offset_y = (h_ext - h_int) // 2
        
        # Convert to grayscale for edge detection
        gray = cv2.cvtColor(cropped_exterior, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)
        
        # Store for debugging
        self.last_edges = edges.copy()
        self.last_stripe_masks = []
        
        # Base mask: exterior minus interior
        base_mask = np.ones((h_ext, w_ext), dtype=np.uint8) * 255
        base_mask[offset_y:offset_y + h_int, offset_x:offset_x + w_int] = 0
        
        region_metrics = []
        
        # Helper function to calculate contour area for a region
        def calculate_region_contour_area(mask):
            # Combine with base mask
            region_mask = cv2.bitwise_and(mask, base_mask)
            # Store mask for debugging
            self.last_stripe_masks.append(region_mask.copy())
            # Extract edges in this region
            region_edges = cv2.bitwise_and(edges, edges, mask=region_mask)
            # Find contours
            contours, _ = cv2.findContours(region_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # Calculate total contour area
            total_area = sum(cv2.contourArea(c) for c in contours)
            # Also count edge pixels as an alternative metric
            edge_pixels = np.count_nonzero(region_edges)
            # Combine both metrics (weighted)
            return total_area + edge_pixels * 0.1
        
        # Top stripe
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[:offset_y, :] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Bottom stripe
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[offset_y + h_int:, :] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Left stripe
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[:, :offset_x] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Right stripe
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[:, offset_x + w_int:] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Corner calculations
        mid_x_left = offset_x // 2
        mid_x_right = offset_x + w_int + (w_ext - offset_x - w_int) // 2
        mid_y_top = offset_y // 2
        mid_y_bottom = offset_y + h_int + (h_ext - offset_y - h_int) // 2
        
        # Top-left corner
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[:offset_y, mid_x_left:offset_x] = 255
        mask[:mid_y_top, :offset_x] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Top-right corner
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[:offset_y, offset_x + w_int:mid_x_right] = 255
        mask[:mid_y_top, offset_x + w_int:] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Bottom-left corner
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[offset_y + h_int:, mid_x_left:offset_x] = 255
        mask[mid_y_bottom:, :offset_x] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        # Bottom-right corner
        mask = np.zeros((h_ext, w_ext), dtype=np.uint8)
        mask[offset_y + h_int:, offset_x + w_int:mid_x_right] = 255
        mask[mid_y_bottom:, offset_x + w_int:] = 255
        region_metrics.append(calculate_region_contour_area(mask))
        
        return np.array(region_metrics)
    
    def update(self, cropped_interior: np.ndarray, 
               cropped_exterior: np.ndarray) -> Dict[str, Any]:
        """
        Update hand detection state.
        
        Args:
            cropped_interior: Cropped chess board image
            cropped_exterior: Cropped image including ArUco areas
            
        Returns:
            Dictionary with:
            - 'hand_detected': bool
            - 'skip_processing': bool (True if hand present or in cooldown)
            - 'state': str ('initializing', 'normal', 'hand_detected', 'cooldown')
            - 'contour_diff': float (maximum contour area difference detected)
            - 'cooldown_remaining': float (seconds remaining in cooldown, if applicable)
        """
        current_time = time.time()
        
        # Initialize start time on first call
        if self.start_time is None:
            self.start_time = current_time
        
        # Calculate current stripe contours
        current_contours = self._calculate_stripe_contours(cropped_interior, cropped_exterior)
        
        # Initialize reference if needed
        if self.reference_contours is None:
            self.reference_contours = current_contours.copy()
        
        # Check if still initializing
        elapsed_since_start = current_time - self.start_time
        if elapsed_since_start < self.initialization_duration:
            # During initialization, keep updating history
            self.contour_history.append((current_time, current_contours.copy()))
            cutoff_time = current_time - self.history_duration
            self.contour_history = [(t, c) for t, c in self.contour_history if t > cutoff_time]
            
            return {
                'hand_detected': False,
                'skip_processing': True,
                'state': 'initializing',
                'contour_diff': 0.0,
                'cooldown_remaining': 0.0,
                'initialization_progress': elapsed_since_start / self.initialization_duration
            }
        
        # Calculate contour difference using the stable reference
        contour_diffs = np.abs(current_contours - self.reference_contours)
        max_contour_diff = float(np.max(contour_diffs))
        self.last_contour_diff = max_contour_diff
        
        hand_detected = max_contour_diff > self.contour_threshold
        
        # State machine
        if self.is_frozen:
            if hand_detected:
                # Still see hand, stay frozen
                return {
                    'hand_detected': True,
                    'skip_processing': True,
                    'state': 'hand_detected',
                    'contour_diff': max_contour_diff,
                    'cooldown_remaining': 0.0
                }
            else:
                # Hand gone, start/continue cooldown
                if self.cooldown_start_time is None:
                    self.cooldown_start_time = current_time
                
                elapsed_cooldown = current_time - self.cooldown_start_time
                
                if elapsed_cooldown < self.cooldown_duration:
                    return {
                        'hand_detected': False,
                        'skip_processing': True,
                        'state': 'cooldown',
                        'contour_diff': max_contour_diff,
                        'cooldown_remaining': self.cooldown_duration - elapsed_cooldown
                    }
                else:
                    # Cooldown finished
                    self.is_frozen = False
                    self.cooldown_start_time = None
                    # Reset history to current state
                    self.contour_history = [(current_time, current_contours.copy())]
                    self.reference_contours = current_contours.copy()
                    
                    return {
                        'hand_detected': False,
                        'skip_processing': False,
                        'state': 'normal',
                        'contour_diff': max_contour_diff,
                        'cooldown_remaining': 0.0
                    }
        else:
            if hand_detected:
                # Hand detected, freeze and save clean reference
                self.is_frozen = True
                self.cooldown_start_time = None
                
                # Save the clean reference from history (before hand entered)
                # Use the oldest entry as the clean state
                if self.contour_history:
                    self.reference_contours = self.contour_history[0][1].copy()
                
                return {
                    'hand_detected': True,
                    'skip_processing': True,
                    'state': 'hand_detected',
                    'contour_diff': max_contour_diff,
                    'cooldown_remaining': 0.0
                }
            else:
                # Normal operation - update history and reference
                self.contour_history.append((current_time, current_contours.copy()))
                
                # Clean old history entries
                cutoff_time = current_time - self.history_duration
                self.contour_history = [(t, c) for t, c in self.contour_history if t > cutoff_time]
                
                # Update reference from oldest history entry
                if self.contour_history:
                    self.reference_contours = self.contour_history[0][1]
                
                return {
                    'hand_detected': False,
                    'skip_processing': False,
                    'state': 'normal',
                    'contour_diff': max_contour_diff,
                    'cooldown_remaining': 0.0
                }
    
    def reset(self):
        """Reset the hand detector state."""
        self.reference_contours = None
        self.contour_history = []
        self.is_frozen = False
        self.cooldown_start_time = None
        self.start_time = None
        self.last_contour_diff = 0.0
        self.last_edges = None
        self.last_stripe_masks = []
    
    def get_debug_visualization(self, cropped_exterior: np.ndarray) -> Optional[np.ndarray]:
        """
        Create a debug visualization showing detected edges and stripe regions.
        
        Args:
            cropped_exterior: The exterior cropped image
            
        Returns:
            BGR image with edges and stripe regions visualized, or None if no data
        """
        if self.last_edges is None:
            return None
        
        # Create colored visualization
        debug_img = cropped_exterior.copy()
        
        # Convert edges to color (green)
        edges_colored = cv2.cvtColor(self.last_edges, cv2.COLOR_GRAY2BGR)
        edges_colored[:, :, 0] = 0  # Remove blue
        edges_colored[:, :, 2] = 0  # Remove red, keep green
        
        # Overlay edges on the image
        debug_img = cv2.addWeighted(debug_img, 0.7, edges_colored, 0.3, 0)
        
        # Draw stripe region boundaries in different colors
        colors = [
            (255, 0, 0),    # Blue - Top
            (255, 128, 0),  # Cyan - Bottom
            (0, 255, 0),    # Green - Left
            (0, 255, 255),  # Yellow - Right
            (128, 0, 255),  # Purple - Top-left corner
            (255, 0, 255),  # Magenta - Top-right corner
            (0, 128, 255),  # Orange - Bottom-left corner
            (128, 255, 0)   # Lime - Bottom-right corner
        ]
        
        region_names = [
            "Top", "Bottom", "Left", "Right",
            "TL", "TR", "BL", "BR"
        ]
        
        # Draw contours for each region
        for i, mask in enumerate(self.last_stripe_masks):
            if i < len(colors):
                # Find contours in the masked edge region
                region_edges = cv2.bitwise_and(self.last_edges, self.last_edges, mask=mask)
                contours, _ = cv2.findContours(region_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Draw contours
                cv2.drawContours(debug_img, contours, -1, colors[i], 2)
                
                # Find a good position to place the label
                mask_coords = np.where(mask > 0)
                if len(mask_coords[0]) > 0:
                    label_y = int(np.mean(mask_coords[0]))
                    label_x = int(np.mean(mask_coords[1]))
                    
                    # Draw region label
                    cv2.putText(debug_img, region_names[i], (label_x, label_y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors[i], 2)
        
        return debug_img