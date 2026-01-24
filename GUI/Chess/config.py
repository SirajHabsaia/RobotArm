import cv2

def get_aruco_detector():
    """
    Returns: cv2.aruco.ArucoDetector
    """
    # Using a 4x4 dictionary (you can adjust depending on your markers)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()

    # Adjust parameters for more sensitive detection
    parameters.adaptiveThreshConstant = 5  # Lower = more sensitive (default: 7)
    parameters.adaptiveThreshWinSizeMin = 3  # Minimum window size
    parameters.adaptiveThreshWinSizeMax = 23  # Maximum window size
    parameters.adaptiveThreshWinSizeStep = 1  # Step size

    # Corner refinement for better accuracy
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    parameters.cornerRefinementWinSize = 5
    parameters.cornerRefinementMaxIterations = 30
    parameters.cornerRefinementMinAccuracy = 0.1

    # Detection thresholds - lower values = more permissive
    parameters.minMarkerPerimeterRate = 0.03  # Min marker size (default: 0.03)
    parameters.maxMarkerPerimeterRate = 4.0   # Max marker size (default: 4.0)
    parameters.polygonalApproxAccuracyRate = 0.05  # Lower = more permissive (default: 0.03)
    parameters.minCornerDistanceRate = 0.05  # Min distance between corners (default: 0.05)
    parameters.minDistanceToBorder = 3  # Min distance from image border (default: 3)

    # Error correction
    parameters.errorCorrectionRate = 0.6  # Higher = more error correction (default: 0.6)

    # Create and return detector
    return cv2.aruco.ArucoDetector(aruco_dict, parameters)

class BoardAnalyzerConfig:
    """Configuration for BoardAnalyzer with all tunable parameters."""
    
    # Model settings
    model_path: str = "model.pth"
    device: str = "cpu"
    
    # Model class mappings (index -> label)
    class_names = ["black", "empty", "white"]  # Adjust based on your model's output
    
    # ArUco detection settings
    aruco_pts_movement_threshold: float = 3.0  # Minimum pixel movement to update corners
    
    # Square extraction settings
    square_scale: float = 0.9  # Scale factor for extracting square images
    
    # Hand detection settings
    hand_contour_threshold: float = 15.0  # Minimum contour density
    hand_canny_low: int = 75  # Canny edge detection lower threshold
    hand_canny_high: int = 120  # Canny edge detection higher threshold
    hand_detection_outer_margin: float = 0.1  # Outer margin as fraction of big_cropped size (e.g., 0.1 = 10%)
    hand_detection_stripe_usage: float = 0.7  # Fraction of stripe to use (from outer edge inward, e.g., 0.9 = use outer 90%)
    hand_detection_cooldown_frames: int = 4  # Number of frames to wait after hand is no longer detected before analyzing board
    
    # Stream input settings
    mode: str = "ip_camera"  # Options: "camera", "video", "ip_camera"
    video_path: str = "video.mp4"
    video_input_speed: int = 30  # frames per second
    camera_index: int = 0  # Default camera index
    camera_ip: str = "http://100.97.178.37:8080//video"  # IP camera URL
    
    # Display settings
    display_confidence_decimals: int = 2  # Number of decimal places for confidence
    display_font_scale: float = 0.5
    display_font_thickness: int = 1
    display_text_color: tuple = (0, 0, 255)  # BGR format