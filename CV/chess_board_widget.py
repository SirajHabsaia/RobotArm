from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QFont
import chess


class ChessBoardWidget(QWidget):
    """Widget to display a virtual chess board"""
    
    def __init__(self, board=None):
        super().__init__()
        self.board = board if board is not None else chess.Board()
        self.square_size = 60
        self.setMinimumSize(self.square_size * 8, self.square_size * 8)
        
        # Colors
        self.light_square_color = QColor(240, 217, 181)
        self.dark_square_color = QColor(181, 136, 99)
        self.highlight_color = QColor(255, 255, 0, 100)
        
    def update_board(self, board):
        """Update the chess board state"""
        self.board = board
        self.update()
    
    def paintEvent(self, event):
        """Draw the chess board"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate actual square size based on widget size
        width = self.width()
        height = self.height()
        self.square_size = min(width, height) // 8
        
        # Draw squares
        for rank in range(8):
            for file in range(8):
                x = file * self.square_size
                y = rank * self.square_size
                
                # Determine square color
                is_light = (rank + file) % 2 == 0
                color = self.light_square_color if is_light else self.dark_square_color
                
                painter.fillRect(x, y, self.square_size, self.square_size, color)
        
        # Draw pieces
        font = QFont("Arial", int(self.square_size * 0.6))
        painter.setFont(font)
        
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece is not None:
                file = chess.square_file(square)
                rank = 7 - chess.square_rank(square)  # Flip rank for display
                
                x = file * self.square_size
                y = rank * self.square_size
                
                # Get piece symbol
                piece_symbol = self.get_piece_symbol(piece)
                
                # Set color
                if piece.color == chess.WHITE:
                    painter.setPen(QPen(QColor(255, 255, 255)))
                else:
                    painter.setPen(QPen(QColor(0, 0, 0)))
                
                # Draw piece
                rect = QRectF(x, y, self.square_size, self.square_size)
                painter.drawText(rect, Qt.AlignCenter, piece_symbol)
        
        # Draw coordinates
        coord_font = QFont("Arial", 10)
        painter.setFont(coord_font)
        painter.setPen(QPen(QColor(100, 100, 100)))
        
        # Files (a-h)
        for file in range(8):
            letter = chr(ord('a') + file)
            x = file * self.square_size + self.square_size // 2
            y = 8 * self.square_size + 15
            painter.drawText(x - 5, y, letter)
        
        # Ranks (1-8)
        for rank in range(8):
            number = str(8 - rank)
            x = -15
            y = rank * self.square_size + self.square_size // 2
            painter.drawText(x, y + 5, number)
    
    def get_piece_symbol(self, piece):
        """Get Unicode symbol for chess piece"""
        symbols = {
            chess.PAWN: ('♙', '♟'),
            chess.KNIGHT: ('♘', '♞'),
            chess.BISHOP: ('♗', '♝'),
            chess.ROOK: ('♖', '♜'),
            chess.QUEEN: ('♕', '♛'),
            chess.KING: ('♔', '♚'),
        }
        
        white_symbol, black_symbol = symbols[piece.piece_type]
        return white_symbol if piece.color == chess.WHITE else black_symbol
