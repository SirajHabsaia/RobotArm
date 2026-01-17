import numpy as np
import matplotlib.pyplot as plt
from typing import Callable, List, Tuple, Optional
import toppra
import toppra.constraint as constraint
import toppra.algorithm as algo


class TrajectoryPlanner:
    """Time-optimal trajectory planner for robotic arm motion.
    
    Generates smooth, time-optimal trajectories respecting velocity and acceleration constraints.
    Supports automatic inverse kinematics transformation from Cartesian to joint space.
    """
    
    def __init__(self, 
                 n_joints: int,
                 joints_names: List[str],
                 joints_max_speeds: np.ndarray,
                 joints_max_accel: np.ndarray,
                 dt_waypoints: float = 0.2,
                 dt_sample: float = 1e-3,
                 inverse_kinematics_func: Optional[Callable] = None):
        """
        Initialize trajectory planner with joint constraints.
        
        Args:
            n_joints: Number of joints
            joints_names: Names of joints for plotting
            joints_max_speeds: Maximum velocity per joint (deg/s or rad/s)
            joints_max_accel: Maximum acceleration per joint (deg/s^2 or rad/s^2)
            dt_waypoints: Time step for sampling input trajectory
            dt_sample: Time step for dense trajectory reconstruction
            inverse_kinematics_func: Optional function(x, y, z) -> [q1, q2, q3, ...] 
                                    to convert Cartesian to joint space
        """
        self.n_joints = n_joints
        self.joints_names = joints_names
        self.joints_max_speeds = np.array(joints_max_speeds)
        self.joints_max_accel = np.array(joints_max_accel)
        self.dt_waypoints = dt_waypoints
        self.dt_sample = dt_sample
        self.inverse_kinematics = inverse_kinematics_func
        
        # Results (populated after planning)
        self.planned_waypoints = []
        self.total_time = 0.0
        self.node_times = None
        self.t_dense = None
        self.q_dense = None
        self.qdot_dense = None
        self.output_waypoint_count = 0
        self.output_waypoint_dt = 0.0
        
    def plan_trajectory(self, 
                       trajectory_func: Callable,
                       T_duration: float,
                       apply_ik: bool = False) -> List[Tuple[float, ...]]:
        """
        Plan time-optimal trajectory from a given function using TOPPRA.
        
        Args:
            trajectory_func: Function f(t) -> [coord1, coord2, coord3, ...]
                           Returns Cartesian coords if apply_ik=True, joint coords otherwise
            T_duration: Duration of input trajectory function
            apply_ik: If True, apply inverse kinematics to convert Cartesian to joint space
            
        Returns:
            planned_waypoints: List of waypoints, each is (pos_j0, pos_j1, pos_j2, ...)
        """
        # Generate waypoints
        t_waypoints = np.arange(0.0, T_duration + 1e-9, self.dt_waypoints)
        waypoints_raw = np.array([trajectory_func(t) for t in t_waypoints])
        
        # Apply inverse kinematics if requested
        if apply_ik:
            if self.inverse_kinematics is None:
                raise ValueError("Inverse kinematics function not provided")
            waypoints = np.array([self.inverse_kinematics(*wp) for wp in waypoints_raw])
        else:
            waypoints = waypoints_raw
        
        n_waypoints = len(waypoints)
        
        # Create geometric path using waypoints
        # TOPPRA expects a path parametrized by a scalar s in [0, 1]
        path_positions = waypoints
        
        # Create a path using spline interpolation (piecewise polynomial)
        # Normalize path parameter to [0, 1]
        ss = np.linspace(0, 1, n_waypoints)
        path = toppra.SplineInterpolator(ss, path_positions)
        
        # Setup velocity and acceleration constraints
        vlim = np.vstack([-self.joints_max_speeds, self.joints_max_speeds]).T
        alim = np.vstack([-self.joints_max_accel, self.joints_max_accel]).T
        
        pc_vel = constraint.JointVelocityConstraint(vlim)
        pc_acc = constraint.JointAccelerationConstraint(alim)
        
        # Setup TOPPRA instance with constraints
        instance = algo.TOPPRA(
            [pc_vel, pc_acc], 
            path,
            parametrizer="ParametrizeConstAccel"
        )
        
        # Compute time-optimal parameterization
        jnt_traj = instance.compute_trajectory()
        
        if jnt_traj is None:
            raise ValueError("TOPPRA failed to compute trajectory. Check constraints.")
        
        # Get trajectory duration
        self.total_time = jnt_traj.duration
        
        # Reconstruct trajectory at high resolution
        self.t_dense = np.arange(0.0, self.total_time + self.dt_sample/2.0, self.dt_sample) if self.total_time > 0 else np.array([0.0])
        
        # Evaluate trajectory at dense time points
        self.q_dense = jnt_traj(self.t_dense)
        self.qdot_dense = jnt_traj(self.t_dense, 1)  # First derivative
        
        # Store node times for compatibility (find closest trajectory points to waypoints)
        self.node_times = np.zeros(n_waypoints)
        for i, wp in enumerate(waypoints):
            # Find the time when trajectory is closest to this waypoint
            distances = np.linalg.norm(self.q_dense - wp, axis=1)
            closest_idx = np.argmin(distances)
            self.node_times[i] = self.t_dense[closest_idx]
        
        # Generate output waypoints from optimized trajectory
        min_waypoint_dt = 0.02  # 20ms minimum spacing
        max_waypoint_count = 100
        
        # Calculate time spacing and number of points
        if self.total_time / min_waypoint_dt > max_waypoint_count:
            # Use max 100 points
            self.output_waypoint_count = max_waypoint_count
            self.output_waypoint_dt = self.total_time / max_waypoint_count
        else:
            # Use 20ms spacing
            self.output_waypoint_dt = min_waypoint_dt
            self.output_waypoint_count = int(np.ceil(self.total_time / min_waypoint_dt)) + 1
        
        # Sample waypoints from optimized trajectory at fixed time intervals
        self.planned_waypoints = []
        waypoint_times = np.linspace(0, self.total_time, self.output_waypoint_count)
        for t in waypoint_times:
            # Find position in dense trajectory
            idx = np.searchsorted(self.t_dense, t)
            idx = min(idx, len(self.t_dense) - 1)
            waypoint = tuple(self.q_dense[idx, j] for j in range(self.n_joints))
            self.planned_waypoints.append(waypoint)
        
        print("Total time:", self.total_time)
        print(f"Output waypoints: {self.output_waypoint_count} points @ {self.output_waypoint_dt*1000:.1f}ms spacing")
        
        return self.planned_waypoints
    
    def plot_results(self, trajectory_func=None, T_duration=None, apply_ik=False):
        """Plot planned trajectory results.
        
        Args:
            trajectory_func: Original trajectory function
            T_duration: Duration of original trajectory
            apply_ik: Whether IK was applied (if True, shows Cartesian and joint space original)
        """
        if self.q_dense is None:
            raise ValueError("No trajectory planned yet. Call plan_trajectory() first.")
        
        # Create figure with 4 columns
        fig, axes = plt.subplots(self.n_joints, 4, figsize=(20, 10))
        
        cartesian_labels = ['x', 'y', 'z']
        
        for j in range(self.n_joints):
            # Column 0: Original Cartesian trajectory (if IK was applied)
            if trajectory_func is not None and T_duration is not None and apply_ik:
                t_theory = np.linspace(0, T_duration, 501)
                cartesian_theory = np.array([trajectory_func(t) for t in t_theory])
                t_waypoints = np.arange(0.0, T_duration + 1e-9, self.dt_waypoints)
                cartesian_waypoints = np.array([trajectory_func(t) for t in t_waypoints])
                
                axes[j, 0].plot(t_theory, cartesian_theory[:, j], 'b-')
                axes[j, 0].scatter(t_waypoints, cartesian_waypoints[:, j], color='r', s=20)
                axes[j, 0].set_title(f"{cartesian_labels[j]} Cartesian original")
                axes[j, 0].set_ylabel(f"{cartesian_labels[j]} (mm)")
            else:
                axes[j, 0].set_title(f"Cartesian {cartesian_labels[j]} (N/A)")
                axes[j, 0].text(0.5, 0.5, 'No IK data', ha='center', va='center', 
                               transform=axes[j, 0].transAxes)
            
            # Column 1: Original joint trajectory (after IK if applied)
            if trajectory_func is not None and T_duration is not None:
                t_theory = np.linspace(0, T_duration, 501)
                t_waypoints = np.arange(0.0, T_duration + 1e-9, self.dt_waypoints)
                
                if apply_ik and self.inverse_kinematics is not None:
                    # Apply IK to get joint space trajectory
                    cartesian_theory = np.array([trajectory_func(t) for t in t_theory])
                    joint_theory = np.array([self.inverse_kinematics(*pos) for pos in cartesian_theory])
                    cartesian_waypoints = np.array([trajectory_func(t) for t in t_waypoints])
                    joint_waypoints = np.array([self.inverse_kinematics(*pos) for pos in cartesian_waypoints])
                else:
                    # Direct joint space trajectory
                    joint_theory = np.array([trajectory_func(t) for t in t_theory])
                    joint_waypoints = np.array([trajectory_func(t) for t in t_waypoints])
                
                axes[j, 1].plot(t_theory, joint_theory[:, j], 'g-')
                axes[j, 1].scatter(t_waypoints, joint_waypoints[:, j], color='r', s=20)
                axes[j, 1].set_title(f"{self.joints_names[j]} original (IK)")
                axes[j, 1].set_ylabel(f"{self.joints_names[j]} (deg)")
            else:
                axes[j, 1].set_title(f"{self.joints_names[j]} original (N/A)")
            
            # Column 2: Generated trajectory with waypoints
            axes[j, 2].plot(self.t_dense, self.q_dense[:, j], 'b-', linewidth=1.5)
            waypoints_pos = [wp[j] for wp in self.planned_waypoints]
            waypoint_times = np.linspace(0, self.total_time, self.output_waypoint_count)
            axes[j, 2].scatter(waypoint_times, waypoints_pos, color='red', s=30, zorder=5)
            axes[j, 2].set_title(f"{self.joints_names[j]} generated")
            axes[j, 2].set_ylabel(f"{self.joints_names[j]} (deg)")
            
            # Column 3: Generated velocity
            axes[j, 3].plot(self.t_dense, self.qdot_dense[:, j], 'b-')
            axes[j, 3].axhline(self.joints_max_speeds[j], color='r', linestyle='--', linewidth=1, label='Max')
            axes[j, 3].axhline(-self.joints_max_speeds[j], color='r', linestyle='--', linewidth=1)
            axes[j, 3].set_title(f"{self.joints_names[j]} speed")
            axes[j, 3].set_ylabel(f"Speed (deg/s)")
            if j == 0:
                axes[j, 3].legend(loc='upper right')

        # Add x-labels to bottom row
        for col in range(4):
            axes[-1, col].set_xlabel('Time (s)')
        
        for ax in axes.flatten():
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    # Example usage: standalone execution
    
    # Define joint constraints
    n_joints = 3
    joints_names = ['theta', 'alpha', 'beta']
    joints_max_speeds = np.array([30.0, 15.0, 15.0])   # deg/s
    joints_max_accel = np.array([20.0, 10.0, 10.0])   # deg/s^2
    
    # Define trajectory function and duration
    def trajectory_func(t):
        return [
            450,
            -300+60*t,
            0
        ]
    T_initial = 10.0
    
    # Create planner
    from kinematics import inverse_kinematics
    fct = lambda x, y, z: [angle * 180.0/np.pi for angle in inverse_kinematics(x, y, z)[:-1]]  # Convert to degrees and ignore mu
    planner = TrajectoryPlanner(
        n_joints=n_joints,
        joints_names=joints_names,
        joints_max_speeds=joints_max_speeds,
        joints_max_accel=joints_max_accel,
        dt_waypoints=0.2,
        dt_sample=1e-3,
        inverse_kinematics_func=fct
    )
    
    # Plan trajectory
    planned_waypoints = planner.plan_trajectory(trajectory_func, T_initial, apply_ik=True)
    
    # Print generated points
    print("\n=== Generated Waypoints ===")
    print(f"Count: {planner.output_waypoint_count}, Time spacing: {round(planner.output_waypoint_dt*1e6)}us")
    waypoint_times = np.linspace(0, planner.total_time, planner.output_waypoint_count)
    for i, (t, waypoint) in enumerate(zip(waypoint_times, planned_waypoints)):
        for j, pos in enumerate(waypoint):
            print(f"{joints_names[j]}: {pos:.4f} ", end='')
        print()
    
    # Show GUI
    planner.plot_results(trajectory_func, T_initial, apply_ik=True)
