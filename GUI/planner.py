import numpy as np
import matplotlib.pyplot as plt
from typing import Callable, List, Tuple, Optional, Dict
import toppra
import toppra.constraint as constraint
import toppra.algorithm as algo


class TrajectoryPlanner:
    """Time-optimal trajectory planner for robotic arm motion with gripper control.
    
    Treats mu as a 4th pseudo-joint with very loose constraints, allowing TOPPRA
    to optimize time while respecting actual joint limits on theta, alpha, beta.
    """
    
    def __init__(self, 
                 joints_max_speeds: np.ndarray,  # [theta, alpha, beta] max speeds
                 joints_max_accel: np.ndarray,   # [theta, alpha, beta] max accels
                 n_waypoints_input: int = 100,
                 dt_sample: float = 1e-3,
                 inverse_kinematics_func: Optional[Callable] = None,
                 forward_kinematics_func: Optional[Callable] = None,
                 mu_func: Optional[Callable] = None,
                 gripper_actions: Optional[Dict[float, float]] = None,
                 adaptive_sampling: bool = True):
        """
        Initialize trajectory planner.
        
        Args:
            joints_max_speeds: Max velocities for [theta, alpha, beta] (deg/s)
            joints_max_accel: Max accelerations for [theta, alpha, beta] (deg/s^2)
            n_waypoints_input: Number of waypoints to sample from input trajectory
            dt_sample: Time step for dense trajectory reconstruction
            inverse_kinematics_func: Function(x, y, z, mu) -> [theta, alpha, beta, gamma]
            forward_kinematics_func: Function(theta, alpha, beta, gamma) -> [x, y, z]
            mu_func: Function(x, y, z) -> mu to compute end-effector orientation
            gripper_actions: Dict mapping original trajectory times to gripper angles (degrees)
            adaptive_sampling: If True, distribute waypoints based on trajectory acceleration magnitude
        """
        self.joints_max_speeds = np.array(joints_max_speeds)
        self.joints_max_accel = np.array(joints_max_accel)
        self.n_waypoints_input = n_waypoints_input
        self.dt_sample = dt_sample
        self.inverse_kinematics = inverse_kinematics_func
        self.forward_kinematics = forward_kinematics_func
        self.mu_func = mu_func if mu_func is not None else lambda x, y, z: 0.0
        self.gripper_actions = gripper_actions
        self.adaptive_sampling = adaptive_sampling
        
        # Results
        self.planned_waypoints = []
        self.total_time = 0.0
        self.output_waypoint_count = 0
        self.output_waypoint_dt = 0.0
        self.t_dense = None
        self.q_dense = None
        self.qdot_dense = None
        self.t_waypoints_input = None
        self.gripper_dense = None
        
    def plan_trajectory(self, 
                       trajectory_func: Callable,
                       T_duration: float,
                       gripper_actions: Optional[Dict[float, float]] = None) -> List[Tuple[float, ...]]:
        """
        Plan time-optimal trajectory with gripper control.
        
        Args:
            trajectory_func: Function f(t) -> [x, y, z] returning Cartesian coordinates
            T_duration: Duration of input trajectory
            gripper_actions: Optional dict mapping times to gripper angles (overrides init value)
            
        Returns:
            List of waypoints: (theta, alpha, beta, mu, gripper)
        """
        if gripper_actions is None:
            gripper_actions = self.gripper_actions
            
        # Sample waypoints from original trajectory (adaptive or uniform)
        if self.adaptive_sampling:
            # Sample trajectory densely to compute acceleration
            n_dense_samples = max(1000, self.n_waypoints_input * 10)
            t_dense_sample = np.linspace(0, T_duration, n_dense_samples)
            traj_dense = np.array([trajectory_func(t) for t in t_dense_sample])
            
            # Compute numerical derivatives
            dt = T_duration / (n_dense_samples - 1)
            velocity = np.gradient(traj_dense, dt, axis=0)
            acceleration = np.gradient(velocity, dt, axis=0)
            
            # Compute acceleration magnitude (plus small constant to avoid zeros)
            accel_mag = np.linalg.norm(acceleration, axis=1) + 1e-6
            
            # Create cumulative distribution for sampling (higher weight where acceleration is high)
            sampling_weight = accel_mag ** 0.6
            cumulative_weight = np.cumsum(sampling_weight)
            cumulative_weight = cumulative_weight / cumulative_weight[-1]  # Normalize to [0, 1]
            
            # Sample waypoint times from this distribution
            uniform_samples = np.linspace(0, 1, self.n_waypoints_input)
            t_waypoints = np.interp(uniform_samples, cumulative_weight, t_dense_sample)
            
            # Always include start and end points
            t_waypoints[0] = 0.0
            t_waypoints[-1] = T_duration
            
            print(f"Adaptive sampling: distributed {self.n_waypoints_input} waypoints based on acceleration")
        else:
            # Uniform time sampling
            t_waypoints = np.linspace(0, T_duration, self.n_waypoints_input)
            print(f"Uniform sampling: {self.n_waypoints_input} waypoints evenly spaced in time")
        
        self.t_waypoints_input = t_waypoints
        cartesian_waypoints = np.array([trajectory_func(t) for t in t_waypoints])
        
        # Apply inverse kinematics and compute mu for each waypoint
        joint_waypoints = []
        for cart_pos in cartesian_waypoints:
            x, y, z = cart_pos
            mu = self.mu_func(x, y, z)
            joints = self.inverse_kinematics(x, y, z, mu)  # Returns [theta, alpha, beta, gamma]
            # Store as [theta, alpha, beta, mu] - treating mu as 4th joint
            joint_waypoints.append([joints[0], joints[1], joints[2], mu])
        
        waypoints = np.array(joint_waypoints)
        n_waypoints = len(waypoints)
        
        # Map gripper actions to waypoint indices
        gripper_waypoint_map = {}  # Maps waypoint index to gripper angle
        if gripper_actions:
            for t_action, gripper_angle in gripper_actions.items():
                if t_action < 0 or t_action > T_duration:
                    print(f"Warning: Gripper action at t={t_action} outside trajectory duration")
                    continue
                # Find closest waypoint to this time
                idx = np.argmin(np.abs(t_waypoints - t_action))
                gripper_waypoint_map[idx] = gripper_angle
                print(f"Gripper action {gripper_angle}° mapped to waypoint {idx} (t={t_waypoints[idx]:.3f}s)")
        
        # Create path for TOPPRA (4 joints: theta, alpha, beta, mu)
        ss = np.linspace(0, 1, n_waypoints)
        path = toppra.SplineInterpolator(ss, waypoints)
        
        # Setup constraints: tight for theta/alpha/beta, loose for mu
        MU_LIMIT = 1000.0  # Very high limit for mu (practically infinite)
        vlim = np.array([
            [-self.joints_max_speeds[0], self.joints_max_speeds[0]],  # theta
            [-self.joints_max_speeds[1], self.joints_max_speeds[1]],  # alpha
            [-self.joints_max_speeds[2], self.joints_max_speeds[2]],  # beta
            [-MU_LIMIT, MU_LIMIT]  # mu (loose constraint)
        ])
        alim = np.array([
            [-self.joints_max_accel[0], self.joints_max_accel[0]],  # theta
            [-self.joints_max_accel[1], self.joints_max_accel[1]],  # alpha
            [-self.joints_max_accel[2], self.joints_max_accel[2]],  # beta
            [-MU_LIMIT, MU_LIMIT]  # mu (loose constraint)
        ])
        
        pc_vel = constraint.JointVelocityConstraint(vlim)
        pc_acc = constraint.JointAccelerationConstraint(alim)
        
        # Run TOPPRA
        instance = algo.TOPPRA([pc_vel, pc_acc], path, parametrizer="ParametrizeConstAccel")
        jnt_traj = instance.compute_trajectory()
        
        if jnt_traj is None:
            raise ValueError("TOPPRA failed to compute trajectory")
        
        # Get optimized trajectory
        self.total_time = jnt_traj.duration
        self.t_dense = np.arange(0.0, self.total_time + self.dt_sample/2.0, self.dt_sample)
        self.q_dense = jnt_traj(self.t_dense)  # Shape: (N, 4) - includes mu as 4th column
        self.qdot_dense = jnt_traj(self.t_dense, 1)  # First derivative
        
        t_dense = self.t_dense
        q_dense = self.q_dense
        
        # Map gripper actions to dense trajectory
        self.gripper_dense = np.full(len(t_dense), -1.0)
        gripper_optimized_times = {}
        gripper_dense = self.gripper_dense
        
        if gripper_waypoint_map:
            # For each waypoint with gripper action, find its position in dense trajectory
            for waypoint_idx, gripper_angle in gripper_waypoint_map.items():
                target_position = waypoints[waypoint_idx, :3]  # theta, alpha, beta only
                # Find closest point in optimized trajectory
                distances = np.linalg.norm(q_dense[:, :3] - target_position, axis=1)
                closest_idx = np.argmin(distances)
                gripper_dense[closest_idx] = gripper_angle
                gripper_optimized_times[t_dense[closest_idx]] = gripper_angle
                print(f"Gripper {gripper_angle}° assigned to optimized t={t_dense[closest_idx]:.3f}s")
        
        # Generate output waypoints
        min_waypoint_dt = 0.02  # 20ms minimum spacing
        max_waypoint_count = 100
        
        if self.total_time / min_waypoint_dt > max_waypoint_count:
            self.output_waypoint_count = max_waypoint_count
            self.output_waypoint_dt = self.total_time / max_waypoint_count
        else:
            self.output_waypoint_dt = min_waypoint_dt
            self.output_waypoint_count = int(np.ceil(self.total_time / min_waypoint_dt)) + 1
        
        waypoint_times = np.linspace(0, self.total_time, self.output_waypoint_count)
        
        # Map gripper actions to output waypoints
        output_gripper_map = {}
        if gripper_optimized_times:
            for t_opt, gripper_angle in gripper_optimized_times.items():
                closest_idx = np.argmin(np.abs(waypoint_times - t_opt))
                output_gripper_map[closest_idx] = gripper_angle
                print(f"Gripper {gripper_angle}° at output waypoint {closest_idx} (t={waypoint_times[closest_idx]:.3f}s)")
        
        # Generate output waypoints
        self.planned_waypoints = []
        for i, t in enumerate(waypoint_times):
            idx = np.searchsorted(t_dense, t)
            idx = min(idx, len(t_dense) - 1)
            
            # Get joint values: theta, alpha, beta, mu
            theta, alpha, beta, mu = q_dense[idx]
            
            # Get gripper value
            gripper = output_gripper_map.get(i, -1.0)
            
            # Store waypoint: (theta, alpha, beta, mu, gripper)
            self.planned_waypoints.append((theta, alpha, beta, mu, gripper))
        
        print(f"Total time: {self.total_time:.3f}s")
        print(f"Output: {self.output_waypoint_count} waypoints @ {self.output_waypoint_dt*1000:.1f}ms spacing")
        
        return self.planned_waypoints
    
    def plot_results(self, trajectory_func=None, T_duration=None):
        """Plot planned trajectory results.
        
        Args:
            trajectory_func: Original trajectory function f(t) -> [x, y, z]
            T_duration: Duration of original trajectory
        """
        if self.q_dense is None:
            raise ValueError("No trajectory planned yet. Call plan_trajectory() first.")
        
        joints_names = ['theta', 'alpha', 'beta']
        cartesian_labels = ['x', 'y', 'z']
        
        # Create figure with 4 columns, 3 rows (theta, alpha, beta only)
        fig, axes = plt.subplots(3, 4, figsize=(20, 10))
        
        for j in range(3):  # Only theta, alpha, beta (not mu)
            # Column 0: Original Cartesian trajectory
            if trajectory_func is not None and T_duration is not None:
                t_theory = np.linspace(0, T_duration, 501)
                cartesian_theory = np.array([trajectory_func(t) for t in t_theory])
                cartesian_waypoints = np.array([trajectory_func(t) for t in self.t_waypoints_input])
                
                axes[j, 0].plot(t_theory, cartesian_theory[:, j], 'b-')
                axes[j, 0].scatter(self.t_waypoints_input, cartesian_waypoints[:, j], color='r', s=5)
                # Plot gripper actions as green dots
                if self.gripper_actions:
                    gripper_times = list(self.gripper_actions.keys())
                    gripper_positions = [trajectory_func(t)[j] for t in gripper_times]
                    axes[j, 0].scatter(gripper_times, gripper_positions, color='green', s=50, marker='o', zorder=10, label='Gripper' if j == 0 else '')
                axes[j, 0].set_title(f"{cartesian_labels[j]} Cartesian original")
                axes[j, 0].set_ylabel(f"{cartesian_labels[j]} (mm)")
                if j == 0 and self.gripper_actions:
                    axes[j, 0].legend(loc='best')
            else:
                axes[j, 0].set_title(f"Cartesian {cartesian_labels[j]} (N/A)")
                axes[j, 0].text(0.5, 0.5, 'No data', ha='center', va='center', 
                               transform=axes[j, 0].transAxes)
            
            # Column 1: Original joint trajectory (after IK)
            if trajectory_func is not None and T_duration is not None and self.inverse_kinematics is not None:
                t_theory = np.linspace(0, T_duration, 501)
                cartesian_theory = np.array([trajectory_func(t) for t in t_theory])
                cartesian_waypoints = np.array([trajectory_func(t) for t in self.t_waypoints_input])
                
                # Apply IK to get joint space trajectory
                joint_theory = []
                for pos in cartesian_theory:
                    mu = self.mu_func(pos[0], pos[1], pos[2])
                    joints = self.inverse_kinematics(pos[0], pos[1], pos[2], mu)
                    joint_theory.append(joints[:3])  # theta, alpha, beta
                joint_theory = np.array(joint_theory)
                
                joint_waypoints = []
                for pos in cartesian_waypoints:
                    mu = self.mu_func(pos[0], pos[1], pos[2])
                    joints = self.inverse_kinematics(pos[0], pos[1], pos[2], mu)
                    joint_waypoints.append(joints[:3])
                joint_waypoints = np.array(joint_waypoints)
                
                axes[j, 1].plot(t_theory, joint_theory[:, j], 'g-')
                axes[j, 1].scatter(self.t_waypoints_input, joint_waypoints[:, j], color='r', s=5)
                # Plot gripper actions as green dots
                if self.gripper_actions:
                    gripper_times = list(self.gripper_actions.keys())
                    gripper_joint_positions = []
                    for t in gripper_times:
                        cart_pos = trajectory_func(t)
                        mu = self.mu_func(cart_pos[0], cart_pos[1], cart_pos[2])
                        joints = self.inverse_kinematics(cart_pos[0], cart_pos[1], cart_pos[2], mu)
                        gripper_joint_positions.append(joints[j])
                    axes[j, 1].scatter(gripper_times, gripper_joint_positions, color='green', s=50, marker='o', zorder=10, label='Gripper' if j == 0 else '')
                axes[j, 1].set_title(f"{joints_names[j]} original (IK)")
                axes[j, 1].set_ylabel(f"{joints_names[j]} (deg)")
                if j == 0 and self.gripper_actions:
                    axes[j, 1].legend(loc='best')
            else:
                axes[j, 1].set_title(f"{joints_names[j]} original (N/A)")
            
            # Column 2: Generated trajectory with waypoints
            axes[j, 2].plot(self.t_dense, self.q_dense[:, j], 'b-', linewidth=1.5)
            waypoints_pos = [wp[j] for wp in self.planned_waypoints]
            waypoint_times = np.linspace(0, self.total_time, self.output_waypoint_count)
            axes[j, 2].scatter(waypoint_times, waypoints_pos, color='red', s=5, zorder=5)
            # Plot gripper actions as green dots
            if self.gripper_dense is not None:
                gripper_indices = np.where(self.gripper_dense != -1.0)[0]
                if len(gripper_indices) > 0:
                    gripper_opt_times = self.t_dense[gripper_indices]
                    gripper_opt_positions = self.q_dense[gripper_indices, j]
                    axes[j, 2].scatter(gripper_opt_times, gripper_opt_positions, color='green', s=50, marker='o', zorder=10, label='Gripper' if j == 0 else '')
            axes[j, 2].set_title(f"{joints_names[j]} generated")
            axes[j, 2].set_ylabel(f"{joints_names[j]} (deg)")
            if j == 0 and self.gripper_dense is not None and np.any(self.gripper_dense != -1.0):
                axes[j, 2].legend(loc='best')
            
            # Column 3: Generated velocity
            axes[j, 3].plot(self.t_dense, self.qdot_dense[:, j], 'b-')
            axes[j, 3].axhline(self.joints_max_speeds[j], color='r', linestyle='--', linewidth=1, label='Max')
            axes[j, 3].axhline(-self.joints_max_speeds[j], color='r', linestyle='--', linewidth=1)
            axes[j, 3].set_title(f"{joints_names[j]} speed")
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
    # Example usage
    from kinematics import inverse_kinematics, direct_kinematics
    
    # Joint constraints
    joints_max_speeds = np.array([30.0, 15.0, 15.0])  # deg/s
    joints_max_accel = np.array([20.0, 10.0, 10.0])   # deg/s^2
    
    # Mu function parameters
    Rmin = 250
    Rmax = 500
    mumin = -90.0
    mumax = -45.0
    
    # Trajectory primitives
    def quarter_ellipse(s, xi, yi, zi, xf, yf, zf, n=3):
        s = 1-(1-s)**n if s>=0 else -1+(1+s)**n
        return [
            xi + (xf - xi) * s,
            yi + (yf - yi) * s,
            zf + (zi - zf) * (1 - abs(s)**n) ** (1/n)
        ]
    
    def semi_ellipse(s, xi, yi, zi, xf, yf, zm, n=3):
        s = s-1
        # s = s**(1/n) if s>=0 else -(-s)**(1/n)
        return quarter_ellipse(s, (xi+xf)/2, (yi+yf)/2, zm, xf, yf, zi, n=n)
    
    def move_piece(s, xi, yi, zi, xp, yp, zp, xg, yg, zm, n=3):
        if s <= 1: return quarter_ellipse(s, xi, yi, zi, xp, yp, zp, n=n)
        if s <= 3: return semi_ellipse(s-1, xp, yp, zp, xg, yg, zm, n=n)
        return quarter_ellipse(1-(s-3), xi, yi, zi, xg, yg, zp, n=n)
    
    # Trajectory function
    def trajectory_func(t):
        return move_piece(t, xi=167, yi=0, zi=0, xp=203, yp=-132, zp=-132, 
                         xg=470, yg=-132, zm=-50, n=3)
        # return semi_ellipse(t, xi=250, yi=0, zi=-100, xf=300, yf=0, zm=-50, n=3)
    
    T_initial = 4.0
    
    # IK/FK wrappers
    ik_func = lambda x, y, z, mu: [angle * 180.0/np.pi for angle in inverse_kinematics(x, y, z, mu=mu)]
    fk_func = lambda theta, alpha, beta, gamma: direct_kinematics(
        theta * np.pi/180.0, alpha * np.pi/180.0, beta * np.pi/180.0, gamma * np.pi/180.0
    )
    
    # Mu function
    def mu_func(x, y, z):
        r = np.sqrt(x**2 + y**2)
        if r < Rmin:
            mu_deg = mumin
        elif r > Rmax:
            mu_deg = mumax
        else:
            mu_deg = mumin + (mumax - mumin) * (r - Rmin) / (Rmax - Rmin)
        return mu_deg * np.pi / 180.0  # Return radians
    
    # Gripper actions
    gripper_actions = {
        0.0: 40.0,
        1.0: 85.0,
        3.0: 40.0
    }
    
    # Create planner
    planner = TrajectoryPlanner(
        joints_max_speeds=joints_max_speeds,
        joints_max_accel=joints_max_accel,
        n_waypoints_input=100,
        dt_sample=1e-3,
        inverse_kinematics_func=ik_func,
        forward_kinematics_func=fk_func,
        mu_func=mu_func,
        gripper_actions=gripper_actions,
        adaptive_sampling=False
    )
    
    # Plan trajectory
    planned_waypoints = planner.plan_trajectory(trajectory_func, T_initial)
    
    # Print Arduino command format
    print("\n=== Generated Waypoints ===")
    time_us = round(planner.output_waypoint_dt * 1e6)
    output_parts = [f"wn{planner.output_waypoint_count}d{time_us}"]
    
    for waypoint in planned_waypoints:
        theta, alpha, beta, mu, gripper = waypoint
        waypoint_str = f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}"
        output_parts.append(waypoint_str)
    
    output = ",".join(output_parts)
    print(output)
    
    # Show plots
    # planner.plot_results(trajectory_func, T_initial)
