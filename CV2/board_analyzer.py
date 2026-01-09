"""
Chess Board Analyzer using CNN-based piece detection.

This module provides a clean implementation of chess board analysis using:
- ArUco markers for board detection and perspective correction
- PyTorch CNN for piece classification (black/white/empty)
- Time-based hand detection and cooldown logic

Usage:
    analyzer = BoardAnalyzer(model_path="model.pth")
    
    # Process frames in a loop
    while True:
        frame = capture_frame()
        result = analyzer.process_frame(frame)
        
        if result is not None:
            board_state = result['board_state']
            # Use board_state for your application
"""

import cv2
import numpy as np
import os
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field

from utils import (
    BoardCropper, 
    SquareClassifier, 
    HandDetector,
    predict_board,
    get_board_state
)


@dataclass
class BoardAnalyzerConfig:
    """Configuration for BoardAnalyzer with all tunable parameters."""
    
    # Model settings
    model_path: str = "model.pth"
    img_size: int = 100
    device: Optional[str] = None  # 'cuda', 'cpu', or None for auto
    
    # ArUco/Cropping settings
    aruco_update_interval: float = 1.0  # Seconds between ArUco updates after init
    pts_movement_threshold: float = 3.0  # Minimum pixel movement to update corners
    
    # Square extraction settings
    square_scale: float = 0.9  # Scale factor for extracting square images
    
    # Hand detection settings
    hand_contour_threshold: float = 300.0  # Minimum contour area increase for hand detection
    hand_canny_low: int = 100  # Canny edge detection lower threshold
    hand_canny_high: int = 200  # Canny edge detection higher threshold
    hand_cooldown_duration: float = 2  # Seconds to wait after hand leaves
    hand_history_duration: float = 0.5  # Seconds of contour history to maintain
    hand_initialization_duration: float = 1.0  # Seconds to wait at startup
    
    # Video settings (for standalone mode)
    video_path: str = "video.mp4"
    use_video: bool = True


class BoardAnalyzer:
    """
    Main class for analyzing chess board positions from camera/video input.
    
    Combines ArUco detection, CNN inference, and hand detection into a
    single cohesive interface.
    """
    
    def __init__(self, config: Optional[BoardAnalyzerConfig] = None, **kwargs):
        """
        Initialize the BoardAnalyzer.
        
        Args:
            config: BoardAnalyzerConfig instance, or None to use defaults
            **kwargs: Override individual config parameters
        """
        # Build config
        if config is None:
            config = BoardAnalyzerConfig()
        
        # Override with kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        self.config = config
        
        # Resolve model path (relative to this file if not absolute)
        model_path = config.model_path
        if not os.path.isabs(model_path):
            model_path = os.path.join(os.path.dirname(__file__), model_path)
        
        # Initialize components
        self.cropper = BoardCropper(
            update_interval=config.aruco_update_interval,
            pts_movement_threshold=config.pts_movement_threshold
        )
        
        self.classifier = SquareClassifier(
            model_path=model_path,
            img_size=config.img_size,
            device=config.device
        )
        
        self.hand_detector = HandDetector(
            contour_threshold=config.hand_contour_threshold,
            canny_low=config.hand_canny_low,
            canny_high=config.hand_canny_high,
            cooldown_duration=config.hand_cooldown_duration,
            history_duration=config.hand_history_duration,
            initialization_duration=config.hand_initialization_duration
        )
        
        # State
        self.board_state: Optional[np.ndarray] = None
        self.prediction_matrix: Optional[np.ndarray] = None
        self.last_stable_board_state: Optional[np.ndarray] = None
        
        # Video capture (for standalone mode)
        self.cap = None
        if config.use_video:
            self.cap = cv2.VideoCapture(config.video_path)
            if not self.cap.isOpened():
                raise ValueError(f"Could not open video source: {config.video_path}")
    
    def process_frame(self, frame: Optional[np.ndarray] = None) -> Optional[Dict[str, Any]]:
        """
        Process a single frame and return analysis results.
        
        If frame is None and use_video is True, reads from video capture.
        
        Args:
            frame: BGR image frame, or None to read from video
            
        Returns:
            Dictionary with analysis results, or None if processing should be skipped.
            
            Keys:
            - 'cropped': Cropped chess board image
            - 'big_cropped': Cropped image including ArUco areas
            - 'board_state': 8x8 numpy array with 'B', 'W', or None
            - 'prediction_matrix': 8x8x3 numpy array with class probabilities
            - 'hand_status': Dict with hand detection info
            - 'is_stable': bool indicating if detection is stable (no hand, not initializing)
        """
        # Get frame if not provided
        if frame is None:
            if self.cap is not None:
                ret, frame = self.cap.read()
                if not ret:
                    return None
            else:
                return None
        
        # Step 1: Crop the board using ArUco markers
        if not self.cropper.update(frame):
            # Still initializing ArUco detection
            return None
        
        cropped = self.cropper.get_cropped()
        big_cropped = self.cropper.get_big_cropped()
        
        if cropped is None or big_cropped is None:
            return None
        
        # Step 2: Check for hand presence
        hand_status = self.hand_detector.update(cropped, big_cropped)
        
        # Build result dict
        result = {
            'cropped': cropped,
            'big_cropped': big_cropped,
            'board_state': self.last_stable_board_state,
            'prediction_matrix': self.prediction_matrix,
            'hand_status': hand_status,
            'is_stable': not hand_status['skip_processing']
        }
        
        # Step 3: Run CNN inference if no hand detected
        if not hand_status['skip_processing']:
            # Run CNN inference
            self.prediction_matrix = predict_board(
                cropped, 
                self.classifier, 
                self.config.square_scale
            )
            
            # Convert to board state
            self.board_state = get_board_state(self.prediction_matrix)
            self.last_stable_board_state = self.board_state.copy()
            
            result['board_state'] = self.board_state
            result['prediction_matrix'] = self.prediction_matrix
        
        return result
    
    def get_board_state(self) -> Optional[np.ndarray]:
        """Get the current board state (8x8 array with 'B', 'W', or None)."""
        return self.last_stable_board_state
    
    def is_stable(self) -> bool:
        """Check if the analyzer is in a stable state (no hand, initialized)."""
        return (
            self.cropper.is_initialized() and 
            not self.hand_detector.is_frozen and
            self.last_stable_board_state is not None
        )
    
    def reset(self):
        """Reset the analyzer state."""
        self.hand_detector.reset()
        self.board_state = None
        self.prediction_matrix = None
        self.last_stable_board_state = None
    
    def cleanup(self):
        """Release resources."""
        if self.cap is not None:
            self.cap.release()
    
    def create_visualization(self, cropped: np.ndarray, 
                            prediction_matrix: np.ndarray,
                            hand_status: Dict[str, Any]) -> np.ndarray:
        """
        Create a visualization of the board analysis.
        
        Args:
            cropped: Cropped chess board image
            prediction_matrix: 8x8x3 prediction matrix
            hand_status: Hand detection status dictionary
            
        Returns:
            Annotated image with predictions overlaid
        """
        display = cropped.copy()
        height, width = display.shape[:2]
        square_width = width / 8
        square_height = height / 8
        
        for row in range(8):
            for col in range(8):
                probs = prediction_matrix[row, col]
                class_idx = np.argmax(probs)
                confidence = probs[class_idx]
                
                center_x = int((col + 0.5) * square_width)
                center_y = int((row + 0.5) * square_height)
                
                # Determine label and color
                if class_idx == 0:  # black
                    label = "B"
                    color = (0, 0, 0)
                    bg_color = (255, 255, 255)
                elif class_idx == 2:  # white
                    label = "W"
                    color = (255, 255, 255)
                    bg_color = (0, 0, 0)
                else:  # empty
                    label = "E"
                    color = (0, 200, 200)
                    bg_color = (0, 0, 0)
                
                label_text = f"{label}({confidence:.2f})"
                text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                
                # Draw background rectangle
                bg_pt1 = (center_x - text_size[0]//2 - 2, center_y - text_size[1]//2 - 2)
                bg_pt2 = (center_x + text_size[0]//2 + 2, center_y + text_size[1]//2 + 2)
                cv2.rectangle(display, bg_pt1, bg_pt2, bg_color, -1)
                
                # Draw text
                text_pos = (center_x - text_size[0]//2, center_y + text_size[1]//2)
                cv2.putText(display, label_text, text_pos,
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        
        # Add hand status overlay
        state_label = hand_status.get('state', 'unknown')
        contour_diff = hand_status.get('contour_diff', 0.0)
        
        cv2.putText(display, f"State: {state_label}", (10, 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(display, f"Contour Diff: {contour_diff:.2f}", (10, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
        
        return display


def print_board_state(board_state: np.ndarray):
    """Pretty print the board state."""
    print("\n  a b c d e f g h")
    print(" +" + "-"*17 + "+")
    for row in range(8):
        rank = 8 - row
        row_str = f"{rank}|"
        for col in range(8):
            cell = board_state[row, col]
            if cell is None:
                row_str += " ."
            elif cell == 'B':
                row_str += " B"
            else:
                row_str += " W"
        row_str += f" |{rank}"
        print(row_str)
    print(" +" + "-"*17 + "+")
    print("  a b c d e f g h\n")


# ======================== STANDALONE EXECUTION ========================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Chess Board Analyzer")
    parser.add_argument("--video", type=str, default="video.mp4", help="Path to video file")
    parser.add_argument("--model", type=str, default="model.pth", help="Path to CNN model")
    parser.add_argument("--camera", type=int, default=None, help="Camera index (overrides --video)")
    args = parser.parse_args()
    
    # Determine video source
    video_source = args.video
    if args.camera is not None:
        video_source = args.camera
    
    # Check if video file exists (if it's a file path)
    if args.camera is None and not os.path.exists(args.video):
        print(f"Error: Video file '{args.video}' not found.")
        print(f"Please provide a valid video file with --video or use --camera <index> for webcam.")
        exit(1)
    
    # Create analyzer
    config = BoardAnalyzerConfig(
        model_path=args.model,
        video_path=str(video_source),
        use_video=True
    )
    
    try:
        analyzer = BoardAnalyzer(config=config)
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)
    
    print("Starting board analysis...")
    print("Press 'q' to quit, 's' to show current board state")
    print(f"Video source: {video_source}")
    print(f"Waiting for ArUco marker detection...")
    
    prev_board_state = None
    
    frame_count = 0
    try:
        while True:
            result = analyzer.process_frame()
            frame_count += 1
            
            if result is None:
                # During initialization, result will be None
                # Only check for video end if we've processed some frames
                if frame_count > 100:
                    # Might be stuck, check if video actually ended
                    if analyzer.cap is not None:
                        current_pos = analyzer.cap.get(cv2.CAP_PROP_POS_FRAMES)
                        total_frames = analyzer.cap.get(cv2.CAP_PROP_FRAME_COUNT)
                        if total_frames > 0 and current_pos >= total_frames - 1:
                            print("Video ended.")
                            break
                continue
            
            # Create and display visualization
            if result.get('prediction_matrix') is not None:
                vis = analyzer.create_visualization(
                    result['cropped'],
                    result['prediction_matrix'],
                    result['hand_status']
                )
                cv2.imshow("Board Analysis", vis)
            
            # Display big cropped for hand detection visualization
            if result.get('big_cropped') is not None:
                big_display = result['big_cropped'].copy()
                hand_status = result['hand_status']
                
                # Get debug visualization with contours
                debug_vis = analyzer.hand_detector.get_debug_visualization(result['big_cropped'])
                if debug_vis is not None:
                    big_display = debug_vis
                
                # Add status text
                cv2.putText(big_display, f"State: {hand_status['state']}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(big_display, f"Contour Diff: {hand_status['contour_diff']:.2f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(big_display, f"Threshold: {analyzer.hand_detector.contour_threshold:.1f}", (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow("Hand Detection", big_display)
            
            # Check for board state changes
            if result['is_stable'] and result.get('board_state') is not None:
                current_state = result['board_state']
                if prev_board_state is None or not np.array_equal(current_state, prev_board_state):
                    print("\n=== Board State Changed ===")
                    print_board_state(current_state)
                    prev_board_state = current_state.copy()
            
            # Handle key input
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                if analyzer.get_board_state() is not None:
                    print("\n=== Current Board State ===")
                    print_board_state(analyzer.get_board_state())
    
    finally:
        analyzer.cleanup()
        cv2.destroyAllWindows()
        print("Analyzer stopped.")