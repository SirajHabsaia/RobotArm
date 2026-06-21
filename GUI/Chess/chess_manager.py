"""
Chess Manager - Handles chess game logic and board state validation.

This module bridges the board detector (which outputs B/E/W) and the chess widget
(which displays actual pieces). It validates moves using python-chess and maintains
the current game state.
"""

import chess
from typing import Optional, List, Tuple, Dict


class ChessManager:
    """
    Manages chess game state and validates detected board changes.
    
    Workflow:
    1. Maintains current board state with actual piece information
    2. Receives detector output (8x8 matrix of 'black'/'empty'/'white')
    3. Compares with current state to find what changed
    4. Validates the move with chess library
    5. Updates board state and widget if valid
    """
    
    # Mapping from chess.Piece to widget piece codes
    PIECE_TO_CODE = {
        (chess.PAWN, chess.WHITE): 'wp',
        (chess.KNIGHT, chess.WHITE): 'wn',
        (chess.BISHOP, chess.WHITE): 'wb',
        (chess.ROOK, chess.WHITE): 'wr',
        (chess.QUEEN, chess.WHITE): 'wq',
        (chess.KING, chess.WHITE): 'wk',
        (chess.PAWN, chess.BLACK): 'bp',
        (chess.KNIGHT, chess.BLACK): 'bn',
        (chess.BISHOP, chess.BLACK): 'bb',
        (chess.ROOK, chess.BLACK): 'br',
        (chess.QUEEN, chess.BLACK): 'bq',
        (chess.KING, chess.BLACK): 'bk',
    }
    
    # Reverse mapping: widget code to (piece_type, color)
    CODE_TO_PIECE = {v: k for k, v in PIECE_TO_CODE.items()}
    
    def __init__(self, chess_widget):
        """
        Initialize chess manager.
        
        Args:
            chess_widget: ChessWidget instance to update with new states
        """
        self.chess_widget = chess_widget
        
        # Initialize chess board (python-chess)
        self.board = chess.Board()
        
        # Current board state as 8x8 widget matrix (matching ChessWidget format)
        # Rows: rank 8 to rank 1 (index 0 = rank 8, index 7 = rank 1)
        # Cols: file a to h (index 0 = file a, index 7 = file h)
        self.current_state = self._board_to_matrix()
        
        # Store previous detected state to avoid reprocessing same state
        self.previous_detected_state = None

        # Most recent detected color matrix (used to highlight invalid states)
        self.last_detected_colors = None

        # Most recently applied move (used to draw move arrows)
        self.last_move = None
        
        # Update widget to show initial position
        self.chess_widget.set_board_state(self.current_state)
    
    def _board_to_matrix(self) -> List[List[str]]:
        """
        Convert python-chess Board to widget matrix format.
        
        Returns:
            8x8 matrix where rows go from rank 8 to rank 1
        """
        matrix = []
        # Iterate from rank 8 down to rank 1
        for rank in range(7, -1, -1):  # 7, 6, 5, 4, 3, 2, 1, 0
            row = []
            for file in range(8):  # a-h (0-7)
                square = chess.square(file, rank)
                piece = self.board.piece_at(square)
                
                if piece is None:
                    row.append('')
                else:
                    piece_code = self.PIECE_TO_CODE.get((piece.piece_type, piece.color), '')
                    row.append(piece_code)
            matrix.append(row)
        
        return matrix
    
    def _matrix_to_fen(self, matrix: List[List[str]]) -> str:
        """
        Convert widget matrix to FEN position string (piece placement only).
        
        Args:
            matrix: 8x8 widget matrix (rank 8 to rank 1)
        
        Returns:
            FEN piece placement string (e.g., "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
        """
        fen_rows = []
        
        for row in matrix:
            fen_row = ""
            empty_count = 0
            
            for square in row:
                if square == '':
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    
                    # Convert piece code to FEN notation
                    piece_type, color = self.CODE_TO_PIECE.get(square, (None, None))
                    if piece_type is not None:
                        piece_symbol = chess.piece_symbol(piece_type)
                        if color == chess.WHITE:
                            fen_row += piece_symbol.upper()
                        else:
                            fen_row += piece_symbol.lower()
            
            if empty_count > 0:
                fen_row += str(empty_count)
            
            fen_rows.append(fen_row)
        
        return '/'.join(fen_rows)
    
    def _compare_states(self, old_state: List[List[str]], new_state: List[List[str]]) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """
        Compare two board states to find changed squares.
        
        Args:
            old_state: Previous board matrix
            new_state: New board matrix
        
        Returns:
            Tuple of (removed_squares, added_squares) where each is list of (row, col)
        """
        removed = []
        added = []
        
        for row in range(8):
            for col in range(8):
                old_piece = old_state[row][col]
                new_piece = new_state[row][col]
                
                if old_piece != new_piece:
                    if old_piece != '':
                        removed.append((row, col))
                    if new_piece != '':
                        added.append((row, col))
        
        return removed, added
    
    def _try_find_move(self, old_state: List[List[str]], new_state: List[List[str]]) -> Optional[chess.Move]:
        """
        Try to determine the chess move from state changes.
        
        Args:
            old_state: Previous board state
            new_state: New detected state
        
        Returns:
            chess.Move if a valid move can be determined, None otherwise
        """
        removed, added = self._compare_states(old_state, new_state)
        
        # Standard move: one piece removed, one added
        if len(removed) == 1 and len(added) == 1:
            from_row, from_col = removed[0]
            to_row, to_col = added[0]
            
            # Convert to chess square indices (remember: row 0 = rank 8, row 7 = rank 1)
            from_square = chess.square(from_col, 7 - from_row)
            to_square = chess.square(to_col, 7 - to_row)
            
            # Check if this move is legal
            move = chess.Move(from_square, to_square)
            
            # Check for promotion (if pawn reaches last rank)
            piece = self.board.piece_at(from_square)
            if piece and piece.piece_type == chess.PAWN:
                if (piece.color == chess.WHITE and to_row == 0) or (piece.color == chess.BLACK and to_row == 7):
                    # Assume queen promotion by default
                    move = chess.Move(from_square, to_square, promotion=chess.QUEEN)
            
            if move in self.board.legal_moves:
                return move
        
        # Capture: two pieces removed (captured piece + moving piece), one added
        elif len(removed) == 2 and len(added) == 1:
            to_row, to_col = added[0]
            to_square = chess.square(to_col, 7 - to_row)
            
            # One of the removed squares should have the moving piece
            for from_row, from_col in removed:
                from_square = chess.square(from_col, 7 - from_row)
                move = chess.Move(from_square, to_square)
                
                # Check for promotion on capture
                piece = self.board.piece_at(from_square)
                if piece and piece.piece_type == chess.PAWN:
                    if (piece.color == chess.WHITE and to_row == 0) or (piece.color == chess.BLACK and to_row == 7):
                        move = chess.Move(from_square, to_square, promotion=chess.QUEEN)
                
                if move in self.board.legal_moves:
                    return move
        
        # Castling: king moves 2 squares, rook moves to adjacent square
        elif len(removed) == 2 and len(added) == 2:
            # Try to find king move
            for from_row, from_col in removed:
                from_square = chess.square(from_col, 7 - from_row)
                piece = self.board.piece_at(from_square)
                
                if piece and piece.piece_type == chess.KING:
                    # Check all added squares for potential king destination
                    for to_row, to_col in added:
                        to_square = chess.square(to_col, 7 - to_row)
                        move = chess.Move(from_square, to_square)
                        
                        if move in self.board.legal_moves:
                            return move
        
        return None
    
    def process_detected_state(self, detected_state: List[List[Tuple[str, float]]]) -> str:
        """
        Process a detected board state from the board detector.

        Args:
            detected_state: 8x8 matrix of (class_label, confidence) tuples
                           where class_label is 'black', 'empty', or 'white'

        Returns:
            A status string describing the detection:
                - 'moved'     : a legal move was recognized and applied
                - 'invalid'   : a new placement that matches no legal move (illegal)
                - 'nochange'  : the board matches the current expected position
                                (e.g. the starting position, or pieces put back)
                - 'unchanged' : identical to the previously processed frame
        """
        # Convert detected state to color-only matrix
        detected_colors = self._get_color_matrix(detected_state)
        self.last_detected_colors = detected_colors

        # Ignore frames identical to the previous detection
        if self.previous_detected_state is not None:
            if self._states_are_equal(self.previous_detected_state, detected_colors):
                return 'unchanged'

        # Store this state as the new previous state
        self.previous_detected_state = [row[:] for row in detected_colors]

        # If the detected board matches the current (expected) position, no move
        # was made (e.g. the starting position, or pieces put back where they were).
        if self._board_matches_colors(self.board, detected_colors):
            return 'nochange'

        # New state detected, try to find a legal move that explains it
        move = self._find_matching_move(detected_colors)

        if move is not None:
            # Valid move found!
            print(f"[ChessManager] ✓ Valid move: {move.uci()}")

            # Apply move to board
            self.board.push(move)
            self.last_move = move

            # Update current state
            self.current_state = self._board_to_matrix()

            # Update chess widget
            self.chess_widget.set_board_state(self.current_state)

            return 'moved'
        else:
            # A genuinely new placement that matches no legal move
            print(f"[ChessManager] ✗ Invalid board state detected")
            return 'invalid'
    
    def _get_color_matrix(self, detected_state: List[List[Tuple[str, float]]]) -> List[List[Optional[bool]]]:
        """
        Convert detected state to simple color matrix.
        
        Args:
            detected_state: 8x8 matrix of (class_label, confidence)
        
        Returns:
            8x8 matrix where True=white, False=black, None=empty
        """
        color_matrix = []
        for row in range(8):
            color_row = []
            for col in range(8):
                class_label, _ = detected_state[row][col]
                if class_label == 'empty':
                    color_row.append(None)
                elif class_label == 'white':
                    color_row.append(True)  # White
                elif class_label == 'black':
                    color_row.append(False)  # Black
                else:
                    color_row.append(None)  # Unknown, treat as empty
            color_matrix.append(color_row)
        return color_matrix
    
    def _states_are_equal(self, state1: List[List[Optional[bool]]], state2: List[List[Optional[bool]]]) -> bool:
        """
        Compare two color matrices for equality.
        
        Args:
            state1: First 8x8 color matrix
            state2: Second 8x8 color matrix
        
        Returns:
            True if states are identical
        """
        for row in range(8):
            for col in range(8):
                if state1[row][col] != state2[row][col]:
                    return False
        return True
    
    def _find_matching_move(self, detected_colors: List[List[Optional[bool]]]) -> Optional[chess.Move]:
        """
        Try all legal moves to find one that matches the detected color pattern.
        
        Args:
            detected_colors: 8x8 matrix where True=white, False=black, None=empty
        
        Returns:
            chess.Move if found, None otherwise
        """
        # Try each legal move
        for move in self.board.legal_moves:
            # Create a copy to test the move
            test_board = self.board.copy()
            test_board.push(move)
            
            # Check if this board matches detected colors
            if self._board_matches_colors(test_board, detected_colors):
                return move
        
        return None
    
    def _board_matches_colors(self, board: chess.Board, detected_colors: List[List[Optional[bool]]]) -> bool:
        """
        Check if a chess board matches the detected color pattern.
        
        Args:
            board: chess.Board to check
            detected_colors: Expected color matrix
        
        Returns:
            True if board matches detected colors
        """
        for rank in range(7, -1, -1):  # 7 down to 0
            row = 7 - rank  # Convert to matrix row (0 = rank 8)
            for file in range(8):
                square = chess.square(file, rank)
                piece = board.piece_at(square)
                
                detected = detected_colors[row][file]
                
                if detected is None:
                    # Expected empty
                    if piece is not None:
                        return False
                elif detected is True:
                    # Expected white piece
                    if piece is None or piece.color != chess.WHITE:
                        return False
                elif detected is False:
                    # Expected black piece
                    if piece is None or piece.color != chess.BLACK:
                        return False
        
        return True
    
    def get_mismatch_squares(self, detected_colors: Optional[List[List[Optional[bool]]]] = None) -> List[Tuple[int, int]]:
        """
        Return the squares where a detected color matrix differs from the
        current (expected) board position.

        Useful for highlighting an illegal / unverified board state: it marks
        every square whose detected occupancy/color does not match the last
        known-good position.

        Args:
            detected_colors: 8x8 color matrix (True=white, False=black, None=empty).
                             Defaults to the most recently detected state.

        Returns:
            List of (row, col) widget coordinates (row 0 = rank 8, col 0 = file a).
        """
        if detected_colors is None:
            detected_colors = self.last_detected_colors
        if detected_colors is None:
            return []

        mismatches = []
        for rank in range(7, -1, -1):  # 7 down to 0
            row = 7 - rank  # Convert to matrix row (0 = rank 8)
            for file in range(8):
                square = chess.square(file, rank)
                piece = self.board.piece_at(square)
                detected = detected_colors[row][file]

                if detected is None:
                    matches = piece is None
                elif detected is True:
                    matches = piece is not None and piece.color == chess.WHITE
                else:  # detected is False
                    matches = piece is not None and piece.color == chess.BLACK

                if not matches:
                    mismatches.append((row, file))

        return mismatches

    @staticmethod
    def move_to_arrows(move: chess.Move, is_castling: bool) -> List[Tuple[int, int, int, int]]:
        """
        Convert a chess.Move into widget arrow tuples (from_row, from_col,
        to_row, to_col) in widget coordinates (row 0 = rank 8, col 0 = file a).

        A normal move yields one arrow; castling yields two (the king and the
        rook). Works for moves that have not been applied to a board yet, since
        whether the move castles is passed in explicitly.
        """
        def to_rc(square):
            return (7 - chess.square_rank(square), chess.square_file(square))

        from_rc = to_rc(move.from_square)
        to_rc_ = to_rc(move.to_square)
        arrows = [(from_rc[0], from_rc[1], to_rc_[0], to_rc_[1])]

        if is_castling:
            kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
            rank = chess.square_rank(move.from_square)
            rook_from = chess.square(7 if kingside else 0, rank)
            rook_to = chess.square(5 if kingside else 3, rank)
            rf = to_rc(rook_from)
            rt = to_rc(rook_to)
            arrows.append((rf[0], rf[1], rt[0], rt[1]))

        return arrows

    def get_last_move_arrows(self) -> List[Tuple[int, int, int, int]]:
        """
        Return arrows describing the most recently applied move.

        A normal move yields one arrow; castling yields two (king and rook).

        Returns:
            List of arrow tuples (empty if no move has been applied yet).
        """
        move = self.last_move
        if move is None:
            return []

        # Castling: the move is already applied, so the king now sits on to_square.
        piece = self.board.piece_at(move.to_square)
        file_delta = chess.square_file(move.to_square) - chess.square_file(move.from_square)
        is_castling = piece is not None and piece.piece_type == chess.KING and abs(file_delta) == 2

        return self.move_to_arrows(move, is_castling)

    def reset(self):
        """Reset board to starting position."""
        self.board = chess.Board()
        self.current_state = self._board_to_matrix()
        self.previous_detected_state = None
        self.last_detected_colors = None
        self.last_move = None
        self.chess_widget.set_board_state(self.current_state)
    
    def get_fen(self) -> str:
        """Get current board state as FEN string."""
        return self.board.fen()
    
    def get_current_state(self) -> List[List[str]]:
        """Get current board state as widget matrix."""
        return [row[:] for row in self.current_state]
