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
    
    # Chess board edge anchors for coordinate interpolation
    FILE_A_Y = -132.0
    FILE_H_Y = 132.0
    RANK_1_X = 470.0
    RANK_8_X = 198.0
    
    # Robot parameters
    HOME_POSITION = (100.0, 0.0, 130.0)  # Default home position
    
    # Pickup heights per piece type (in mm)
    PICKUP_HEIGHTS = {
        chess.PAWN: 20.0,
        chess.KNIGHT: 20.0,
        chess.BISHOP: 28.0,
        chess.ROOK: 22.0,
        chess.QUEEN: 43.0,
        chess.KING: 43.0,
    }
    
    ARC_HEIGHT = 95.0  # Height of arc during piece transport
    DISCARD_POSITION = (340.0, -250.0, 110.0)  # Where to place captured pieces

    # Trajectory duration is computed as 4.0s per pick-and-place operation
    # (see _build_trajectory): 4s for a simple move, 8s for a capture/castle.

    # Gripper angles
    GRIPPER_OPEN = 40.0
    
    # Gripper closed angles per piece type (activation %)
    GRIPPER_CLOSED_ANGLES = {
        chess.PAWN: 95.0,
        chess.KNIGHT: 100.0,
        chess.BISHOP: 91.0,
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
                 skill_level: int = 20,
                 file_a_y: float = FILE_A_Y,
                 file_h_y: float = FILE_H_Y,
                 rank_1_x: float = RANK_1_X,
                 rank_8_x: float = RANK_8_X):
        """
        Initialize chess engine.
        
        Args:
            stockfish_path: Path to Stockfish executable
            robot_color: Color the robot plays (chess.WHITE or chess.BLACK)
            skill_level: Stockfish skill level (0-20, 20 is strongest)
            file_a_y: Robot Y coordinate for file a
            file_h_y: Robot Y coordinate for file h
            rank_1_x: Robot X coordinate for rank 1
            rank_8_x: Robot X coordinate for rank 8
        """
        self.robot_color = robot_color

        # Generate square mappings from configurable board-edge anchors.
        self.file_to_y = {
            chr(ord('a') + i): file_a_y + (file_h_y - file_a_y) * i / 7
            for i in range(8)
        }
        self.rank_to_x = {
            str(1 + i): rank_1_x + (rank_8_x - rank_1_x) * i / 7
            for i in range(8)
        }
        
        # Initialize Stockfish
        self.engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)
        self.engine.configure({"Skill Level": skill_level})
        
        # Current board state
        self.board = chess.Board()
        
        print(f"[ChessEngine] Initialized Stockfish (skill={skill_level})")
        print(f"[ChessEngine] Robot plays: {'White' if robot_color == chess.WHITE else 'Black'}")

    @classmethod
    def create_offline(cls,
                       robot_color: chess.Color = chess.WHITE,
                       file_a_y: float = FILE_A_Y,
                       file_h_y: float = FILE_H_Y,
                       rank_1_x: float = RANK_1_X,
                       rank_8_x: float = RANK_8_X) -> "ChessEngine":
        """
        Create a ChessEngine WITHOUT launching Stockfish.

        Useful for coordinate/trajectory utilities (e.g. manual test moves) that
        only need square-to-coordinate mapping and trajectory building, not move
        search.
        """
        self = cls.__new__(cls)
        self.robot_color = robot_color
        self.engine = None
        self.board = chess.Board()
        self.file_to_y = {
            chr(ord('a') + i): file_a_y + (file_h_y - file_a_y) * i / 7
            for i in range(8)
        }
        self.rank_to_x = {
            str(1 + i): rank_1_x + (rank_8_x - rank_1_x) * i / 7
            for i in range(8)
        }
        return self

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
    
    def square_to_coords(self, square_name: str, piece_type: Optional[int] = None,
                         position_pct: Optional[Tuple[float, float]] = None) -> Tuple[float, float, float]:
        """
        Convert chess square notation to robot coordinates.

        Args:
            square_name: Chess square like 'e4', 'a1', etc.
            piece_type: Chess piece type (chess.PAWN, etc.) for pickup height.
                       If None, uses PAWN height as default.
            position_pct: Optional ``(x_pct, y_pct)`` from the position model,
                       giving where the piece actually sits inside its square
                       (bottom-left origin: x left->right, y bottom->top, 50/50 =
                       centre). When given, the returned (x, y) is refined to the
                       piece centre instead of the geometric square centre.

        Returns:
            (x, y, z) coordinates where z is pickup height for the piece
        """
        file = square_name[0]
        rank = square_name[1]

        # Geometric centre of the square
        x = self.rank_to_x[rank]
        y = self.file_to_y[file]

        # Refine to the true piece position within the square, if provided.
        if position_pct is not None:
            x_pct, y_pct = position_pct
            # Per-square step vectors derived from the same board-edge anchors
            # used for the centres, so this stays consistent with the calibration:
            #   - files a->h run along +y  (FILE_A_Y -> FILE_H_Y)
            #   - ranks 1->8 run along x   (RANK_1_X -> RANK_8_X)
            d_file_y = (self.file_to_y['h'] - self.file_to_y['a']) / 7.0
            d_rank_x = (self.rank_to_x['8'] - self.rank_to_x['1']) / 7.0
            # x_pct (crop left->right) maps to the file axis (robot y);
            # y_pct (crop bottom->top, i.e. toward rank 8) maps to the rank axis (robot x).
            y = y + (x_pct / 100.0 - 0.5) * d_file_y
            x = x + (y_pct / 100.0 - 0.5) * d_rank_x

        # Get piece-specific pickup height
        if piece_type is None:
            piece_type = chess.PAWN  # Default
        z = self.PICKUP_HEIGHTS.get(piece_type, self.PICKUP_HEIGHTS[chess.PAWN])

        return (x, y, z)
    
    def generate_move_trajectory(self,
                                move: chess.Move,
                                home_position: Optional[Tuple[float, float, float]] = None,
                                piece_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict:
        """
        Generate trajectory function and parameters for a chess move.

        The move is first decomposed into an ordered list of pick-and-place
        operations (see ``_decompose_move``) so every move type is handled
        uniformly:
            - simple move          -> 1 operation
            - capture / en passant -> 2 operations (discard captured piece, then move)
            - castling             -> 2 operations (move king, then move rook)

        Each operation carries the correct pickup height and gripper angle for
        the specific piece it handles, so the eater and the eaten piece no
        longer share a single height, and the captured piece is grabbed from its
        real square (which differs from the mover's destination for en passant).

        Args:
            move: Chess move to execute
            home_position: Starting position, defaults to HOME_POSITION
            piece_positions: Optional dict mapping square name (e.g. 'e2') to the
                       position-model output ``(x_pct, y_pct)`` for the piece on
                       that square. Used to aim picks at the true piece centre
                       instead of the geometric square centre.

        Returns:
            Dictionary with:
                - 'trajectory_func': Function f(t) -> [x, y, z]
                - 'T_duration': Total duration
                - 'gripper_actions': Dict of time -> gripper angle
                - 'description': Human-readable move description
                - 'move': the chess.Move
        """
        if home_position is None:
            home_position = self.HOME_POSITION

        operations, description = self._decompose_move(move, piece_positions)

        trajectory_func, T_duration, gripper_actions = self._build_trajectory(operations, home_position)

        print(f"[ChessEngine] {description} ({len(operations)} pick-and-place op(s), T={T_duration}s)")
        for i, op in enumerate(operations):
            print(f"[ChessEngine]   op{i}: pick z={op['pick'][2]:.1f}  place z={op['place'][2]:.1f}  grip={op['grip']}°")

        return {
            'trajectory_func': trajectory_func,
            'T_duration': T_duration,
            'gripper_actions': gripper_actions,
            'description': description,
            'move': move
        }

    def generate_simple_move_trajectory(self,
                                        piece_type: int,
                                        from_square: str,
                                        to_square: str,
                                        home_position: Optional[Tuple[float, float, float]] = None) -> Dict:
        """
        Generate a trajectory for a single pick-and-place move of a given piece
        type, independent of any board state.

        Unlike ``generate_move_trajectory`` this does not look at the board (no
        capture/castling handling): it simply picks up the piece at
        ``from_square`` and places it on ``to_square``, using the pickup height
        and gripper activation of the supplied piece type. Intended for manual
        test moves.

        Args:
            piece_type: chess piece type (chess.PAWN, chess.ROOK, ...)
            from_square: source square, e.g. 'a1'
            to_square: destination square, e.g. 'h2'
            home_position: starting position, defaults to HOME_POSITION

        Returns:
            Same dict shape as ``generate_move_trajectory`` (with 'move' = None).
        """
        if home_position is None:
            home_position = self.HOME_POSITION

        grip = self.GRIPPER_CLOSED_ANGLES.get(piece_type, self.GRIPPER_CLOSED_ANGLES[chess.PAWN])
        operations = [{
            'pick': self.square_to_coords(from_square, piece_type),
            'place': self.square_to_coords(to_square, piece_type),
            'grip': grip,
        }]

        trajectory_func, T_duration, gripper_actions = self._build_trajectory(operations, home_position)
        description = f"Test move {chess.piece_name(piece_type)} {from_square}->{to_square}"

        print(f"[ChessEngine] {description} (T={T_duration}s, pick z={operations[0]['pick'][2]:.1f}, grip={grip}°)")

        return {
            'trajectory_func': trajectory_func,
            'T_duration': T_duration,
            'gripper_actions': gripper_actions,
            'description': description,
            'move': None,
        }

    def get_pick_squares(self, move: chess.Move) -> List[str]:
        """
        Return the squares the robot will pick a real piece from for this move.

        Mirrors the pick operations of ``_decompose_move``:
            - normal move      -> [from]
            - capture           -> [captured_square, from]
            - en passant        -> [captured_pawn_square, from]
            - castling          -> [king_from, rook_from]

        Used to localize only the relevant squares with the position model.
        """
        from_square = chess.square_name(move.from_square)

        if self.board.is_castling(move):
            kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
            rank = chess.square_rank(move.from_square)
            rook_from = chess.square_name(chess.square(7 if kingside else 0, rank))
            return [from_square, rook_from]

        squares = []
        if self.board.is_capture(move):
            if self.board.is_en_passant(move):
                captured_idx = chess.square(
                    chess.square_file(move.to_square),
                    chess.square_rank(move.from_square),
                )
            else:
                captured_idx = move.to_square
            squares.append(chess.square_name(captured_idx))
        squares.append(from_square)
        return squares

    def _decompose_move(self, move: chess.Move,
                        piece_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> Tuple[List[Dict], str]:
        """
        Decompose a chess move into an ordered list of pick-and-place operations.

        Each operation is a dict::

            {
                'pick':  (x, y, z),   # where to grab a piece (z = that piece's pickup height)
                'place': (x, y, z),   # where to release it
                'grip':  angle,       # gripper closed angle for that piece
            }

        Operations run in order. A captured piece is removed (placed in the
        discard box) *before* the moving piece is placed, so the destination
        square is clear. This naturally supports:
            - normal captures  (captured piece sits on the destination square)
            - en passant        (captured pawn sits behind the destination square)
            - castling          (king and rook are two independent move operations)

        ``piece_positions`` (square name -> (x_pct, y_pct)) refines every *pick*
        to the true piece centre reported by the position model. Places always
        target the geometric square centre (we set the piece down centred).

        Returns:
            (operations, description)
        """
        operations: List[Dict] = []
        positions = piece_positions or {}

        def pick_coords(square_name, piece_type):
            """Pick location, refined by the position model if available for that square."""
            return self.square_to_coords(square_name, piece_type, positions.get(square_name))

        from_square = chess.square_name(move.from_square)
        to_square = chess.square_name(move.to_square)

        moving_piece = self.board.piece_at(move.from_square)
        moving_piece_type = moving_piece.piece_type if moving_piece else chess.PAWN
        moving_grip = self.GRIPPER_CLOSED_ANGLES.get(moving_piece_type, self.GRIPPER_CLOSED_ANGLES[chess.PAWN])

        # --- Castling: move the king first, then the rook (no capture) ---
        if self.board.is_castling(move):
            # Kingside if the king moves toward the h-file, otherwise queenside.
            kingside = chess.square_file(move.to_square) > chess.square_file(move.from_square)
            rank = chess.square_rank(move.from_square)
            rook_from = chess.square_name(chess.square(7 if kingside else 0, rank))
            rook_to = chess.square_name(chess.square(5 if kingside else 3, rank))

            operations.append({
                'pick': pick_coords(from_square, chess.KING),
                'place': self.square_to_coords(to_square, chess.KING),
                'grip': moving_grip,
            })
            operations.append({
                'pick': pick_coords(rook_from, chess.ROOK),
                'place': self.square_to_coords(rook_to, chess.ROOK),
                'grip': self.GRIPPER_CLOSED_ANGLES[chess.ROOK],
            })

            side = 'kingside' if kingside else 'queenside'
            return operations, f"Castle {side} ({from_square}->{to_square}, rook {rook_from}->{rook_to})"

        # --- Capture (including en passant): remove the captured piece first ---
        is_capture = self.board.is_capture(move)
        if is_capture:
            if self.board.is_en_passant(move):
                # The captured pawn is on the destination file but the source rank.
                captured_square_idx = chess.square(
                    chess.square_file(move.to_square),
                    chess.square_rank(move.from_square),
                )
                captured_piece_type = chess.PAWN
            else:
                captured_square_idx = move.to_square
                captured_piece = self.board.piece_at(captured_square_idx)
                captured_piece_type = captured_piece.piece_type if captured_piece else chess.PAWN

            captured_square = chess.square_name(captured_square_idx)
            captured_grip = self.GRIPPER_CLOSED_ANGLES.get(captured_piece_type, self.GRIPPER_CLOSED_ANGLES[chess.PAWN])

            operations.append({
                'pick': pick_coords(captured_square, captured_piece_type),
                'place': tuple(self.DISCARD_POSITION),
                'grip': captured_grip,
            })

        # --- Main move of our own piece ---
        operations.append({
            'pick': pick_coords(from_square, moving_piece_type),
            'place': self.square_to_coords(to_square, moving_piece_type),
            'grip': moving_grip,
        })

        verb = "Capture" if is_capture else "Move"
        return operations, f"{verb} {from_square} to {to_square}"
    
    def _build_trajectory(self, operations: List[Dict],
                          home: Tuple[float, float, float]):
        """
        Build a continuous trajectory function from a list of pick-and-place
        operations.

        The end-effector starts and ends at ``home``. For each operation it:
            1. descends from the current position onto the pick point,
            2. lifts the piece up and over (arc) to the place point,
            3. travels (empty) to the next operation's pick point.

        Vertical legs to/from home use a quarter ellipse; transport and travel
        legs between board-level points use a symmetric arc that peaks at
        ``ARC_HEIGHT``, clearing every piece on the board (the tallest pickup
        height is well below ``ARC_HEIGHT``).

        Timing (in trajectory-parameter "seconds"):
            home -> pick_0                 : 1 unit
            pick_i -> place_i (transport)  : 2 units
            place_i -> pick_{i+1} (travel) : 2 units
            place_last -> home             : 1 unit
        so the total duration is ``4 * len(operations)``.

        Returns:
            (trajectory_func, T_duration, gripper_actions)
        """
        xi, yi, zi = home
        n = len(operations)
        zm = self.ARC_HEIGHT
        nexp = 3
        T_duration = 4.0 * n

        def quarter_ellipse(s, ax, ay, az, bx, by, bz):
            """Smooth quarter ellipse from (ax,ay,az) at s=0 to (bx,by,bz) at s=1."""
            s = 1 - (1 - s) ** nexp if s >= 0 else -1 + (1 + s) ** nexp
            return [
                ax + (bx - ax) * s,
                ay + (by - ay) * s,
                bz + (az - bz) * (1 - abs(s) ** nexp) ** (1 / nexp),
            ]

        def arc(s, x0, y0, z0, x1, y1, z1):
            """Arc peaking at ARC_HEIGHT: (x0,y0,z0) at s=0 -> apex at s=1 -> (x1,y1,z1) at s=2.

            Handles differing endpoint heights (e.g. board square -> discard box),
            and is velocity-continuous at the apex because it splits at the true
            midpoint.
            """
            mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            if s <= 1:
                return quarter_ellipse(1 - s, mx, my, zm, x0, y0, z0)
            return quarter_ellipse(s - 1, mx, my, zm, x1, y1, z1)

        def trajectory_func(t):
            # Descend from home onto the first pick point.
            if t <= 1:
                px, py, pz = operations[0]['pick']
                return quarter_ellipse(t, xi, yi, zi, px, py, pz)

            for i in range(n):
                pick = operations[i]['pick']
                place = operations[i]['place']
                t_pick = 1 + 4 * i      # arrival at pick_i
                t_place = t_pick + 2    # arrival at place_i

                # Transport the grabbed piece from pick_i to place_i.
                if t <= t_place:
                    return arc(t - t_pick, pick[0], pick[1], pick[2],
                               place[0], place[1], place[2])

                if i < n - 1:
                    # Travel (empty, gripper open) from place_i to the next pick.
                    next_pick = operations[i + 1]['pick']
                    t_next_pick = t_place + 2
                    if t <= t_next_pick:
                        return arc(t - t_place, place[0], place[1], place[2],
                                   next_pick[0], next_pick[1], next_pick[2])
                else:
                    # Ascend from the final place point back home.
                    return quarter_ellipse(1 - (t - t_place), xi, yi, zi,
                                           place[0], place[1], place[2])

            # t at/after T_duration -> home (safety fallback).
            return [xi, yi, zi]

        # Gripper: open at home, close on each pick, open on each place.
        gripper_actions = {0.0: self.GRIPPER_OPEN}
        for i, op in enumerate(operations):
            t_pick = float(1 + 4 * i)
            t_place = t_pick + 2.0
            gripper_actions[t_pick] = op['grip']
            gripper_actions[t_place] = self.GRIPPER_OPEN

        return trajectory_func, T_duration, gripper_actions
    
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