import cv2
import numpy as np


def calculate_mean(image, center_x, center_y, width, scale=1.0):
    """
    Calculate the average BGR color of a square region in an image.
    
    Parameters:
    -----------
    image : numpy.ndarray
        The input image in BGR format
    center_x : float
        X-coordinate of the square's center
    center_y : float
        Y-coordinate of the square's center
    width : float
        Width (and height) of the square before scaling
    scale : float, optional
        Scale factor to apply to the square size (default: 1.0)
        Example: 0.8 means use 80% of the full square size
    
    Returns:
    --------
    tuple
        A tuple of (B, G, R) representing the average color values (0-255)
    
    Example:
    --------
    >>> avg_color = calculate_mean(img, 100.5, 100.5, 50, scale=0.8)
    >>> print(f"BGR: {avg_color}")
    BGR: (120.5, 135.2, 150.8)
    """
    # Calculate scaled square dimensions
    scaled_width = width * scale
    scaled_height = width * scale  # Square, so height = width
    
    # Calculate top-left and bottom-right corners of the scaled region
    top_left_x = int(center_x - scaled_width / 2)
    top_left_y = int(center_y - scaled_height / 2)
    bottom_right_x = int(center_x + scaled_width / 2)
    bottom_right_y = int(center_y + scaled_height / 2)
    
    # Ensure coordinates are within image bounds
    top_left_x = max(0, top_left_x)
    top_left_y = max(0, top_left_y)
    bottom_right_x = min(image.shape[1], bottom_right_x)
    bottom_right_y = min(image.shape[0], bottom_right_y)
    
    # Extract the region
    region = image[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
    
    # Calculate and return mean BGR values
    mean_bgr = cv2.mean(region)[:3]  # Get B, G, R (ignore alpha channel if present)
    
    return mean_bgr

def check_square_by_color(image, i, j, square_width, square_height, empty_white_avg, empty_black_avg, 
                 white_piece_avg, black_piece_avg, piece_scale=0.5, perspective_correction=0.01):
    """
    Check if a chess square contains a piece and determine its color.
    
    Parameters:
    -----------
    image : numpy.ndarray
        The cropped chessboard image in BGR format
    i : int
        Column index (0-7, where 0 is leftmost)
    j : int
        Row index (0-7, where 0 is top)
    square_width : float
        Width of a single square on the board
    square_height : float
        Height of a single square on the board
    empty_white_avg : tuple or np.ndarray
        BGR color of empty white squares (B, G, R)
    empty_black_avg : tuple or np.ndarray
        BGR color of empty black squares (B, G, R)
    white_piece_avg : tuple or np.ndarray
        BGR color of white pieces (B, G, R)
    black_piece_avg : tuple or np.ndarray
        BGR color of black pieces (B, G, R)
    piece_scale : float, optional
        Scale factor for sampling region (default: 0.5)
    perspective_correction : float, optional
        Correction factor for perspective distortion (default: 0.02)
    
    Returns:
    --------
    tuple : (piece_type, confidence, corrected_center_x, corrected_center_y, scaled_width, scaled_height)
        piece_type : None, 0, or 1
            None = empty square
            0 = white piece
            1 = black piece
        confidence : float
            Value between 0 and 1 indicating confidence level
        corrected_center_x, corrected_center_y : float
            The corrected center coordinates used for sampling
        scaled_width, scaled_height : float
            The dimensions of the sampling region
    
    Example:
    --------
    >>> result, conf, cx, cy, sw, sh = check_square(board, 0, 0, 50, 50, white_sq, black_sq, white_pc, black_pc)
    """
    # Calculate center of the square
    center_x = (i + 0.5) * square_width
    center_y = (j + 0.5) * square_height
    
    # Calculate board center
    board_center_x = 4.0 * square_width
    board_center_y = 4.0 * square_height
    
    # Calculate distance from board center to square center
    dx = center_x - board_center_x
    dy = center_y - board_center_y
    
    # Apply perspective correction - shift center towards distortion direction
    corrected_center_x = center_x + dx * perspective_correction
    corrected_center_y = center_y + dy * perspective_correction
    
    # Calculate scaled dimensions
    scaled_width = square_width * piece_scale
    scaled_height = square_height * piece_scale
    
    # Get the average color of the center region
    observed_color = np.array(calculate_mean(image, corrected_center_x, corrected_center_y, 
                                             (scaled_width + scaled_height) / 2, piece_scale))
    
    # Determine if this is a white or black square
    is_white_square = (i + j) % 2 == 0
    empty_color = np.array(empty_white_avg if is_white_square else empty_black_avg)
    
    # Calculate Euclidean distances to reference colors
    dist_empty = np.linalg.norm(observed_color - empty_color)
    dist_white_piece = np.linalg.norm(observed_color - np.array(white_piece_avg))
    dist_black_piece = np.linalg.norm(observed_color - np.array(black_piece_avg))
    
    # Find the minimum distance
    distances = [dist_empty, dist_white_piece, dist_black_piece]
    min_dist_idx = np.argmin(distances)
    min_dist = distances[min_dist_idx]
    
    # Calculate confidence based on how much closer the best match is compared to others
    # Use softmax-like approach: confidence is based on the ratio of distances
    total_dist = sum(distances)
    if total_dist == 0:
        confidence = 1.0
        white_conf = 0.33
        black_conf = 0.33
    else:
        # Inverse distance weighting - closer = higher confidence
        weights = [1 / (d + 1e-6) for d in distances]
        total_weight = sum(weights)
        confidence = weights[min_dist_idx] / total_weight
        white_conf = weights[1] / total_weight  # White piece confidence
        black_conf = weights[2] / total_weight  # Black piece confidence
    
    # Map index to result
    if min_dist_idx == 0:
        result = None  # Empty square
    elif min_dist_idx == 1:
        result = 0  # White piece
    else:
        result = 1  # Black piece
    
    return result, confidence, corrected_center_x, corrected_center_y, scaled_width, scaled_height, white_conf, black_conf

def check_square_by_contour(image, i, j, square_width, square_height, sample_scale=0.8, 
                             canny_low=25, canny_high=40):
    """
    Check if a chess square contains a piece using contour density analysis.
    
    Performs Canny edge detection on a scaled region of the square (default 80%) and 
    analyzes the contour density to determine piece presence and emptiness confidence.
    
    Parameters:
    -----------
    image : numpy.ndarray
        The cropped chessboard image in BGR format
    i : int
        Column index (0-7, where 0 is leftmost)
    j : int
        Row index (0-7, where 0 is top)
    square_width : float
        Width of a single square on the board
    square_height : float
        Height of a single square on the board
    sample_scale : float, optional
        Scale factor for the region to analyze (default: 0.8 for 80%)
    canny_low : int, optional
        Lower threshold for Canny edge detection (default: 50)
    canny_high : int, optional
        Higher threshold for Canny edge detection (default: 150)
    
    Returns:
    --------
    tuple : (piece_confidence, empty_confidence, contours, region_bounds)
        piece_confidence : float
            Confidence (0-1) that a piece exists in the square
        empty_confidence : float
            Confidence (0-1) that the square is empty
        contours : list
            List of contours found in the region (for visualization)
        region_bounds : dict
            Dictionary with 'x', 'y', 'width', 'height' of the analyzed region
    
    Example:
    --------
    >>> piece_conf, empty_conf, contours, bounds = check_square_by_contour(board, 0, 0, 50, 50)
    """
    # Calculate center of the square
    center_x = (i + 0.5) * square_width
    center_y = (j + 0.5) * square_height
    
    # Calculate scaled dimensions
    scaled_width = square_width * sample_scale
    scaled_height = square_height * sample_scale
    
    # Calculate region boundaries
    top_left_x = int(center_x - scaled_width / 2)
    top_left_y = int(center_y - scaled_height / 2)
    bottom_right_x = int(center_x + scaled_width / 2)
    bottom_right_y = int(center_y + scaled_height / 2)
    
    # Ensure coordinates are within image bounds
    top_left_x = max(0, top_left_x)
    top_left_y = max(0, top_left_y)
    bottom_right_x = min(image.shape[1], bottom_right_x)
    bottom_right_y = min(image.shape[0], bottom_right_y)
    
    # Extract the region
    region = image[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
    
    # Convert to grayscale
    gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    
    # Apply Canny edge detection
    edges = cv2.Canny(gray_region, canny_low, canny_high)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Calculate contour density metrics
    region_area = region.shape[0] * region.shape[1]
    if region_area == 0:
        return 0.0, 1.0, [], {'x': top_left_x, 'y': top_left_y, 'width': 0, 'height': 0}
    
    # Total contour area
    total_contour_area = sum(cv2.contourArea(c) for c in contours)
    
    # Number of edge pixels
    edge_pixel_count = np.count_nonzero(edges)
    
    # Calculate densities
    contour_density = total_contour_area / region_area
    edge_density = edge_pixel_count / region_area
    
    # Combine metrics for confidence calculation
    # Higher density = higher piece confidence
    # Normalize densities to 0-1 range using sigmoid-like function
    piece_confidence = min(1.0, (contour_density * 10 + edge_density * 5))
    empty_confidence = 1.0 - piece_confidence
    
    # Adjust contours coordinates to absolute image coordinates
    adjusted_contours = []
    for contour in contours:
        adjusted_contour = contour.copy()
        adjusted_contour[:, 0, 0] += top_left_x
        adjusted_contour[:, 0, 1] += top_left_y
        adjusted_contours.append(adjusted_contour)
    
    region_bounds = {
        'x': top_left_x,
        'y': top_left_y,
        'width': bottom_right_x - top_left_x,
        'height': bottom_right_y - top_left_y
    }
    
    return piece_confidence, empty_confidence, adjusted_contours, region_bounds

def check_hand(cropped_interior, cropped_exterior):
    """
    Calculate average colors of 8 stripe regions between the interior cropped image 
    (chess board) and exterior cropped image (including QR codes).
    
    The 8 regions are:
    0: Top stripe (full width)
    1: Bottom stripe (full width)
    2: Left stripe (full height)
    3: Right stripe (full height)
    4: Top-left corner (right half of top-left + upper half of left stripe)
    5: Top-right corner (left half of top-right + upper half of right stripe)
    6: Bottom-left corner (right half of bottom-left + lower half of left stripe)
    7: Bottom-right corner (left half of bottom-right + lower half of right stripe)
    
    Parameters:
    -----------
    cropped_interior : numpy.ndarray
        The interior cropped image (chess board only) in BGR format
    cropped_exterior : numpy.ndarray
        The exterior cropped image (including QR codes) in BGR format
    
    Returns:
    --------
    numpy.ndarray
        Array of shape (8, 3) containing average BGR colors for each of the 8 stripe regions
    
    Example:
    --------
    >>> region_avgs = check_hand(cropped, big_cropped)
    >>> print(f"Top stripe average: {region_avgs[0]}")
    """
    h_ext, w_ext = cropped_exterior.shape[:2]
    h_int, w_int = cropped_interior.shape[:2]
    
    # Calculate the offset to center the interior region within exterior region
    offset_x = (w_ext - w_int) // 2
    offset_y = (h_ext - h_int) // 2
    
    # Create base mask for the stripe regions (exterior minus interior)
    base_mask = np.ones((h_ext, w_ext), dtype=np.uint8) * 255
    base_mask[offset_y:offset_y + h_int, offset_x:offset_x + w_int] = 0
    
    region_averages = []
    
    # Region 0: Top stripe (full width)
    mask_top = np.zeros((h_ext, w_ext), dtype=np.uint8)
    mask_top[:offset_y, :] = 255
    mask_top = cv2.bitwise_and(mask_top, base_mask)
    avg_top = cv2.mean(cropped_exterior, mask=mask_top)[:3]
    region_averages.append(avg_top)
    
    # Region 1: Bottom stripe (full width)
    mask_bottom = np.zeros((h_ext, w_ext), dtype=np.uint8)
    mask_bottom[offset_y + h_int:, :] = 255
    mask_bottom = cv2.bitwise_and(mask_bottom, base_mask)
    avg_bottom = cv2.mean(cropped_exterior, mask=mask_bottom)[:3]
    region_averages.append(avg_bottom)
    
    # Region 2: Left stripe (full height)
    mask_left = np.zeros((h_ext, w_ext), dtype=np.uint8)
    mask_left[:, :offset_x] = 255
    mask_left = cv2.bitwise_and(mask_left, base_mask)
    avg_left = cv2.mean(cropped_exterior, mask=mask_left)[:3]
    region_averages.append(avg_left)
    
    # Region 3: Right stripe (full height)
    mask_right = np.zeros((h_ext, w_ext), dtype=np.uint8)
    mask_right[:, offset_x + w_int:] = 255
    mask_right = cv2.bitwise_and(mask_right, base_mask)
    avg_right = cv2.mean(cropped_exterior, mask=mask_right)[:3]
    region_averages.append(avg_right)
    
    # Calculate midpoints for corner regions
    mid_x_left = offset_x // 2  # Middle of left stripe
    mid_x_right = offset_x + w_int + (w_ext - offset_x - w_int) // 2  # Middle of right stripe
    mid_y_top = offset_y // 2  # Middle of top stripe
    mid_y_bottom = offset_y + h_int + (h_ext - offset_y - h_int) // 2  # Middle of bottom stripe
    
    # Region 4: Top-left corner (right half of top-left + upper half of left stripe)
    mask_top_left = np.zeros((h_ext, w_ext), dtype=np.uint8)
    # Right half of top stripe on left side
    mask_top_left[:offset_y, mid_x_left:offset_x] = 255
    # Upper half of left stripe
    mask_top_left[:mid_y_top, :offset_x] = 255
    mask_top_left = cv2.bitwise_and(mask_top_left, base_mask)
    avg_top_left = cv2.mean(cropped_exterior, mask=mask_top_left)[:3]
    region_averages.append(avg_top_left)
    
    # Region 5: Top-right corner (left half of top-right + upper half of right stripe)
    mask_top_right = np.zeros((h_ext, w_ext), dtype=np.uint8)
    # Left half of top stripe on right side
    mask_top_right[:offset_y, offset_x + w_int:mid_x_right] = 255
    # Upper half of right stripe
    mask_top_right[:mid_y_top, offset_x + w_int:] = 255
    mask_top_right = cv2.bitwise_and(mask_top_right, base_mask)
    avg_top_right = cv2.mean(cropped_exterior, mask=mask_top_right)[:3]
    region_averages.append(avg_top_right)
    
    # Region 6: Bottom-left corner (right half of bottom-left + lower half of left stripe)
    mask_bottom_left = np.zeros((h_ext, w_ext), dtype=np.uint8)
    # Right half of bottom stripe on left side
    mask_bottom_left[offset_y + h_int:, mid_x_left:offset_x] = 255
    # Lower half of left stripe
    mask_bottom_left[mid_y_bottom:, :offset_x] = 255
    mask_bottom_left = cv2.bitwise_and(mask_bottom_left, base_mask)
    avg_bottom_left = cv2.mean(cropped_exterior, mask=mask_bottom_left)[:3]
    region_averages.append(avg_bottom_left)
    
    # Region 7: Bottom-right corner (left half of bottom-right + lower half of right stripe)
    mask_bottom_right = np.zeros((h_ext, w_ext), dtype=np.uint8)
    # Left half of bottom stripe on right side
    mask_bottom_right[offset_y + h_int:, offset_x + w_int:mid_x_right] = 255
    # Lower half of right stripe
    mask_bottom_right[mid_y_bottom:, offset_x + w_int:] = 255
    mask_bottom_right = cv2.bitwise_and(mask_bottom_right, base_mask)
    avg_bottom_right = cv2.mean(cropped_exterior, mask=mask_bottom_right)[:3]
    region_averages.append(avg_bottom_right)
    
    return np.array(region_averages)
