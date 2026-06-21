from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, QRect, QPoint, QSize, QPointF
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QPolygonF
from pathlib import Path
import math


class ChessWidget(QWidget):
    """Non-interactive chess board widget with piece placement - controlled programmatically only."""
    
    # Standard chess starting position (FEN notation as reference)
    # Rows are from rank 8 to rank 1, columns are from file a to h
    INITIAL_BOARD = [
        ['br', 'bn', 'bb', 'bq', 'bk', 'bb', 'bn', 'br'],  # Rank 8
        ['bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp', 'bp'],  # Rank 7
        ['', '', '', '', '', '', '', ''],                    # Rank 6
        ['', '', '', '', '', '', '', ''],                    # Rank 5
        ['', '', '', '', '', '', '', ''],                    # Rank 4
        ['', '', '', '', '', '', '', ''],                    # Rank 3
        ['wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp', 'wp'],  # Rank 2
        ['wr', 'wn', 'wb', 'wq', 'wk', 'wb', 'wn', 'wr'],  # Rank 1
    ]
    
    # Piece code mapping: w=white, b=black, p=pawn, r=rook, n=knight, b=bishop, q=queen, k=king
    PIECE_NAMES = {
        'wp': 'white-pawn',
        'wr': 'white-rook',
        'wn': 'white-knight',
        'wb': 'white-bishop',
        'wq': 'white-queen',
        'wk': 'white-king',
        'bp': 'black-pawn',
        'br': 'black-rook',
        'bn': 'black-knight',
        'bb': 'black-bishop',
        'bq': 'black-queen',
        'bk': 'black-king',
    }
    
    def __init__(self, parent=None, orientation='white', white_color=QColor(240, 217, 181), black_color=QColor(181, 136, 99)):
        """
        Initialize chess board widget.
        
        Args:
            parent: Parent widget
            orientation: 'white' (white pieces at bottom) or 'black' (black pieces at bottom)
            white_color: QColor for white squares
            black_color: QColor for black squares
        """
        super().__init__(parent)
        
        self.orientation = orientation  # 'white' or 'black'
        self.white_color = white_color
        self.black_color = black_color
        
        # Board state: 8x8 matrix where '' is empty, 'wp' is white pawn, etc.
        self.board = [row[:] for row in self.INITIAL_BOARD]  # Deep copy

        # Squares (row, col) to highlight with a translucent red overlay,
        # e.g. to mark the difference of an illegal/unverified board state.
        self.highlighted_squares = set()

        # Arrows marking the last played move(s): list of (from_row, from_col,
        # to_row, to_col). Castling produces two arrows (king and rook).
        self.move_arrows = []

        # Arrows for a move the robot has performed but that is still being
        # verified by the camera. Drawn more transparently to read as tentative.
        self.pending_move_arrows = []
        
        # Load piece images
        self.piece_images = {}  # Original high-res images
        self.scaled_piece_cache = {}  # Cache for scaled images at current size
        self.cached_square_size = 0  # Track when to regenerate cache
        self._load_piece_images()
        
        # Set size policy to maintain aspect ratio
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Set minimum and initial size
        self.setMinimumSize(400, 400)
        self.setMaximumSize(10000, 10000)
    
    def _load_piece_images(self):
        """Load all piece images from the pieces folder."""
        pieces_dir = Path(__file__).parent / "pieces"
        
        for piece_code, piece_name in self.PIECE_NAMES.items():
            image_path = pieces_dir / f"{piece_name}.png"
            if image_path.exists():
                self.piece_images[piece_code] = QPixmap(str(image_path))
            else:
                print(f"Warning: Missing piece image: {image_path}")
    
    def sizeHint(self):
        """Suggest a default size for the widget."""
        return QSize(600, 600)
    
    def hasHeightForWidth(self):
        """Indicate that height depends on width to maintain aspect ratio."""
        return True
    
    def heightForWidth(self, width):
        """Return height that maintains 1:1 aspect ratio."""
        return width
    
    def resizeEvent(self, event):
        """Handle resize to maintain square aspect ratio."""
        # Don't force resize, just accept what the layout gives us
        super().resizeEvent(event)
        # The board will draw centered using _get_board_offset()
    
    def _get_square_size(self):
        """Calculate square size based on widget size."""
        width = self.width()
        height = self.height()
        size = min(width, height)
        return size // 8
        return size // 8
    
    def _get_board_offset(self):
        """Calculate offset to center the board in the widget."""
        square_size = self._get_square_size()
        board_size = square_size * 8
        offset_x = (self.width() - board_size) // 2
        offset_y = (self.height() - board_size) // 2
        return offset_x, offset_y
    
    def _square_to_coords(self, row, col):
        """Convert board coordinates (row, col) to pixel coordinates (x, y)."""
        square_size = self._get_square_size()
        offset_x, offset_y = self._get_board_offset()
        
        # Adjust for orientation
        if self.orientation == 'white':
            # White at bottom: row 0 (rank 8) at top
            display_row = row
            display_col = col
        else:
            # Black at bottom: flip board
            display_row = 7 - row
            display_col = 7 - col
        
        x = offset_x + display_col * square_size
        y = offset_y + display_row * square_size
        
        return x, y
    
    def _coords_to_square(self, x, y):
        """Convert pixel coordinates (x, y) to board coordinates (row, col)."""
        square_size = self._get_square_size()
        offset_x, offset_y = self._get_board_offset()
        
        # Check if click is within board bounds
        board_size = square_size * 8
        if x < offset_x or x >= offset_x + board_size or y < offset_y or y >= offset_y + board_size:
            return None
        
        display_col = (x - offset_x) // square_size
        display_row = (y - offset_y) // square_size
        
        # Adjust for orientation
        if self.orientation == 'white':
            row = display_row
            col = display_col
        else:
            row = 7 - display_row
            col = 7 - display_col
        
        return (row, col)
    
    def paintEvent(self, event):
        """Draw the chess board and pieces."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        square_size = self._get_square_size()
        offset_x, offset_y = self._get_board_offset()
        
        # Regenerate cache if square size changed
        if self.cached_square_size != square_size:
            self._regenerate_scaled_cache(square_size)
        
        # Draw squares
        for row in range(8):
            for col in range(8):
                x, y = self._square_to_coords(row, col)
                
                # Determine square color (alternating pattern)
                is_light = (row + col) % 2 == 0
                color = self.white_color if is_light else self.black_color
                
                painter.fillRect(x, y, square_size, square_size, color)
        
        # Draw border
        board_size = square_size * 8
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawRect(offset_x, offset_y, board_size, board_size)
        
        # Draw pieces using cached scaled images
        for row in range(8):
            for col in range(8):
                piece = self.board[row][col]
                if piece:
                    self._draw_piece(painter, piece, row, col, square_size)

        # Draw the pending (being-verified) move arrows first, then the solid
        # confirmed move arrows on top.
        if self.pending_move_arrows:
            self._draw_arrows(painter, square_size, self.pending_move_arrows,
                              QColor(255, 140, 0, 110))  # transparent orange
        if self.move_arrows:
            self._draw_arrows(painter, square_size, self.move_arrows,
                              QColor(30, 120, 220, 200))  # semi-transparent blue

        # Draw translucent red overlay on highlighted squares (on top of pieces)
        if self.highlighted_squares:
            highlight_color = QColor(255, 0, 0, 110)  # semi-transparent red
            for (row, col) in self.highlighted_squares:
                if 0 <= row < 8 and 0 <= col < 8:
                    x, y = self._square_to_coords(row, col)
                    painter.fillRect(x, y, square_size, square_size, highlight_color)
    
    def _draw_piece(self, painter, piece_code, row, col, square_size):
        """Draw a piece at the specified board position using cached scaled image."""
        scaled_pixmap = self.scaled_piece_cache.get(piece_code)
        if scaled_pixmap:
            x, y = self._square_to_coords(row, col)
            painter.drawPixmap(x, y, scaled_pixmap)
    
    def _regenerate_scaled_cache(self, square_size):
        """Regenerate scaled piece images cache for current square size."""
        self.scaled_piece_cache.clear()
        for piece_code, pixmap in self.piece_images.items():
            # Use high-quality scaling
            scaled = pixmap.scaled(
                square_size, 
                square_size, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.scaled_piece_cache[piece_code] = scaled
        self.cached_square_size = square_size
    
    def reset_board(self):
        """Reset board to initial position."""
        self.board = [row[:] for row in self.INITIAL_BOARD]
        self.update()
    
    def set_orientation(self, orientation):
        """Change board orientation ('white' or 'black')."""
        if orientation in ['white', 'black']:
            self.orientation = orientation
            self.update()
    
    def get_board_state(self):
        """Get current board state as 8x8 matrix."""
        return [row[:] for row in self.board]
    
    def set_board_state(self, board):
        """Set board state from 8x8 matrix."""
        if len(board) == 8 and all(len(row) == 8 for row in board):
            self.board = [row[:] for row in board]
            self.update()

    def set_highlighted_squares(self, squares):
        """Highlight the given squares with a translucent red overlay.

        Args:
            squares: iterable of (row, col) tuples (row 0 = rank 8, col 0 = file a)
        """
        new_squares = set(squares)
        if new_squares != self.highlighted_squares:
            self.highlighted_squares = new_squares
            self.update()

    def clear_highlights(self):
        """Remove any highlight overlay from the board."""
        if self.highlighted_squares:
            self.highlighted_squares = set()
            self.update()

    def set_move_arrows(self, arrows):
        """Show arrows for the last played move.

        Args:
            arrows: iterable of (from_row, from_col, to_row, to_col) tuples
                    (row 0 = rank 8, col 0 = file a). Castling passes two arrows.
        """
        self.move_arrows = list(arrows)
        self.update()

    def clear_move_arrows(self):
        """Remove the move arrows from the board."""
        if self.move_arrows:
            self.move_arrows = []
            self.update()

    def set_pending_move_arrows(self, arrows):
        """Show tentative arrows for a robot move that is being verified.

        Args:
            arrows: iterable of (from_row, from_col, to_row, to_col) tuples.
                    Castling passes two arrows.
        """
        self.pending_move_arrows = list(arrows)
        self.update()

    def clear_pending_move_arrows(self):
        """Remove the pending (being-verified) move arrows from the board."""
        if self.pending_move_arrows:
            self.pending_move_arrows = []
            self.update()

    def _draw_arrows(self, painter, square_size, arrows, color):
        """Draw arrows (square centre to square centre) in the given colour."""
        painter.save()
        pen = QPen(color, max(3, square_size // 10))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(color)

        half = square_size / 2.0
        head = square_size * 0.34  # arrowhead length
        for (from_row, from_col, to_row, to_col) in arrows:
            fx, fy = self._square_to_coords(from_row, from_col)
            tx, ty = self._square_to_coords(to_row, to_col)
            x1, y1 = fx + half, fy + half
            x2, y2 = tx + half, ty + half

            angle = math.atan2(y2 - y1, x2 - x1)

            # End the shaft just short of the tip so the head isn't doubled up
            shaft_x = x2 - head * 0.55 * math.cos(angle)
            shaft_y = y2 - head * 0.55 * math.sin(angle)
            painter.drawLine(QPointF(x1, y1), QPointF(shaft_x, shaft_y))

            # Arrowhead triangle at the destination
            left = QPointF(x2 - head * math.cos(angle - math.pi / 6),
                           y2 - head * math.sin(angle - math.pi / 6))
            right = QPointF(x2 - head * math.cos(angle + math.pi / 6),
                            y2 - head * math.sin(angle + math.pi / 6))
            painter.drawPolygon(QPolygonF([QPointF(x2, y2), left, right]))

        painter.restore()
