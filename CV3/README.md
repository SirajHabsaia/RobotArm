# Chess Board Detection System (CV3)

A computer vision system for detecting and classifying chess pieces on a board using ArUco markers and CNN-based classification.

## Features

- **ArUco Marker Detection**: Automatically detects the chess board using 4 ArUco markers at the corners
- **Hand Detection**: Uses Canny edge detection on the stripe between markers to detect hand movement
- **CNN-based Classification**: Classifies each square as empty, white piece, or black piece
- **Multiple Input Modes**: Supports video files, webcam, and IP camera
- **PySide6 Compatible**: Can be imported and integrated into GUI applications

## Architecture

### Files

- `config.py`: Configuration settings and ArUco detector initialization
- `board_detector.py`: Main detection logic with `BoardDetector` class
- `main.py`: Standalone runner with visualization
- `model.pth`: Pre-trained CNN model for piece classification

### Workflow

1. **ArUco Detection**: Detects 4 markers (IDs 0-3) at board corners
2. **Perspective Transform**: Creates two cropped images:
   - `big_cropped`: 1000×1000px (includes ArUco markers)
   - `small_cropped`: 800×800px (chess board only)
3. **Hand Detection**: Analyzes the 100px stripe between images using Canny edge detection
4. **Square Extraction**: If no hand detected, extracts 64 squares from the board
5. **Classification**: Runs CNN inference on each square
6. **Display**: Shows results with predictions and confidence scores

## Usage

### Standalone Mode

```bash
python main.py
```

This will open two windows:
- **Big Cropped - Hand Detection**: Shows contour detection in the stripe area
- **Small Cropped - Predictions**: Shows piece classifications with confidence

Press 'q' to quit.

### Integration Mode

```python
from board_detector import BoardDetector
from config import BoardAnalyzerConfig

# Configure
config = BoardAnalyzerConfig()
config.mode = "camera"  # or "video" or "ip_camera"
config.video_input_speed = 5  # FPS for video mode

# Initialize
detector = BoardDetector(config)

# Process stream
for result in detector.process_stream():
    if result['skipped']:
        # Hand detected, frame skipped
        continue
    
    board_state = result['board_state']  # 8x8 grid of (class, confidence)
    display_big = result['display_big_cropped']
    display_small = result['display_small_cropped']
    
    # Use board_state for your application
    for row in range(8):
        for col in range(8):
            class_label, confidence = board_state[row][col]
            # col=0 -> file 'a', row=7 -> rank '1'
            print(f"{chr(ord('a')+col)}{8-row}: {class_label} ({confidence:.2f})")
```

## Configuration

Edit `config.py` or override settings programmatically:

```python
config = BoardAnalyzerConfig()

# Model settings
config.model_path = "model.pth"
config.img_size = 100
config.device = "cpu"  # or "cuda"

# Square extraction
config.square_scale = 0.9  # 0.0-1.0, smaller = more margin

# Hand detection
config.hand_contour_threshold = 100.0  # Lower = more sensitive
config.hand_canny_low = 100
config.hand_canny_high = 200

# Stream input
config.mode = "video"  # "camera", "video", "ip_camera"
config.video_path = "video.mp4"
config.video_input_speed = 5  # FPS for video mode
config.camera_index = 0  # For camera mode
config.camera_ip = "http://192.168.1.100/video"  # For ip_camera mode

# Display
config.display_confidence_decimals = 2
config.display_text_color = (0, 255, 0)  # BGR
```

## ArUco Marker Layout

The system expects 4 ArUco markers (DICT_4X4_50) positioned as follows:

```
   0 ----------- 1
   |             |
   |   BOARD     |
   |             |
   3 ----------- 2
```

- **Marker 0**: Top-left corner
- **Marker 1**: Top-right corner  
- **Marker 2**: Bottom-right corner
- **Marker 3**: Bottom-left corner

## Board Coordinate System

After correct ArUco detection:
- **Bottom-left** of the board corresponds to square **a1**
- **Top-right** corresponds to square **h8**
- `board_state[row][col]` where:
  - `row=0` → rank 8, `row=7` → rank 1
  - `col=0` → file a, `col=7` → file h

## Stream Input Modes

### Video Mode
- Processes frames at controlled FPS (`video_input_speed`)
- Analyzes every frame sequentially
- Suitable for testing and debugging

### Camera/IP Camera Mode
- Always processes the latest frame
- Skips frames if falling behind
- Ensures real-time performance

## Hand Detection Logic

1. Extract stripe region (100px border between big and small cropped)
2. Apply Canny edge detection
3. Find contours in stripe
4. Calculate total contour length
5. If length > `hand_contour_threshold`, skip frame (hand detected)

**Note**: Contours are only detected in the stripe area, never on the board itself.

## Model Output

The CNN model outputs 3 classes:
- `0`: empty
- `1`: white piece
- `2`: black piece

The display shows:
- **E**: Empty square
- **W**: White piece
- **B**: Black piece

Each prediction includes a confidence score (0.00-1.00).

## Requirements

```
opencv-python
numpy
torch
torchvision
pillow
```

## Integration with PySide6

The `BoardDetector` class can be easily integrated into PySide6 applications:

```python
from PySide6.QtCore import QThread, Signal
from board_detector import BoardDetector
from config import BoardAnalyzerConfig

class DetectorThread(QThread):
    frame_ready = Signal(dict)
    
    def __init__(self, config):
        super().__init__()
        self.detector = BoardDetector(config)
        self.running = True
    
    def run(self):
        for result in self.detector.process_stream():
            if not self.running:
                break
            self.frame_ready.emit(result)
    
    def stop(self):
        self.running = False
        self.detector.release()
```

## Troubleshooting

### ArUco Markers Not Detected
- Ensure markers are printed clearly and visible
- Check lighting conditions
- Verify marker IDs are 0, 1, 2, 3
- Adjust ArUco detector parameters in `config.py`

### Hand Detection Too Sensitive
- Increase `hand_contour_threshold` in config
- Adjust `hand_canny_low` and `hand_canny_high` thresholds

### Poor Classification Accuracy
- Retrain the CNN model with more data
- Adjust `square_scale` to capture better square regions
- Check lighting conditions on the board

### Video/Camera Not Opening
- Verify file path or camera index
- Check camera permissions
- Ensure OpenCV is properly installed

## License

This project is part of the RobotArm workspace.
