import sys
import cv2
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
import chess
import chess.svg
from aruco import BoardDetector
from chess_board_widget import ChessBoardWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chess Board Detection")
        self.setGeometry(300, 30, 900, 800)
        
        # Initialize board detector
        self.detector = BoardDetector(
            #video_path="http://10.49.56.193:8080/video"
        )
        
        # Initialize chess board with starting position
        self.chess_board = chess.Board()
        
        # Central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left side: Camera views
        left_layout = QVBoxLayout()
        
        # Hand detection region display
        self.hand_detection_label = QLabel("Hand Detection Region")
        self.hand_detection_label.setAlignment(Qt.AlignCenter)
        self.hand_detection_label.setMinimumSize(400, 400)
        self.hand_detection_label.setStyleSheet("border: 2px solid gray;")
        left_layout.addWidget(self.hand_detection_label)
        
        # Overall confidence display
        self.overall_label = QLabel("Overall Confidence")
        self.overall_label.setAlignment(Qt.AlignCenter)
        self.overall_label.setMinimumSize(400, 400)
        self.overall_label.setStyleSheet("border: 2px solid gray;")
        left_layout.addWidget(self.overall_label)
        
        main_layout.addLayout(left_layout)
        
        # Right side: Virtual chess board
        self.chess_widget = ChessBoardWidget(self.chess_board)
        self.chess_widget.setMinimumSize(600, 600)
        main_layout.addWidget(self.chess_widget)
        
        # Timer for updating frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)
        
        # Previous board state for move detection
        self.previous_board_state = None
        
    def update_frame(self):
        """Update all displays with new frame data"""
        # Process next frame
        result = self.detector.process_frame()
        
        if result is None:
            return
        
        hand_detection_img = result.get('hand_detection_display')
        overall_display_img = result.get('overall_display')
        board_state = result.get('board_state')
        
        # Update hand detection display
        if hand_detection_img is not None:
            self.display_image(hand_detection_img, self.hand_detection_label)
        
        # Update overall confidence display
        if overall_display_img is not None:
            self.display_image(overall_display_img, self.overall_label)
        
        # Update chess board if board state changed
        if board_state is not None and self.detector.is_stable():
            self.update_chess_board(board_state)
    
    def display_image(self, cv_img, label):
        """Convert OpenCV image to QPixmap and display in label"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        # Scale to fit label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
    
    def update_chess_board(self, board_state):
        """Update virtual chess board based on detected board state"""
        
        if self.previous_board_state is None:
            # First detection - assume starting position
            print("\n--- First Board State Detected ---")
            print("Board state:")
            for j in range(8):
                row = [str(board_state[i, j]) if board_state[i, j] is not None else '.' for i in range(8)]
                print(f"Rank {8-j}: {' '.join(row)}")
            self.previous_board_state = board_state.copy()
            return
        
        # Check if anything changed
        if np.array_equal(board_state, self.previous_board_state):
            return
        
        print("\n--- Board State CHANGED ---")
        print("Previous board state:")
        for j in range(8):
            row = [str(self.previous_board_state[i, j]) if self.previous_board_state[i, j] is not None else '.' for i in range(8)]
            print(f"Rank {8-j}: {' '.join(row)}")
        print("Current board state:")
        for j in range(8):
            row = [str(board_state[i, j]) if board_state[i, j] is not None else '.' for i in range(8)]
            print(f"Rank {8-j}: {' '.join(row)}")
        
        # Detect move by comparing previous and current state
        move = self.detect_move(self.previous_board_state, board_state)
        
        if move is not None:
            print(f"Move detected: {move}")
            try:
                # Try to make the move on the chess board
                if move in self.chess_board.legal_moves:
                    self.chess_board.push(move)
                    self.chess_widget.update_board(self.chess_board)
                    print(f"✓ Move applied successfully: {move}")
                else:
                    print(f"✗ Illegal move: {move}")
                    print(f"Legal moves: {list(self.chess_board.legal_moves)}")
            except Exception as e:
                print(f"✗ Error applying move: {e}")
        else:
            print("Could not determine move from board state changes")
        
        self.previous_board_state = board_state.copy()
    
    def detect_move(self, prev_state, curr_state):
        """
        Detect chess move from board state changes.
        Handles: normal moves, captures, castling, en passant
        """
        # Find differences between states
        from_square = None
        to_square = None
        changes = []
        disappeared_squares = []  # Squares where pieces disappeared
        appeared_squares = []      # Squares where pieces appeared or changed
        
        for i in range(8):
            for j in range(8):
                if prev_state[i, j] != curr_state[i, j]:
                    square = self.matrix_to_square(i, j)
                    square_name = chess.square_name(square)
                    
                    # Piece disappeared (became empty)
                    if prev_state[i, j] is not None and curr_state[i, j] is None:
                        disappeared_squares.append((square, prev_state[i, j]))
                        changes.append(f"{square_name}: {prev_state[i, j]} -> empty")
                    
                    # Piece appeared on empty square
                    elif prev_state[i, j] is None and curr_state[i, j] is not None:
                        appeared_squares.append((square, curr_state[i, j]))
                        changes.append(f"{square_name}: empty -> {curr_state[i, j]}")
                    
                    # Piece changed color (capture)
                    else:
                        appeared_squares.append((square, curr_state[i, j]))
                        changes.append(f"{square_name}: {prev_state[i, j]} -> {curr_state[i, j]}")
        
        print(f"Detected changes: {changes}")
        
        # Detect move type
        # Normal move or capture: 1 piece disappeared, 1 piece appeared
        if len(disappeared_squares) == 1 and len(appeared_squares) == 1:
            from_square = disappeared_squares[0][0]
            to_square = appeared_squares[0][0]
            from_piece = disappeared_squares[0][1]
            to_piece = appeared_squares[0][1]
            
            # Verify the piece color matches
            if from_piece == to_piece:
                print(f"From square: {chess.square_name(from_square)}")
                print(f"To square: {chess.square_name(to_square)}")
                
                try:
                    move = chess.Move(from_square, to_square)
                    return move
                except Exception as e:
                    print(f"Error creating move: {e}")
                    return None
        
        # Castling: 2 pieces disappeared, 2 pieces appeared (king and rook move)
        elif len(disappeared_squares) == 2 and len(appeared_squares) == 2:
            # Find the king move (king moves 2 squares)
            for from_sq, from_piece in disappeared_squares:
                for to_sq, to_piece in appeared_squares:
                    if from_piece == to_piece:
                        from_file = chess.square_file(from_sq)
                        to_file = chess.square_file(to_sq)
                        
                        # King moves 2 squares in castling
                        if abs(to_file - from_file) == 2:
                            print(f"Castling detected: {chess.square_name(from_sq)} -> {chess.square_name(to_sq)}")
                            try:
                                move = chess.Move(from_sq, to_sq)
                                return move
                            except Exception as e:
                                print(f"Error creating castling move: {e}")
                                return None
        
        print(f"Could not determine move: {len(disappeared_squares)} disappeared, {len(appeared_squares)} appeared")
        return None
    
    def matrix_to_square(self, i, j):
        """
        Convert matrix indices (i, j) to chess square index.
        Assuming matrix[0,0] is a8 (top-left from white's perspective)
        """
        # i = file (0-7 for a-h)
        # j = rank (0-7 for 8-1)
        rank = 7 - j  # Flip rank
        file = i
        return chess.square(file, rank)
    
    def closeEvent(self, event):
        """Clean up when window is closed"""
        self.detector.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
