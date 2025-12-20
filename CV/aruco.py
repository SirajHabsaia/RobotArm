import cv2
import numpy as np
import time
from aruco_config import get_aruco_detector
from helper import *


class BoardDetector:
    """Handles chess board detection and piece recognition"""
    
    def __init__(self, video_path="video.mp4", use_video=True, enable_performance_metrics=False):
        self.USE_VIDEO = use_video
        self.VIDEO_PATH = video_path
        self.PROCESS_EVERY_N_FRAMES = 1
        self.VIDEO_SPEED = 1
        self.enable_performance_metrics = enable_performance_metrics
        
        # Initialize video capture
        if self.USE_VIDEO:
            self.cap = cv2.VideoCapture(self.VIDEO_PATH)
            if not self.cap.isOpened():
                raise FileNotFoundError(f"Couldn't open video: {self.VIDEO_PATH}")
        
        # ArUco detector
        self.detector = get_aruco_detector()
        self.PTS_UPDATE_THRESHOLD = 3
        self.UPDATE_EVERY_N_FRAMES = 3

        self.pts = None
        self.pts_exterior = None
        self.frame_count = 0
        self.processed_frame_count = 0
        self.updated_frame_count = self.UPDATE_EVERY_N_FRAMES
        self.last_frame_time = time.time()
        
        # Store last cropped images
        self.cropped = None
        self.big_cropped = None
        
        # Hand detection variables
        self.HAND_HISTORY_SIZE = 10
        self.HAND_COLOR_DIFF_THRESHOLD = 20
        self.HAND_COOLDOWN_FRAMES = 4
        self.REWIND_FRAME_COUNT = 4

        self.hand_history = []
        self.hand_cooldown = 0
        self.first_frame_average = None
        self.hand_frozen = False
        
        # Result frame history
        self.result_frame_history = []
        self.result_data_history = []
        self.frozen_result_frame = None
        self.board_state = None
        
        # Detection weights
        self.color_weight = 0.3
        self.contour_weight = 0.7
        
        # Performance metrics
        if self.enable_performance_metrics:
            self.perf_metrics = {
                'aruco_detection': [],
                'hand_detection': [],
                'piece_color_detection': [],
                'piece_contour_detection': [],
                'total_frame_processing': []
            }
    
    def process_frame(self, return_debug_images=False):
        """Process one frame and return results"""
        frame_start_time = time.time() if self.enable_performance_metrics else None
        
        if self.USE_VIDEO:
            ret, img = self.cap.read()
            if not ret:
                return None
            
            self.frame_count += 1
            
            # Skip frames if needed
            if self.frame_count % self.PROCESS_EVERY_N_FRAMES != 0:
                return None
            
            # Video speed control
            if self.VIDEO_SPEED < 1.0:
                current_time = time.time()
                time_per_frame = 1.0 / (30 * self.VIDEO_SPEED)
                elapsed = current_time - self.last_frame_time
                if elapsed < time_per_frame:
                    time.sleep(time_per_frame - elapsed)
                self.last_frame_time = time.time()
        
        # Run ArUco detection only once every UPDATE_EVERY_N_FRAMES frames
        self.updated_frame_count += 1
        should_update_aruco = self.updated_frame_count >= self.UPDATE_EVERY_N_FRAMES
        
        if should_update_aruco:
            aruco_start_time = time.time() if self.enable_performance_metrics else None
            
            # Detect ArUco markers
            corners, ids, rejected = self.detector.detectMarkers(img)
            if ids is None or len(ids) < 4:
                if self.pts is None:
                    return None
            else:
                ids = ids.flatten()
                sorted_idx = np.argsort(ids)
                sorted_ids = ids[sorted_idx]
                sorted_corners = [corners[i] for i in sorted_idx]
                
                if np.array_equal(sorted_ids, [0, 1, 2, 3]):
                    new_pts_interior = np.array([
                        sorted_corners[0][0][2],
                        sorted_corners[1][0][3],
                        sorted_corners[2][0][0],
                        sorted_corners[3][0][1]
                    ], dtype=np.float32)
                    
                    new_pts_exterior = np.array([
                        sorted_corners[0][0][0],
                        sorted_corners[1][0][1],
                        sorted_corners[2][0][2],
                        sorted_corners[3][0][3]
                    ], dtype=np.float32)
                    
                    if self.pts is None:
                        self.pts = new_pts_interior
                        self.pts_exterior = new_pts_exterior
                    else:
                        point_diffs = np.linalg.norm(new_pts_interior - self.pts, axis=1)
                        max_movement = np.max(point_diffs)
                        
                        if max_movement > self.PTS_UPDATE_THRESHOLD:
                            self.pts = new_pts_interior
                            self.pts_exterior = new_pts_exterior
            
            if self.pts is None:
                return None
            
            # Update cropped regions
            self.cropped, self.big_cropped = self._get_cropped_regions(img)
            self.updated_frame_count = 0
            
            if self.enable_performance_metrics:
                self.perf_metrics['aruco_detection'].append(time.time() - aruco_start_time)
        else:
            # Reuse previous cropped images
            if self.cropped is None or self.big_cropped is None:
                return None
        
        self.processed_frame_count += 1
        
        # Hand detection
        hand_start_time = time.time() if self.enable_performance_metrics else None
        hand_result = self._detect_hand(self.cropped, self.big_cropped)
        if self.enable_performance_metrics:
            self.perf_metrics['hand_detection'].append(time.time() - hand_start_time)
        
        # Always create hand detection display (don't freeze this window)
        hand_visual = self._create_hand_display(self.big_cropped, hand_result['state_label'], 
                                                  hand_result['max_color_diff'])
        
        if hand_result['skip_processing']:
            result = {
                'hand_detection_display': hand_visual,
                'overall_display': hand_result.get('frozen_display'),
                'board_state': self.board_state,
                'big_cropped': self.big_cropped
            }
            if return_debug_images:
                result['debug_images'] = None
            return result
        
        # Analyze board
        if return_debug_images:
            overall_board, board_state_temp, debug_images = self._analyze_board(self.cropped, return_debug_images=True)
        else:
            overall_board, board_state_temp = self._analyze_board(self.cropped)
        
        # Update histories
        self.result_frame_history.append(overall_board.copy())
        self.result_data_history.append(board_state_temp.copy())
        
        if len(self.result_frame_history) > self.REWIND_FRAME_COUNT:
            self.result_frame_history.pop(0)
            self.result_data_history.pop(0)
        
        # Use the latest board state for move detection (index -1)
        if len(self.result_data_history) > 0:
            self.board_state = self.result_data_history[-1]
        
        # Create overall display
        if self.frozen_result_frame is not None:
            overall_display = self.frozen_result_frame.copy()
        else:
            overall_display = overall_board.copy()
        
        if self.USE_VIDEO:
            cv2.putText(overall_display, f"Frame: {self.processed_frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(overall_display, hand_result['state_label'], (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        
        result = {
            'hand_detection_display': hand_visual,
            'overall_display': overall_display,
            'board_state': self.board_state,
            'big_cropped': self.big_cropped
        }
        
        if return_debug_images:
            result['debug_images'] = debug_images
        
        if self.enable_performance_metrics:
            self.perf_metrics['total_frame_processing'].append(time.time() - frame_start_time)
        
        return result
    
    def _get_cropped_regions(self, img):
        """Get cropped and big_cropped regions"""
        width_top = np.linalg.norm(self.pts[1] - self.pts[0])
        width_bottom = np.linalg.norm(self.pts[2] - self.pts[3])
        width = int(max(width_top, width_bottom))
        
        height_left = np.linalg.norm(self.pts[3] - self.pts[0])
        height_right = np.linalg.norm(self.pts[2] - self.pts[1])
        height = int(max(height_left, height_right))
        
        width_top_ext = np.linalg.norm(self.pts_exterior[1] - self.pts_exterior[0])
        width_bottom_ext = np.linalg.norm(self.pts_exterior[2] - self.pts_exterior[3])
        width_ext = int(max(width_top_ext, width_bottom_ext))
        
        height_left_ext = np.linalg.norm(self.pts_exterior[3] - self.pts_exterior[0])
        height_right_ext = np.linalg.norm(self.pts_exterior[2] - self.pts_exterior[1])
        height_ext = int(max(height_left_ext, height_right_ext))
        
        dst_pts = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
        dst_pts_ext = np.array([[0, 0], [width_ext - 1, 0], [width_ext - 1, height_ext - 1], [0, height_ext - 1]], dtype=np.float32)
        
        M = cv2.getPerspectiveTransform(self.pts, dst_pts)
        cropped = cv2.warpPerspective(img, M, (width, height))
        
        M_ext = cv2.getPerspectiveTransform(self.pts_exterior, dst_pts_ext)
        big_cropped = cv2.warpPerspective(img, M_ext, (width_ext, height_ext))
        
        return cropped, big_cropped
    
    def _detect_hand(self, cropped, big_cropped):
        """Perform hand detection"""
        current_stripe_regions = check_hand(cropped, big_cropped)
        
        if self.first_frame_average is None:
            self.first_frame_average = current_stripe_regions.copy()
            self.hand_history = [self.first_frame_average.copy() for _ in range(self.HAND_HISTORY_SIZE)]
        
        max_color_diff = 0
        hand_detected = False
        state_label = ""
        skip_processing = False
        
        if self.processed_frame_count >= 11:
            reference_frame = self.hand_history[0]
            color_diffs = np.linalg.norm(current_stripe_regions - reference_frame, axis=1)
            max_color_diff = np.max(color_diffs)
            
            if max_color_diff > self.HAND_COLOR_DIFF_THRESHOLD:
                hand_detected = True
            
            if self.hand_frozen:
                if hand_detected:
                    state_label = "HAND DETECTED - FROZEN"
                    skip_processing = True
                else:
                    if self.hand_cooldown == 0:
                        self.hand_cooldown = self.HAND_COOLDOWN_FRAMES
                    
                    self.hand_cooldown -= 1
                    
                    if self.hand_cooldown > 0:
                        state_label = f"COOLDOWN: {self.hand_cooldown}"
                        skip_processing = True
                    else:
                        self.hand_frozen = False
                        self.hand_cooldown = 0
                        self.frozen_result_frame = None
            else:
                if hand_detected:
                    self.hand_frozen = True
                    self.hand_cooldown = self.HAND_COOLDOWN_FRAMES
                    state_label = "HAND DETECTED - FREEZING"
                    skip_processing = True
                    
                    clean_reference = self.hand_history[0].copy()
                    self.hand_history = [clean_reference.copy() for _ in range(self.HAND_HISTORY_SIZE)]
                    
                    if len(self.result_frame_history) >= self.REWIND_FRAME_COUNT:
                        self.frozen_result_frame = self.result_frame_history[-(self.REWIND_FRAME_COUNT)].copy()
                    elif len(self.result_frame_history) > 0:
                        self.frozen_result_frame = self.result_frame_history[0].copy()
                    else:
                        self.frozen_result_frame = None
                    
                    # Trim both histories to stay synchronized
                    if len(self.result_frame_history) >= self.REWIND_FRAME_COUNT:
                        self.result_frame_history = self.result_frame_history[:-(self.REWIND_FRAME_COUNT-1)]
                        self.result_data_history = self.result_data_history[:-(self.REWIND_FRAME_COUNT-1)]
                else:
                    self.hand_history.append(current_stripe_regions)
                    self.hand_history.pop(0)
                    state_label = f"NORMAL - Diff: {max_color_diff:.2f}"
        else:
            state_label = f"INITIALIZING ({self.processed_frame_count}/10)"
        
        result = {
            'skip_processing': skip_processing,
            'state_label': state_label,
            'max_color_diff': max_color_diff,
            'hand_visual': None
        }
        
        if skip_processing and self.frozen_result_frame is not None:
            frozen_display = self.frozen_result_frame.copy()
            if self.USE_VIDEO:
                cv2.putText(frozen_display, f"Frame: {self.processed_frame_count}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                cv2.putText(frozen_display, state_label, (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            result['frozen_display'] = frozen_display
        
        return result
    
    def _create_hand_display(self, big_cropped, state_label, max_color_diff):
        """Create hand detection display"""
        display = big_cropped.copy()
        if self.USE_VIDEO:
            cv2.putText(display, f"Frame: {self.processed_frame_count}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(display, state_label, (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(display, f"Stripe Diff: {max_color_diff:.2f}", (10, 110),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2, cv2.LINE_AA)
        return display
    
    def _analyze_board(self, cropped, return_debug_images=False):
        """Analyze chess board and return overall_board image and board_state matrix"""
        color_start_time = time.time() if self.enable_performance_metrics else None
        
        width = cropped.shape[1]
        height = cropped.shape[0]
        square_width = width / 8
        square_height = height / 8
        
        # Calculate average colors
        average_square_scale = 0.8
        white_square_colors = [[], [], [], []]
        black_square_colors = [[], [], [], []]
        white_avg_bgr = [None, None, None, None]
        black_avg_bgr = [None, None, None, None]
        
        def find_region(i, j):
            if (i<=3 and j<=3):
                return 0  # Top left
            elif (i>=4 and j<=3):
                return 1  # Top right
            elif (i<=3 and j>=4):
                return 2  # Bottom left
            else:
                return 3  # Bottom right
        
        for i in range(8):
            for j in range(2, 6):  # Ranks 3-6 (0-indexed: 2, 3, 4, 5)
                center_x = (i + 0.5) * square_width
                center_y = (j + 0.5) * square_height
                mean_bgr = calculate_mean(cropped, center_x, center_y, square_width, average_square_scale)
        
                if (i + j) % 2 == 0:  # White squares
                    white_square_colors[find_region(i, j)].append(mean_bgr)
                else:  # Black squares
                    black_square_colors[find_region(i, j)].append(mean_bgr)
        
        for region_idx in range(4):
            white_avg_bgr[region_idx] = np.mean(white_square_colors[region_idx], axis=0)
            black_avg_bgr[region_idx] = np.mean(black_square_colors[region_idx], axis=0)
        
        # Calculate piece colors
        piece_scale = 0.35
        white_piece_colors = []
        black_piece_colors = []
        
        for i in range(8):
            for j in (6, 7):  # White pieces area
                center_x = (i + 0.5) * square_width
                center_y = (j + 0.5) * square_height
                mean_bgr = calculate_mean(cropped, center_x, center_y, square_width, piece_scale)
                white_piece_colors.append(mean_bgr)
            
            for j in (0, 1):  # Black pieces area
                center_x = (i + 0.5) * square_width
                center_y = (j + 0.5) * square_height
                mean_bgr = calculate_mean(cropped, center_x, center_y, square_width, piece_scale)
                black_piece_colors.append(mean_bgr)
        
        white_piece_avg_bgr = np.mean(white_piece_colors, axis=0)
        black_piece_avg_bgr = np.mean(black_piece_colors, axis=0)
        
        # Check all squares by color
        check_scale = 0.45
        piece_result_color = np.full((8, 8), None)
        piece_conf_color = np.zeros((8, 8))
        white_piece_conf = np.zeros((8, 8))
        black_piece_conf = np.zeros((8, 8))
        
        for i in range(8):
            for j in range(8):
                piece_result_color[i, j], piece_conf_color[i, j], _, _, _, _, white_piece_conf[i, j], black_piece_conf[i, j] = check_square_by_color(
                    cropped, i, j, square_width, square_height,
                    white_avg_bgr[find_region(i, j)], black_avg_bgr[find_region(i, j)],
                    white_piece_avg_bgr, black_piece_avg_bgr,
                    piece_scale=check_scale)
        
        if self.enable_performance_metrics:
            self.perf_metrics['piece_color_detection'].append(time.time() - color_start_time)
        
        # Check all squares by contour
        contour_start_time = time.time() if self.enable_performance_metrics else None
        contour_scale = 0.75
        piece_conf_contour = np.zeros((8, 8))
        empty_conf_contour = np.zeros((8, 8))
        all_contours = {}  # Store contours for visualization
        
        for i in range(8):
            for j in range(8):
                piece_conf_contour[i, j], empty_conf_contour[i, j], contours, region_bounds = check_square_by_contour(
                    cropped, i, j, square_width, square_height, sample_scale=contour_scale)
                all_contours[(i, j)] = {'contours': contours, 'bounds': region_bounds}
        
        if self.enable_performance_metrics:
            self.perf_metrics['piece_contour_detection'].append(time.time() - contour_start_time)
        
        # Calculate overall confidence
        piece_conf_color_normalized = np.zeros((8, 8))
        empty_conf_color_normalized = np.zeros((8, 8))
        
        for i in range(8):
            for j in range(8):
                if piece_result_color[i, j] is None:
                    empty_conf_color_normalized[i, j] = piece_conf_color[i, j]
                    piece_conf_color_normalized[i, j] = 1.0 - piece_conf_color[i, j]
                else:
                    piece_conf_color_normalized[i, j] = piece_conf_color[i, j]
                    empty_conf_color_normalized[i, j] = 1.0 - piece_conf_color[i, j]
        
        overall_piece_conf = self.color_weight * piece_conf_color_normalized + self.contour_weight * piece_conf_contour
        overall_empty_conf = self.color_weight * empty_conf_color_normalized + self.contour_weight * empty_conf_contour
        
        # Build debug images if requested
        debug_images = {}
        if return_debug_images:
            # Color detection visualization
            color_board = cropped.copy()
            for i in range(8):
                for j in range(8):
                    center_x = int((i + 0.5) * square_width)
                    center_y = int((j + 0.5) * square_height)
                    
                    if piece_result_color[i, j] is None:
                        label = "E"
                        color = (0, 200, 200)
                    elif piece_result_color[i, j] == 0:  # 0 = white piece
                        label = "W"
                        color = (255, 255, 255)
                    else:  # 1 = black piece
                        label = "B"
                        color = (0, 0, 0)
                    
                    label_text = f"{label}({piece_conf_color[i, j]:.2f})"
                    text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                    bg_pt1 = (center_x - text_size[0]//2 - 2, center_y - text_size[1]//2 - 2)
                    bg_pt2 = (center_x + text_size[0]//2 + 2, center_y + text_size[1]//2 + 2)
                    
                    bg_color = (0, 0, 0) if label != "B" else (255, 255, 255)
                    cv2.rectangle(color_board, bg_pt1, bg_pt2, bg_color, -1)
                    
                    text_pos = (center_x - text_size[0]//2, center_y + text_size[1]//2)
                    cv2.putText(color_board, label_text, text_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
            
            debug_images['color'] = color_board
            
            # Contour detection visualization
            contour_board = cropped.copy()
            
            # Draw all contours on the board
            for i in range(8):
                for j in range(8):
                    contour_data = all_contours[(i, j)]
                    if contour_data['contours']:
                        # Draw contours in green
                        cv2.drawContours(contour_board, contour_data['contours'], -1, (0, 255, 0), 1)
                    
                    # Draw region bounds
                    bounds = contour_data['bounds']
                    cv2.rectangle(contour_board, 
                                (bounds['x'], bounds['y']),
                                (bounds['x'] + bounds['width'], bounds['y'] + bounds['height']),
                                (255, 0, 0), 1)
            
            # Add labels after drawing contours
            for i in range(8):
                for j in range(8):
                    center_x = int((i + 0.5) * square_width)
                    center_y = int((j + 0.5) * square_height)
                    
                    if piece_conf_contour[i, j] > empty_conf_contour[i, j]:
                        label = "P"
                        color = (255, 165, 0)  # Orange for piece
                        confidence = piece_conf_contour[i, j]
                    else:
                        label = "E"
                        color = (0, 200, 200)
                        confidence = empty_conf_contour[i, j]
                    
                    label_text = f"{label}({confidence:.2f})"
                    text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                    bg_pt1 = (center_x - text_size[0]//2 - 2, center_y - text_size[1]//2 - 2)
                    bg_pt2 = (center_x + text_size[0]//2 + 2, center_y + text_size[1]//2 + 2)
                    
                    cv2.rectangle(contour_board, bg_pt1, bg_pt2, (0, 0, 0), -1)
                    
                    text_pos = (center_x - text_size[0]//2, center_y + text_size[1]//2)
                    cv2.putText(contour_board, label_text, text_pos,
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
            
            debug_images['contour'] = contour_board
        
        # Build board state and visual
        overall_board = cropped.copy()
        board_state_temp = np.full((8, 8), None)
        
        for i in range(8):
            for j in range(8):
                center_x = int((i + 0.5) * square_width)
                center_y = int((j + 0.5) * square_height)
                
                if overall_piece_conf[i, j] > overall_empty_conf[i, j]:
                    if white_piece_conf[i, j] > black_piece_conf[i, j]:
                        label = "W"
                        color = (255, 255, 255)
                        board_state_temp[i, j] = 'W'
                    else:
                        label = "B"
                        color = (0, 0, 0)
                        board_state_temp[i, j] = 'B'
                    confidence = overall_piece_conf[i, j]
                else:
                    label = "E"
                    color = (0, 200, 200)
                    confidence = overall_empty_conf[i, j]
                    board_state_temp[i, j] = None
                
                label_text = f"{label}({confidence:.2f})"
                text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
                bg_pt1 = (center_x - text_size[0]//2 - 2, center_y - text_size[1]//2 - 2)
                bg_pt2 = (center_x + text_size[0]//2 + 2, center_y + text_size[1]//2 + 2)
                
                bg_color = (0, 0, 0) if label != "B" else (255, 255, 255)
                cv2.rectangle(overall_board, bg_pt1, bg_pt2, bg_color, -1)
                
                text_pos = (center_x - text_size[0]//2, center_y + text_size[1]//2)
                cv2.putText(overall_board, label_text, text_pos,
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
        
        if return_debug_images:
            return overall_board, board_state_temp, debug_images
        return overall_board, board_state_temp
    
    def is_stable(self):
        """Check if detection is stable (not frozen or in cooldown)"""
        return not self.hand_frozen and self.processed_frame_count >= 11
    
    def print_performance_metrics(self):
        """Print performance metrics summary"""
        if not self.enable_performance_metrics:
            print("Performance metrics are not enabled. Enable them with enable_performance_metrics=True")
            return
        
        print("\n" + "="*70)
        print("PERFORMANCE METRICS")
        print("="*70)
        
        for metric_name, timings in self.perf_metrics.items():
            if not timings:
                continue
            
            avg_actual = np.mean(timings) * 1000  # Convert to ms
            count = len(timings)
            total_frames = self.processed_frame_count
            
            # Calculate effective average (accounting for skipped frames)
            if metric_name == 'aruco_detection':
                effective_avg = (avg_actual * count / total_frames) if total_frames > 0 else 0
                effective_note = f" (runs every {self.UPDATE_EVERY_N_FRAMES} frames)"
            else:
                effective_avg = avg_actual
                effective_note = ""
            
            print(f"\n{metric_name.replace('_', ' ').title()}:")
            print(f"  Actual Average:    {avg_actual:8.3f} ms{effective_note}")
            print(f"  Effective Average: {effective_avg:8.3f} ms")
            print(f"  Count:             {count:8d}")
            print(f"  Min:               {min(timings)*1000:8.3f} ms")
            print(f"  Max:               {max(timings)*1000:8.3f} ms")
        
        print("\n" + "="*70)
        print(f"Total frames processed: {self.processed_frame_count}")
        print("="*70 + "\n")
    
    def cleanup(self):
        """Release resources"""
        if self.USE_VIDEO and hasattr(self, 'cap'):
            self.cap.release()


# Standalone script mode
if __name__ == "__main__":
    detector = BoardDetector(
        #video_path="http://10.49.56.193:8080/video",
        use_video=True)
    
    while True:
        result = detector.process_frame(return_debug_images=True)
        
        if result is None:
            # Check if video ended or just no markers detected yet
            if detector.USE_VIDEO and detector.frame_count > 0:
                # Video ended
                ret, _ = detector.cap.read()
                if not ret:
                    break
            continue  # Skip this frame, don't break
        
        # Display big cropped (hand detection area)
        if result.get('big_cropped') is not None:
            cv2.imshow("Big Cropped (Hand Detection Area)", result['big_cropped'])
        
        # Display debug images if available
        if result.get('debug_images') is not None:
            cv2.imshow("Piece Color Detection", result['debug_images']['color'])
            cv2.imshow("Piece Contour Detection", result['debug_images']['contour'])
        
        # Display overall confidence
        if result['overall_display'] is not None:
            cv2.imshow("Overall Detection", result['overall_display'])
        
        # Exit on 'q' key
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
    
    detector.cleanup()
    cv2.destroyAllWindows()
