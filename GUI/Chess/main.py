"""
Standalone runner for chess board detection system.

Displays two windows:
1. "Big Cropped - Hand Detection": Shows the outer board area with contours (stripe only)
2. "Small Cropped - Predictions": Shows the inner board with piece predictions

Press 'q' to quit.
"""

import cv2
import numpy as np
from board_detector import BoardDetector
from config import BoardAnalyzerConfig


def main():
    """Main function for standalone execution."""
    
    # Load configuration
    config = BoardAnalyzerConfig()
    
    print("Chess Board Detection System")
    print("=" * 50)
    print(f"Mode: {config.mode}")
    if config.mode == "video":
        print(f"Video path: {config.video_path}")
        print(f"Processing speed: {config.video_input_speed} FPS")
    elif config.mode == "camera":
        print(f"Camera index: {config.camera_index}")
    elif config.mode == "ip_camera":
        print(f"IP camera: {config.camera_ip}")
    print(f"Hand detection threshold: {config.hand_contour_threshold}")
    print("=" * 50)
    print("\nInitializing detector...")
    
    # Initialize detector with performance metrics enabled
    try:
        detector = BoardDetector(config, performance_metrics=True)
    except Exception as e:
        print(f"Error initializing detector: {e}")
        return
    
    print("Detector initialized. Waiting for ArUco markers...")
    print("Press 'q' to quit.")
    
    # Create windows
    cv2.namedWindow("Full Region - Hand Detection", cv2.WINDOW_NORMAL)
    cv2.namedWindow("Small Cropped - Predictions", cv2.WINDOW_NORMAL)
    
    # Resize windows for better viewing (display size, not processing size)
    display_size = 800
    cv2.resizeWindow("Full Region - Hand Detection", display_size, display_size)
    cv2.resizeWindow("Small Cropped - Predictions", display_size, display_size)
    
    # Last valid small cropped image (for when hand is detected)
    last_small_cropped = None
    
    # Statistics
    frame_count = 0
    processed_count = 0
    skipped_count = 0
    
    try:
        for result in detector.process_stream():
            frame_count += 1
            
            # Get display images
            display_big = result['display_big_cropped']
            display_small = result['display_small_cropped']
            hand_detected = result['hand_detected']
            skipped = result['skipped']
            contour_density = result['contour_density']
            
            if skipped:
                skipped_count += 1
            else:
                processed_count += 1
            
            # Resize for display (but keep original for processing)
            big_height, big_width = display_big.shape[:2]
            small_height = display_small.shape[0] if display_small is not None else 0
            
            # Add status text to big cropped image
            status_text = "HAND DETECTED - SKIPPING" if hand_detected else "Processing"
            font_scale_big = big_height / 1000.0  # Scale based on image size
            cv2.putText(display_big, status_text, (10, int(30 * font_scale_big)), 
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale_big, (0, 0, 255) if hand_detected else (0, 255, 0), 
                       max(1, int(2 * font_scale_big)), cv2.LINE_AA)
            
            # Add contour density display
            density_text = f"Contour Density: {contour_density:.1f}"
            cv2.putText(display_big, density_text, (10, int(70 * font_scale_big)), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8 * font_scale_big, (255, 255, 0), 
                       max(1, int(2 * font_scale_big)), cv2.LINE_AA)
            
            # Add frame counter
            counter_text = f"Frame: {frame_count} | Processed: {processed_count} | Skipped: {skipped_count}"
            cv2.putText(display_big, counter_text, (10, big_height - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6 * font_scale_big, (255, 255, 255), 
                       max(1, int(1 * font_scale_big)), cv2.LINE_AA)
            
            # Resize big cropped for display
            display_big_resized = cv2.resize(display_big, (display_size, display_size))
            cv2.imshow("Full Region - Hand Detection", display_big_resized)
            
            # Display small cropped (show last valid if hand detected)
            if display_small is not None:
                last_small_cropped = display_small
                display_small_resized = cv2.resize(display_small, (display_size, display_size))
                cv2.imshow("Small Cropped - Predictions", display_small_resized)
            elif last_small_cropped is not None:
                # Show last valid small cropped with "PAUSED" overlay
                paused_display = last_small_cropped.copy()
                
                # Add semi-transparent overlay
                overlay = paused_display.copy()
                h, w = paused_display.shape[:2]
                cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.3, paused_display, 0.7, 0, paused_display)
                
                # Add "PAUSED" text
                font_scale_paused = h / 800.0
                text_size = cv2.getTextSize("PAUSED", cv2.FONT_HERSHEY_SIMPLEX, 2.0 * font_scale_paused, int(4 * font_scale_paused))[0]
                text_x = (w - text_size[0]) // 2
                text_y = (h + text_size[1]) // 2
                cv2.putText(paused_display, "PAUSED", (text_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 2.0 * font_scale_paused, (0, 0, 255), 
                           max(1, int(4 * font_scale_paused)), cv2.LINE_AA)
                
                paused_display_resized = cv2.resize(paused_display, (display_size, display_size))
                cv2.imshow("Small Cropped - Predictions", paused_display_resized)
            
            # Check for quit command
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\nQuitting...")
                break
    
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    
    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        detector.release()
        cv2.destroyAllWindows()
        print("Done.")
        
        # Print final statistics
        print("\nStatistics:")
        print(f"Total frames: {frame_count}")
        print(f"Processed: {processed_count}")
        print(f"Skipped (hand detected): {skipped_count}")


if __name__ == "__main__":
    main()
