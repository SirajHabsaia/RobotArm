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
                 adaptive_sampling: bool = True,
                 verbose_logging: bool = False):
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
        self.verbose_logging = verbose_logging
        
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
                       trajectory_func: Optional[Callable] = None,
                       T_duration: Optional[float] = None,
                       gripper_actions: Optional[Dict[float, float]] = None,
                       waypoint_list: Optional[List[List[float]]] = None,
                       use_waypoint_list: bool = False) -> List[Tuple[float, ...]]:
        """
        Plan time-optimal trajectory with gripper control.
        
        Supports two input modes:
        1. Trajectory function mode (default): Samples from continuous trajectory function
        2. Waypoint list mode: Creates linear interpolation in Cartesian space from waypoints,
           then samples from this interpolation before converting to joint angles
        
        Args:
            trajectory_func: Function f(t) -> [x, y, z] returning Cartesian coordinates (required if use_waypoint_list=False)
            T_duration: Duration of input trajectory (required if use_waypoint_list=False)
            gripper_actions: Dict mapping times to gripper angles. 
                            - In trajectory mode: keys are time values in [0, T_duration]
                            - In waypoint list mode: keys are normalized times in [0, 1]
            waypoint_list: List of [x, y, z] waypoints (required if use_waypoint_list=True)
            use_waypoint_list: If True, use waypoint_list with linear interpolation; if False, use trajectory_func (default: False)
            
        Returns:
            List of waypoints: (theta, alpha, beta, mu, gripper)
        """
        if gripper_actions is None:
            gripper_actions = self.gripper_actions
        
        # Validate inputs based on mode
        if use_waypoint_list:
            if waypoint_list is None:
                raise ValueError("waypoint_list must be provided when use_waypoint_list=True")
            
            # Create linear interpolation in Cartesian space from waypoint list
            input_waypoints = np.array(waypoint_list)
            n_input_waypoints = len(input_waypoints)
            
            if self.verbose_logging:
                print(f"Waypoint list mode: Creating Cartesian interpolation from {n_input_waypoints} input waypoints")
            
            # Create normalized parameter for waypoints (0 to 1)
            waypoint_params = np.linspace(0, 1, n_input_waypoints)
            
            # Create linear interpolation functions for x, y, z
            from scipy.interpolate import interp1d
            interp_x = interp1d(waypoint_params, input_waypoints[:, 0], kind='linear')
            interp_y = interp1d(waypoint_params, input_waypoints[:, 1], kind='linear')
            interp_z = interp1d(waypoint_params, input_waypoints[:, 2], kind='linear')
            
            # Create trajectory function from interpolation
            def interpolated_trajectory(t):
                """Linear interpolation through waypoints in Cartesian space."""
                # t is normalized parameter [0, 1]
                return [interp_x(t), interp_y(t), interp_z(t)]
            
            # Now sample from this interpolated trajectory (uniform sampling)
            # Use uniform sampling since linear interpolation doesn't have acceleration patterns
            t_waypoints = np.linspace(0, 1, self.n_waypoints_input)
            cartesian_waypoints = np.array([interpolated_trajectory(t) for t in t_waypoints])
            
            # Store for plotting and gripper mapping
            self.t_waypoints_input = t_waypoints
            self.interpolated_trajectory_func = interpolated_trajectory
            self.T_interpolation = 1.0  # Normalized duration
            
            # Map gripper actions from waypoint indices to normalized time
            if gripper_actions:
                gripper_actions_mapped = {}
                for waypoint_idx, gripper_angle in gripper_actions.items():
                    if 0 <= waypoint_idx < n_input_waypoints:
                        # Convert waypoint index to normalized time parameter
                        t_normalized = waypoint_params[int(waypoint_idx)]
                        gripper_actions_mapped[t_normalized] = gripper_angle
                        if self.verbose_logging:
                            print(f"Gripper action {gripper_angle}° at input waypoint {waypoint_idx} → t={t_normalized:.4f}")
                gripper_actions = gripper_actions_mapped
            
            if self.verbose_logging:
                print(f"Sampling {self.n_waypoints_input} waypoints from Cartesian interpolation")
        else:
            if trajectory_func is None or T_duration is None:
                raise ValueError("trajectory_func and T_duration must be provided when use_waypoint_list=False")
            
            # Sample waypoints from original trajectory (adaptive or uniform)
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
                
                if self.verbose_logging:
                    print(f"Adaptive sampling: {self.n_waypoints_input} waypoints based on acceleration magnitude")
            else:
                # Uniform time sampling
                t_waypoints = np.linspace(0, T_duration, self.n_waypoints_input)
                if self.verbose_logging:
                    print(f"Uniform sampling: {self.n_waypoints_input} waypoints evenly spaced in time")
            
            self.t_waypoints_input = t_waypoints
            cartesian_waypoints = np.array([trajectory_func(t) for t in t_waypoints])
            
            # Store trajectory function for plotting
            self.interpolated_trajectory_func = None
            self.T_interpolation = None
        
        # Store input mode information for plotting
        self.use_waypoint_list_mode = use_waypoint_list
        self.input_cartesian_waypoints = np.array(waypoint_list) if use_waypoint_list else None
        
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
        
        # Create path for TOPPRA (4 joints: theta, alpha, beta, mu)
        ss = np.linspace(0, 1, n_waypoints)
        path = toppra.SplineInterpolator(ss, waypoints)
        
        # Map gripper actions to path parameter s
        gripper_s_map = {}  # Maps path parameter s to gripper angle
        if gripper_actions:
            # Both modes now use time-based gripper actions (normalized time for waypoint list mode)
            # Get the appropriate time duration
            time_duration = self.T_interpolation if use_waypoint_list else T_duration
            
            for t_action, gripper_angle in gripper_actions.items():
                if t_action < 0 or t_action > time_duration:
                    if self.verbose_logging:
                        print(f"Warning: Gripper action at t={t_action} outside trajectory duration")
                    continue
                # Convert time to path parameter s using linear interpolation
                s_action = np.interp(t_action, self.t_waypoints_input, ss)
                gripper_s_map[s_action] = gripper_angle
                if self.verbose_logging:
                    print(f"Gripper action {gripper_angle}° mapped to path parameter s={s_action:.4f} (t_orig={t_action:.3f}s)")
        
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
        
        # Map gripper actions to dense trajectory using path parameter
        self.gripper_dense = np.full(len(t_dense), -1.0)
        gripper_optimized_times = {}
        gripper_dense = self.gripper_dense
        
        if gripper_s_map:
            # For each gripper action, evaluate the path at its s parameter
            # then find that exact configuration in the dense trajectory
            for s_action, gripper_angle in gripper_s_map.items():
                # Evaluate the path (spline) at this s parameter to get joint configuration
                target_joints = path.eval(s_action)  # Returns [theta, alpha, beta, mu]
                target_position = target_joints[:3]  # Use only theta, alpha, beta
                
                # Find this configuration in the optimized dense trajectory
                distances = np.linalg.norm(q_dense[:, :3] - target_position, axis=1)
                closest_idx = np.argmin(distances)
                min_distance = distances[closest_idx]
                
                # Assign gripper action
                gripper_dense[closest_idx] = gripper_angle
                gripper_optimized_times[t_dense[closest_idx]] = gripper_angle
                
                if self.verbose_logging:
                    print(f"Gripper {gripper_angle}° assigned at t={t_dense[closest_idx]:.3f}s (idx={closest_idx}, dist={min_distance:.4f})")
        
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
                if self.verbose_logging:
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
        
        if self.verbose_logging:
            print(f"Total time: {self.total_time:.3f}s")
            print(f"Output: {self.output_waypoint_count} waypoints @ {self.output_waypoint_dt*1000:.1f}ms spacing")
        
        return self.planned_waypoints
    
    def plot_results(self, trajectory_func=None, T_duration=None):
        """Plot planned trajectory results.
        
        Args:
            trajectory_func: Original trajectory function f(t) -> [x, y, z] (only used in trajectory mode)
            T_duration: Duration of original trajectory (only used in trajectory mode)
        """
        if self.q_dense is None:
            raise ValueError("No trajectory planned yet. Call plan_trajectory() first.")
        
        joints_names = ['theta', 'alpha', 'beta']
        cartesian_labels = ['x', 'y', 'z']
        
        # Determine if we have input data to plot
        has_trajectory_input = (trajectory_func is not None and T_duration is not None)
        has_waypoint_input = (self.use_waypoint_list_mode and self.input_cartesian_waypoints is not None)
        
        # Create figure with 4 columns, 3 rows (theta, alpha, beta only)
        fig, axes = plt.subplots(3, 4, figsize=(20, 10))
        
        for j in range(3):  # Only theta, alpha, beta (not mu)
            # Column 0: Original Cartesian trajectory or waypoints
            if has_trajectory_input:
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
            elif has_waypoint_input:
                # Plot interpolated trajectory with original waypoints
                if self.interpolated_trajectory_func is not None:
                    # Plot smooth interpolation
                    t_interp = np.linspace(0, 1, 501)
                    cartesian_interp = np.array([self.interpolated_trajectory_func(t) for t in t_interp])
                    axes[j, 0].plot(t_interp, cartesian_interp[:, j], 'b-', linewidth=1.5, label='Interpolation')
                    
                    # Plot sampled waypoints
                    cartesian_waypoints = np.array([self.interpolated_trajectory_func(t) for t in self.t_waypoints_input])
                    axes[j, 0].scatter(self.t_waypoints_input, cartesian_waypoints[:, j], color='r', s=5, label='Sampled')
                    
                    # Plot original input waypoints as larger markers
                    n_input = len(self.input_cartesian_waypoints)
                    waypoint_params = np.linspace(0, 1, n_input)
                    axes[j, 0].scatter(waypoint_params, self.input_cartesian_waypoints[:, j], color='orange', s=30, marker='s', zorder=10, label='Input WPs')
                    
                    # Plot gripper actions as green dots
                    if self.gripper_actions:
                        for t_action, gripper_angle in self.gripper_actions.items():
                            gripper_pos = self.interpolated_trajectory_func(t_action)[j]
                            axes[j, 0].scatter(t_action, gripper_pos, color='green', s=50, marker='o', zorder=10, label='Gripper' if (j == 0 and t_action == list(self.gripper_actions.keys())[0]) else '')
                    
                    axes[j, 0].set_title(f"{cartesian_labels[j]} Cartesian Interpolation")
                    axes[j, 0].set_ylabel(f"{cartesian_labels[j]} (mm)")
                    axes[j, 0].set_xlabel("Normalized Time")
                    if j == 0:
                        axes[j, 0].legend(loc='best', fontsize=8)
            else:
                axes[j, 0].set_title(f"Cartesian {cartesian_labels[j]} (N/A)")
                axes[j, 0].text(0.5, 0.5, 'No data', ha='center', va='center', 
                               transform=axes[j, 0].transAxes)
            
            # Column 1: Original joint trajectory (after IK)
            if has_trajectory_input and self.inverse_kinematics is not None:
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
            elif has_waypoint_input and self.inverse_kinematics is not None:
                # Apply IK to interpolated trajectory
                if self.interpolated_trajectory_func is not None:
                    # Plot smooth joint trajectory from interpolation
                    t_interp = np.linspace(0, 1, 501)
                    joint_interp = []
                    for t in t_interp:
                        cart_pos = self.interpolated_trajectory_func(t)
                        mu = self.mu_func(cart_pos[0], cart_pos[1], cart_pos[2])
                        joints = self.inverse_kinematics(cart_pos[0], cart_pos[1], cart_pos[2], mu)
                        joint_interp.append(joints[:3])
                    joint_interp = np.array(joint_interp)
                    
                    axes[j, 1].plot(t_interp, joint_interp[:, j], 'g-', linewidth=1.5, label='Interpolation')
                    
                    # Plot sampled waypoints
                    joint_sampled = []
                    for t in self.t_waypoints_input:
                        cart_pos = self.interpolated_trajectory_func(t)
                        mu = self.mu_func(cart_pos[0], cart_pos[1], cart_pos[2])
                        joints = self.inverse_kinematics(cart_pos[0], cart_pos[1], cart_pos[2], mu)
                        joint_sampled.append(joints[:3])
                    joint_sampled = np.array(joint_sampled)
                    axes[j, 1].scatter(self.t_waypoints_input, joint_sampled[:, j], color='r', s=5, label='Sampled')
                    
                    # Plot original input waypoints
                    joint_input = []
                    n_input = len(self.input_cartesian_waypoints)
                    waypoint_params = np.linspace(0, 1, n_input)
                    for pos in self.input_cartesian_waypoints:
                        mu = self.mu_func(pos[0], pos[1], pos[2])
                        joints = self.inverse_kinematics(pos[0], pos[1], pos[2], mu)
                        joint_input.append(joints[:3])
                    joint_input = np.array(joint_input)
                    axes[j, 1].scatter(waypoint_params, joint_input[:, j], color='orange', s=30, marker='s', zorder=10, label='Input WPs')
                    
                    # Plot gripper actions
                    if self.gripper_actions:
                        for t_action, gripper_angle in self.gripper_actions.items():
                            cart_pos = self.interpolated_trajectory_func(t_action)
                            mu = self.mu_func(cart_pos[0], cart_pos[1], cart_pos[2])
                            joints = self.inverse_kinematics(cart_pos[0], cart_pos[1], cart_pos[2], mu)
                            axes[j, 1].scatter(t_action, joints[j], color='green', s=50, marker='o', zorder=10, label='Gripper' if (j == 0 and t_action == list(self.gripper_actions.keys())[0]) else '')
                    
                    axes[j, 1].set_title(f"{joints_names[j]} Interpolated (IK)")
                    axes[j, 1].set_ylabel(f"{joints_names[j]} (deg)")
                    axes[j, 1].set_xlabel("Normalized Time")
                    if j == 0:
                        axes[j, 1].legend(loc='best', fontsize=8)
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
    joints_max_speeds = np.array([20.0, 15.0, 15.0])  # deg/s
    joints_max_accel = np.array([60.0, 20.0, 20.0])   # deg/s^2
    
    # Mu function parameters
    Rmin = 250
    Rmax = 500
    mumin = -90.0
    mumax = -45.0

    # Piece box coordinates (for pick & place with existing piece)
    xbox = 340.0
    ybox = -250.0
    zbox = 110.0
    
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
    
    # ========================================================================
    # TRAJECTORY EXAMPLES
    # ========================================================================
    
    # --- Example 1: Linear trajectory ---
    def linear_trajectory(t, T_total=3.0):
        """Straight line from start to end position."""
        s = t / T_total  # Normalized time [0, 1]
        x_start, y_start, z_start = 250, 0, 100
        x_end, y_end, z_end = 400, 200, 100
        
        x = x_start + (x_end - x_start) * s
        y = y_start + (y_end - y_start) * s
        z = z_start + (z_end - z_start) * s
        return [x, y, z]
    
    # --- Example 2: Circular trajectory ---
    def circular_trajectory(t, T_total=5.0):
        """Circle in XY plane at constant Z."""
        s = t / T_total  # Normalized time [0, 1]
        center_x, center_y, center_z = 350, 0, 50
        radius = 100
        angle = 2 * np.pi * s  # Full circle
        
        x = center_x + radius * np.cos(angle)
        y = center_y + radius * np.sin(angle)
        z = center_z
        return [x, y, z]
    
    # --- Example 3: Square trajectory ---
    def square_trajectory(t, T_total=8.0):
        """Square path in XY plane at constant Z.
        
        Creates a square with 4 equal sides, moving counter-clockwise:
        - Segment 0 (t=0 to T/4): Bottom edge, left to right
        - Segment 1 (t=T/4 to T/2): Right edge, bottom to top
        - Segment 2 (t=T/2 to 3T/4): Top edge, right to left
        - Segment 3 (t=3T/4 to T): Left edge, top to bottom
        """
        s = t / T_total  # Normalized time [0, 1]
        center_x, center_y, center_z = (203+470)/2, 0, 10
        side_length = 470 - 203
        half_side = side_length / 2
        
        # Divide time into 4 segments (one per side)
        segment = int(s * 4)
        segment = min(segment, 3)  # Clamp to avoid index error at t=T_total
        local_s = (s * 4) - segment  # Progress within current segment [0, 1]
        
        if segment == 0:  # Bottom edge (left to right)
            x = center_x - half_side + side_length * local_s
            y = center_y - half_side
        elif segment == 1:  # Right edge (bottom to top)
            x = center_x + half_side
            y = center_y - half_side + side_length * local_s
        elif segment == 2:  # Top edge (right to left)
            x = center_x + half_side - side_length * local_s
            y = center_y + half_side
        else:  # Left edge (top to bottom)
            x = center_x - half_side
            y = center_y + half_side - side_length * local_s
        
        z = center_z
        return [x, y, z]
    
    # --- Example 4 & 5: Pick & Place trajectories (using ellipses) ---
    
    # Ellipse primitives for smooth pick & place motions
    def quarter_ellipse(s, xi, yi, zi, xf, yf, zf, n=3):
        """Quarter ellipse from (xi, yi, zi) to (xf, yf, zf)."""
        s = 1-(1-s)**n if s>=0 else -1+(1+s)**n
        return [
            xi + (xf - xi) * s,
            yi + (yf - yi) * s,
            zf + (zi - zf) * (1 - abs(s)**n) ** (1/n)
        ]
    
    def semi_ellipse(s, xi, yi, zi, xf, yf, zm, n=3):
        """Semi-ellipse arc from (xi, yi, zi) to (xf, yf, zi) with max height zm."""
        s = s-1
        return quarter_ellipse(s, (xi+xf)/2, (yi+yf)/2, zm, xf, yf, zi, n=n)
    
    def pick_and_place_no_existing(t, xi=167, yi=0, zi=0, xp=203, yp=-132, zp=20, 
                                   xg=470, yg=-132, zm=-50, n=3):
        """Pick & place: home -> pick piece -> place piece -> home.
        
        Timeline:
        - t=0 to 1: Home to piece location (quarter ellipse down)
        - t=1 to 3: Piece location to goal (semi-ellipse arc)
        - t=3 to 4: Goal to home (quarter ellipse up)
        """
        s = t
        if s <= 1: 
            return quarter_ellipse(s, xi, yi, zi, xp, yp, zp, n=n)
        if s <= 3: 
            return semi_ellipse(s-1, xp, yp, zp, xg, yg, zm, n=n)
        return quarter_ellipse(1-(s-3), xi, yi, zi, xg, yg, zp, n=n)
    
    def pick_and_place_with_existing(t, xi=167, yi=0, zi=0, xp=203, yp=-132, zp=20,
                                    xg=470, yg=-132, zm=-50, n=3):
        """Pick & place with existing piece removal: home -> goal -> box -> piece -> goal -> home.
        
        Timeline:
        - t=0 to 1: Home to goal (to remove existing piece)
        - t=1 to 2: Goal to box (discard existing piece)
        - t=2 to 3: Box to piece location (pick new piece)
        - t=3 to 5: Piece to goal (place new piece)
        - t=5 to 6: Goal to home
        """
        s = t
        if s <= 1: 
            return quarter_ellipse(s, xi, yi, zi, xg, yg, zp, n=n)
        if s <= 2: 
            return quarter_ellipse(1-(s-1), xbox, ybox, zbox, xg, yg, zp, n=n)
        if s <= 3: 
            return quarter_ellipse(s-2, xbox, ybox, zbox, xp, yp, zp, n=n)
        if s <= 5: 
            return semi_ellipse(s-3, xp, yp, zp, xg, yg, zm, n=n)
        return quarter_ellipse(1-(s-5), xi, yi, zi, xg, yg, zp, n=n)
    
    # Gripper actions for pick & place trajectories
    gripper_actions_no_existing = {
        0.0: 40.0,   # Start with gripper open
        1.0: 82.0,   # Close gripper (pick piece)
        3.0: 40.0,   # Open gripper (place piece)
    }
    
    gripper_actions_with_existing = {
        0.0: 40.0,   # Start with gripper open
        1.0: 90.0,   # Close gripper (grab existing piece)
        2.0: 40.0,   # Open gripper (drop in box)
        3.0: 90.0,   # Close gripper (pick new piece)
        5.0: 40.0,   # Open gripper (place piece)
    }
    
    # ========================================================================
    # SELECT TRAJECTORY TO RUN
    # ========================================================================
    
    
    # trajectory_func = lambda t: linear_trajectory(t, T_total=3.0)
    # T_duration = 3.0
    # gripper_actions = None
    
    # trajectory_func = lambda t: circular_trajectory(t, T_total=5.0)
    # T_duration = 5.0
    # gripper_actions = None
    
    # trajectory_func = lambda t: square_trajectory(t, T_total=8.0)
    # T_duration = 8.0
    # gripper_actions = None

    # Cool curve
    # trajectory_func = lambda t: [
    #     400+40.0 * np.sin(5.0 * 2*np.pi*t),
    #     50.0 * np.cos(3.0 * 2*np.pi*t),
    #     20
    # ]
    # T_duration = 1.0
    # gripper_actions = None
    
    # trajectory_func = lambda t: pick_and_place_no_existing(t,
    #                                                        xi=100, yi=0, zi=-20, 
    #                                                        xp=203, yp=-132, zp=-125, 
    #                                                        xg=470, yg=132, zm=-50,
    #                                                        n=3)
    # T_duration = 4.0
    # gripper_actions = gripper_actions_no_existing
    
    # trajectory_func = lambda t: pick_and_place_with_existing(t, xi=167, yi=0, zi=0,
    #                                                          xp=203, yp=-132, zp=-132,
    #                                                          xg=470, yg=-132, zm=-50, n=3)
    # T_duration = 6.0
    # gripper_actions = gripper_actions_with_existing

    #define waypoints
    waypoints = [
        [499.7, 56.5, 20],
        [482.9, 16.2, 20],
        [440.6, 13.2, 20],
        [472.9, -13.8, 20],
        [463.2, -56.2, 20],
        [499.7, -33.5, 20],
        [536.5, -56.2, 20],
        [526.5, -14.7, 20],
        [559.1, 12.9, 20],
        [557.1, 14.1, 20],
        [516.5, 16.8, 20],
        [500.0, 56.5, 20]
    ]
    
    # Gripper actions for waypoint list mode (using normalized time 0-1)
    # For example, gripper action at 25% through the interpolation (between waypoints 3 and 4)
    # and at 75% through (between waypoints 9 and 10)
    gripper_actions_waypoint_mode = {
        0.25: 82.0,  # Close gripper at 25% through trajectory
        0.75: 40.0   # Open gripper at 75% through trajectory
    }
    
    # ========================================================================
    # RUN TRAJECTORY PLANNER
    # ========================================================================
    
    # Create planner
    planner = TrajectoryPlanner(
        joints_max_speeds=joints_max_speeds,
        joints_max_accel=joints_max_accel,
        n_waypoints_input=200,
        dt_sample=1e-3,
        inverse_kinematics_func=ik_func,
        forward_kinematics_func=fk_func,
        # mu_func=mu_func,
        mu_func = lambda x,y,z: 0,
        gripper_actions=None,
        adaptive_sampling=False
    )
    
    # Plan trajectory
    print(f"\n{'='*60}")
    print(f"Planning trajectory...")
    print(f"{'='*60}")
    planned_waypoints = planner.plan_trajectory(waypoint_list=waypoints, use_waypoint_list=True)
    
    # Print Arduino command format
    print(f"\n{'='*60}")
    print("Generated Waypoints (Arduino format)")
    print(f"{'='*60}")
    time_us = round(planner.output_waypoint_dt * 1e6)
    output_parts = [f"wn{planner.output_waypoint_count}d{time_us}"]
    
    for waypoint in planned_waypoints:
        theta, alpha, beta, mu, gripper = waypoint
        waypoint_str = f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}"
        output_parts.append(waypoint_str)
    
    output = ",".join(output_parts)
    print(output)
    print(f"{'='*60}\n")
    
    # Show plots (no trajectory_func needed for waypoint list mode)
    planner.plot_results()
