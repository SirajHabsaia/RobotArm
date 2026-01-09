import cv2

def get_aruco_detector():
    """
    Creates and returns a configured ArUco detector with optimized parameters.
    
    Returns:
        cv2.aruco.ArucoDetector: Configured detector instance
    """
    # Using a 4x4 dictionary (you can adjust depending on your markers)
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters()

    # Adjust parameters for more sensitive detection
    parameters.adaptiveThreshConstant = 7  # Lower = more sensitive (default: 7)
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
