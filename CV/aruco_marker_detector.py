import cv2
import numpy as np
from aruco_config import get_aruco_detector


def main():
    """
    Main function to detect ArUco markers from video input and display their centers.
    """
    # Get the configured ArUco detector
    detector = get_aruco_detector()
    
    # Open video capture (0 for default webcam, or specify video file path)
    cap = cv2.VideoCapture("video.mp4")
    
    if not cap.isOpened():
        print("Error: Could not open video capture")
        return
    
    print("Press 'q' to quit")
    
    while True:
        # Read frame from video
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Could not read frame")
            break
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect ArUco markers
        corners, ids, rejected = detector.detectMarkers(gray)
        
        # If markers are detected
        if ids is not None and len(ids) > 0:
            for i, corner in enumerate(corners):
                # Calculate center of the marker
                corner_points = corner[0]
                center_x = int(np.mean(corner_points[:, 0]))
                center_y = int(np.mean(corner_points[:, 1]))
                
                # Draw a dot at the center
                cv2.circle(frame, (center_x, center_y), 8, (0, 0, 255), -1)
                
                # Optional: Draw marker ID near the center
                marker_id = ids[i][0]
                cv2.putText(frame, f"ID: {marker_id}", 
                           (center_x + 10, center_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Optional: Draw marker outline
                cv2.polylines(frame, [corner_points.astype(int)], True, (0, 255, 0), 2)
        
        # Display marker count
        marker_count = len(ids) if ids is not None else 0
        cv2.putText(frame, f"Markers detected: {marker_count}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow('ArUco Marker Detection', frame)
        
        # Break loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
