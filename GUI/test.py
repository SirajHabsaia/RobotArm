import numpy as np
import sys
import os

# Add Chess folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Chess'))

from Chess.chess_engine import ChessEngine
from planner import TrajectoryPlanner
from kinematics import inverse_kinematics, direct_kinematics
import chess


def generate_waypoints_for_move(move_uci: str, robot_color: chess.Color = chess.WHITE, should_plot: bool = False) -> str:
    """
    Generate Arduino waypoints for a chess move.
    
    Args:
        move_uci: Move in UCI notation (e.g., 'e2e4', 'e7e8q' for promotion)
        robot_color: Color the robot is playing
    
    Returns:
        String with Arduino command format
    """
    print(f"\n{'='*60}")
    print(f"Generating trajectory for move: {move_uci}")
    print(f"{'='*60}\n")
    
    # Initialize chess engine (without Stockfish since we're providing the move)
    # We just need it for coordinate mapping and trajectory generation
    try:
        # Try to initialize with stockfish (may not be available)
        engine = ChessEngine(
            stockfish_path=".stockfish/stockfish-windows-x86-64-avx2.exe",
            robot_color=robot_color,
            skill_level=1
        )
    except:
        print("[Warning] Stockfish not available, using dummy engine")
        engine = ChessEngine.__new__(ChessEngine)
        engine.robot_color = robot_color
        engine.board = chess.Board()
    
    # Parse the move
    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError as e:
        print(f"Error: Invalid move format '{move_uci}': {e}")
        return None
    
    # Generate trajectory data
    trajectory_data = engine.generate_move_trajectory(move)
    
    print(f"Move: {trajectory_data['description']}")
    print(f"Duration: {trajectory_data['T_duration']}s")
    print(f"Gripper actions: {trajectory_data['gripper_actions']}\n")
    
    # Setup trajectory planner
    joints_max_speeds = np.array([30.0, 15.0, 15.0])  # deg/s
    joints_max_accel = np.array([20.0, 10.0, 10.0])   # deg/s^2
    
    # IK/FK wrappers
    ik_func = lambda x, y, z, mu: [angle * 180.0/np.pi for angle in inverse_kinematics(x, y, z, mu=mu)]
    fk_func = lambda theta, alpha, beta, gamma: direct_kinematics(
        theta * np.pi/180.0, alpha * np.pi/180.0, beta * np.pi/180.0, gamma * np.pi/180.0
    )
    
    # Create planner
    planner = TrajectoryPlanner(
        joints_max_speeds=joints_max_speeds,
        joints_max_accel=joints_max_accel,
        n_waypoints_input=100,
        dt_sample=1e-3,
        inverse_kinematics_func=ik_func,
        forward_kinematics_func=fk_func,
        mu_func=ChessEngine.mu_func,
        gripper_actions=trajectory_data['gripper_actions'],
        adaptive_sampling=False
    )
    
    # Plan trajectory
    planned_waypoints = planner.plan_trajectory(
        trajectory_data['trajectory_func'],
        trajectory_data['T_duration']
    )
    
    # Generate Arduino command format
    print("\n" + "="*60)
    print("Generated Waypoints (Arduino Format)")
    print("="*60 + "\n")
    
    if should_plot:
        print("\nGenerating plots...")
        planner.plot_results(trajectory_data['trajectory_func'], trajectory_data['T_duration'])
    
    time_us = round(planner.output_waypoint_dt * 1e6)
    output_parts = [f"wn{planner.output_waypoint_count}d{time_us}"]
    
    for waypoint in planned_waypoints:
        theta, alpha, beta, mu, gripper = waypoint
        waypoint_str = f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}"
        output_parts.append(waypoint_str)
    
    output = ",".join(output_parts)
    print(output)
    
    # Clean up
    if hasattr(engine, 'engine'):
        engine.close()
    
    return output


if __name__ == "__main__":
    # Example usage
    move_uci = "a8h1"  # Change this to test different moves
    
    # You can also test captures:
    # move_uci = "e4d5"  # Capture move
    
    # Generate waypoints
    waypoints_command = generate_waypoints_for_move(move_uci, robot_color=chess.WHITE, should_plot=False)
    
    if waypoints_command:
        print("\n✓ Waypoints generated successfully!")
        print(f"Total length: {len(waypoints_command)} characters")
