"""
Chess Engine - Generates robot trajectories for chess moves.

This module uses Stockfish to compute moves and translates them into
robot arm trajectories using the trajectory planner.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
import chess
import chess.engine


class ChessEngine:
    """
    Chess engine that generates robot trajectories for chess moves.
    
    Integrates Stockfish for move generation and trajectory planner
    for converting chess moves to robot commands.
    """
    
    # Chess square to robot coordinate mapping
    # Files: a=-132, h=132 (linear interpolation for b-g)
    FILE_TO_Y = {
        'a': -132.0,
        'b': -132.0 + (132.0 - (-132.0)) * 1/7,
        'c': -132.0 + (132.0 - (-132.0)) * 2/7,
        'd': -132.0 + (132.0 - (-132.0)) * 3/7,
        'e': -132.0 + (132.0 - (-132.0)) * 4/7,
        'f': -132.0 + (132.0 - (-132.0)) * 5/7,
        'g': -132.0 + (132.0 - (-132.0)) * 6/7,
        'h': 132.0,
    }
    
    # Ranks: 1=470, 8=203 (linear interpolation for 2-7)
    RANK_TO_X = {
        '1': 470.0,
        '2': 470.0 + (203.0 - 470.0) * 1/7,
        '3': 470.0 + (203.0 - 470.0) * 2/7,
        '4': 470.0 + (203.0 - 470.0) * 3/7,
        '5': 470.0 + (203.0 - 470.0) * 4/7,
        '6': 470.0 + (203.0 - 470.0) * 5/7,
        '7': 470.0 + (203.0 - 470.0) * 6/7,
        '8': 203.0,
    }
    
    # Robot parameters
    HOME_POSITION = (100.0, 0.0, 130.0)  # Default home position
    
    # Pickup heights per piece type (in mm)
    PICKUP_HEIGHTS = {
        chess.PAWN: 17.0,
        chess.KNIGHT: 23.0,
        chess.BISHOP: 28.0,
        chess.ROOK: 22.0,
        chess.QUEEN: 43.0,
        chess.KING: 43.0,
    }
    
    ARC_HEIGHT = 95.0  # Height of arc during piece transport
    DISCARD_POSITION = (340.0, -250.0, 110.0)  # Where to place captured pieces
    
    # Trajectory timing
    T_NO_CAPTURE = 4.0  # Duration for simple move (no capture)
    T_WITH_CAPTURE = 6.0  # Duration for move with capture
    
    # Gripper angles
    GRIPPER_OPEN = 40.0
    
    # Gripper closed angles per piece type (activation %)
    GRIPPER_CLOSED_ANGLES = {
        chess.PAWN: 88.0,
        chess.KNIGHT: 100.0,
        chess.BISHOP: 85.0,
        chess.ROOK: 82.0,
        chess.QUEEN: 80.0,
        chess.KING: 78.0,
    }
    
    # Mu function parameters
    RMIN = 250.0
    RMAX = 500.0
    MUMIN = -90.0  # degrees
    MUMAX = -45.0  # degrees
    
    def __init__(self, 
                 stockfish_path: str,
                 robot_color: chess.Color = chess.WHITE,
                 skill_level: int = 20):
        """
        Initialize chess engine.
        
        Args:
            stockfish_path: Path to Stockfish executable
            robot_color: Color the robot plays (chess.WHITE or chess.BLACK)
            skill_level: Stockfish skill level (0-20, 20 is strongest)
        """
        self.robot_color = robot_color
        
        # Initialize Stockfish
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.engine.configure({"Skill Level": skill_level})
        
        # Current board state
        self.board = chess.Board()
        
        print(f"[ChessEngine] Initialized Stockfish (skill={skill_level})")
        print(f"[ChessEngine] Robot plays: {'White' if robot_color == chess.WHITE else 'Black'}")
    
    def update_board(self, fen: str):
        """
        Update internal board state from FEN string.
        
        Args:
            fen: FEN string representing current board position
        """
        self.board = chess.Board(fen)
        print(f"[ChessEngine] Board updated: {fen}")
    
    def is_robot_turn(self) -> bool:
        """Check if it's the robot's turn to move."""
        return self.board.turn == self.robot_color
    
    def get_best_move(self, time_limit: float = 0.1) -> Optional[chess.Move]:
        """
        Get best move from Stockfish.
        
        Args:
            time_limit: Time limit for Stockfish in seconds
        
        Returns:
            Best move, or None if game is over
        """
        if self.board.is_game_over():
            print("[ChessEngine] Game over!")
            return None
        
        result = self.engine.play(self.board, chess.engine.Limit(time=time_limit))
        print(f"[ChessEngine] Stockfish suggests: {result.move.uci()}")
        
        return result.move
    
    def square_to_coords(self, square_name: str, piece_type: Optional[int] = None) -> Tuple[float, float, float]:
        """
        Convert chess square notation to robot coordinates.
        
        Args:
            square_name: Chess square like 'e4', 'a1', etc.
            piece_type: Chess piece type (chess.PAWN, etc.) for pickup height.
                       If None, uses PAWN height as default.
        
        Returns:
            (x, y, z) coordinates where z is pickup height for the piece
        """
        file = square_name[0]
        rank = square_name[1]
        
        x = self.RANK_TO_X[rank]
        y = self.FILE_TO_Y[file]
        
        # Get piece-specific pickup height
        if piece_type is None:
            piece_type = chess.PAWN  # Default
        z = self.PICKUP_HEIGHTS.get(piece_type, self.PICKUP_HEIGHTS[chess.PAWN])
        
        return (x, y, z)
    
    def generate_move_trajectory(self, 
                                move: chess.Move,
                                home_position: Optional[Tuple[float, float, float]] = None) -> Dict:
        """
        Generate trajectory function and parameters for a chess move.
        
        Args:
            move: Chess move to execute
            home_position: Starting position, defaults to HOME_POSITION
        
        Returns:
            Dictionary with:
                - 'trajectory_func': Function f(t) -> [x, y, z]
                - 'T_duration': Total duration
                - 'gripper_actions': Dict of time -> gripper angle
                - 'description': Human-readable move description
        """
        if home_position is None:
            home_position = self.HOME_POSITION
        
        xi, yi, zi = home_position
        
        # Get source and destination squares
        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)
        
        # Determine piece types for correct pickup heights and gripper angles
        moving_piece = self.board.piece_at(move.from_square)
        moving_piece_type = moving_piece.piece_type if moving_piece else chess.PAWN
        
        xp, yp, zp = self.square_to_coords(from_square, moving_piece_type)
        xg, yg, zg = self.square_to_coords(to_square, moving_piece_type)
        
        # Get gripper angle for the moving piece
        gripper_closed = self.GRIPPER_CLOSED_ANGLES.get(moving_piece_type, self.GRIPPER_CLOSED_ANGLES[chess.PAWN])
        
        # Check if this is a capture
        is_capture = self.board.is_capture(move)
        
        # For captures, get the captured piece info
        if is_capture:
            captured_piece = self.board.piece_at(move.to_square)
            captured_piece_type = captured_piece.piece_type if captured_piece else chess.PAWN
            gripper_closed_captured = self.GRIPPER_CLOSED_ANGLES.get(captured_piece_type, self.GRIPPER_CLOSED_ANGLES[chess.PAWN])
            # Recompute destination with captured piece height for initial grab
            xg_capture, yg_capture, zg_capture = self.square_to_coords(to_square, captured_piece_type)
        
        print(f"[ChessEngine] Generating trajectory: {from_square} -> {to_square} (capture={is_capture})")
        print(f"[ChessEngine] Moving piece: {chess.piece_name(moving_piece_type)}, gripper={gripper_closed}°")
        
        # Define trajectory function
        if not is_capture:
            # Simple move: home -> pickup -> destination -> home
            T_duration = self.T_NO_CAPTURE
            
            def trajectory_func(t):
                return self._move_piece(
                    t, xi, yi, zi, xp, yp, zp, xg, yg, 
                    zm=self.ARC_HEIGHT, n=3, existing_piece=False
                )
            
            gripper_actions = {
                0.0: self.GRIPPER_OPEN,   # Start open
                1.0: gripper_closed,       # Close on piece
                3.0: self.GRIPPER_OPEN,    # Release piece
            }
            
            description = f"Move {from_square} to {to_square}"
        
        else:
            # Capture: home -> target (grab it) -> discard -> pickup source -> destination -> home
            T_duration = self.T_WITH_CAPTURE
            xbox, ybox, zbox = self.DISCARD_POSITION
            
            def trajectory_func(t):
                return self._move_piece(
                    t, xi, yi, zi, xp, yp, zp, xg_capture, yg_capture,
                    zm=self.ARC_HEIGHT, n=3, existing_piece=True,
                    xbox=xbox, ybox=ybox, zbox=zbox
                )
            
            gripper_actions = {
                0.0: self.GRIPPER_OPEN,        # Start open
                1.0: gripper_closed_captured,   # Grab opponent piece
                2.0: self.GRIPPER_OPEN,         # Release at discard
                3.0: gripper_closed,            # Grab our piece
                5.0: self.GRIPPER_OPEN,         # Release at destination
            }
            
            description = f"Capture {from_square} to {to_square}"
        
        return {
            'trajectory_func': trajectory_func,
            'T_duration': T_duration,
            'gripper_actions': gripper_actions,
            'description': description,
            'move': move
        }
    
    def _move_piece(self, s, xi, yi, zi, xp, yp, zp, xg, yg, zm, n=3, 
                   existing_piece=False, xbox=None, ybox=None, zbox=None):
        """
        Generate trajectory for moving a chess piece.
        
        This uses the same logic as in planner.py's move_piece function.
        
        Args:
            s: Time parameter (normalized trajectory time)
            xi, yi, zi: Home position
            xp, yp, zp: Pickup position (source square)
            xg, yg: Goal position (destination square) - z will be zp
            zm: Arc height during transport
            n: Ellipse exponent for smoothness
            existing_piece: If True, first move opponent piece to discard
            xbox, ybox, zbox: Discard box position (required if existing_piece=True)
        """
        # Quarter ellipse helper
        def quarter_ellipse(s, xi, yi, zi, xf, yf, zf, n=3):
            s = 1-(1-s)**n if s>=0 else -1+(1+s)**n
            return [
                xi + (xf - xi) * s,
                yi + (yf - yi) * s,
                zf + (zi - zf) * (1 - abs(s)**n) ** (1/n)
            ]
        
        # Semi ellipse helper
        def semi_ellipse(s, xi, yi, zi, xf, yf, zm, n=3):
            s = s-1
            return quarter_ellipse(s, (xi+xf)/2, (yi+yf)/2, zm, xf, yf, zi, n=n)
        
        if not existing_piece:
            # Simple move trajectory
            if s <= 1: 
                return quarter_ellipse(s, xi, yi, zi, xp, yp, zp, n=n)
            if s <= 3: 
                return semi_ellipse(s-1, xp, yp, zp, xg, yg, zm, n=n)
            return quarter_ellipse(1-(s-3), xi, yi, zi, xg, yg, zp, n=n)
        else:
            # Capture trajectory (with discard)
            if xbox is None or ybox is None or zbox is None:
                raise ValueError("Discard position required for existing_piece=True")
            
            if s <= 1: 
                return quarter_ellipse(s, xi, yi, zi, xg, yg, zp, n=n)
            if s <= 2: 
                return quarter_ellipse(1-(s-1), xbox, ybox, zbox, xg, yg, zp, n=n)
            if s <= 3: 
                return quarter_ellipse(s-2, xbox, ybox, zbox, xp, yp, zp, n=n)
            if s <= 5: 
                return semi_ellipse(s-3, xp, yp, zp, xg, yg, zm, n=n)
            return quarter_ellipse(1-(s-5), xi, yi, zi, xg, yg, zp, n=n)
    
    @staticmethod
    def mu_func(x: float, y: float, z: float) -> float:
        """
        Compute mu (end-effector orientation) based on position.
        
        Same mu function as in planner.py's __main__.
        
        Args:
            x, y, z: Cartesian coordinates
        
        Returns:
            mu in radians
        """
        r = np.sqrt(x**2 + y**2)
        if r < ChessEngine.RMIN:
            mu_deg = ChessEngine.MUMIN
        elif r > ChessEngine.RMAX:
            mu_deg = ChessEngine.MUMAX
        else:
            mu_deg = ChessEngine.MUMIN + (ChessEngine.MUMAX - ChessEngine.MUMIN) * (r - ChessEngine.RMIN) / (ChessEngine.RMAX - ChessEngine.RMIN)
        return mu_deg * np.pi / 180.0  # Return radians
    
    def close(self):
        """Clean up Stockfish engine."""
        self.engine.quit()
        print("[ChessEngine] Stockfish engine closed")


# Example usage
if __name__ == "__main__":
    # Initialize engine
    engine = ChessEngine(
        stockfish_path=".stockfish/stockfish-windows-x86-64-avx2.exe",  # Adjust path as needed
        robot_color=chess.WHITE,
        skill_level=10
    )
    
    try:
        # Simulate a position
        engine.board.push_san("e4")
        engine.board.push_san("e5")
        engine.board.push_san("Nf3")
        engine.board.push_san("Nc6")
        
        print(f"Current board:\n{engine.board}")
        print(f"Is robot's turn: {engine.is_robot_turn()}")
        
        # Get best move
        if engine.is_robot_turn():
            best_move = engine.get_best_move()
            
            if best_move:
                # Generate trajectory
                trajectory_data = engine.generate_move_trajectory(best_move)
                
                print(f"\nTrajectory generated:")
                print(f"  Description: {trajectory_data['description']}")
                print(f"  Duration: {trajectory_data['T_duration']}s")
                print(f"  Gripper actions: {trajectory_data['gripper_actions']}")
                
                # Test trajectory function
                traj_func = trajectory_data['trajectory_func']
                print(f"  Start position: {traj_func(0.0)}")
                print(f"  End position: {traj_func(trajectory_data['T_duration'])}")
    
    finally:
        engine.close()