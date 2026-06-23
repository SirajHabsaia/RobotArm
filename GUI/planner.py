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
                 n_waypoints_input: int = 500,
                 dt_sample: float = 1e-3,
                 inverse_kinematics_func: Optional[Callable] = None,
                 forward_kinematics_func: Optional[Callable] = None,
                 mu_func: Optional[Callable] = None,
                 gripper_actions: Optional[Dict[float, float]] = None,
                 adaptive_sampling: bool = True,
                 max_waypoint_count: int = 100,
                 min_waypoint_dt: float = 0.02,
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
            max_waypoint_count: Maximum number of output waypoints (default: 100)
            min_waypoint_dt: Minimum time spacing between output waypoints in seconds (default: 0.02 = 20ms)
            verbose_logging: If True, print detailed planning information
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
        self.max_waypoint_count = max_waypoint_count
        self.min_waypoint_dt = min_waypoint_dt
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
            
            # Map gripper actions from normalized time (if provided)
            if gripper_actions:
                gripper_actions_mapped = {}
                for t_norm, gripper_angle in gripper_actions.items():
                    if t_norm < 0 or t_norm > 1:
                        if self.verbose_logging:
                            print(f"Warning: Gripper action at t={t_norm} outside normalized range [0, 1]")
                        continue
                    gripper_actions_mapped[t_norm] = gripper_angle
                gripper_actions = gripper_actions_mapped
            
            if self.verbose_logging:
                print(f"Sampling {self.n_waypoints_input} waypoints from Cartesian interpolation")
        else:
            if trajectory_func is None or T_duration is None:
                raise ValueError("trajectory_func and T_duration must be provided when use_waypoint_list=False")
            
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
        
        # --- Deterministic gripper-action timing ------------------------------
        # TOPPRA computes the path time-parameterization s(t). The parametrizer
        # exposes it directly: ``_ss`` are the path parameters (in [0, 1]) and
        # ``_ts`` the matching optimized times, both monotonic. Each gripper
        # action is already mapped to a path parameter s_action, so its optimized
        # time is just the (unique) inverse s -> t via interpolation. This is
        # stable and exact, unlike searching for the nearest joint configuration
        # (which is ambiguous whenever the path revisits a similar pose, e.g. an
        # out-and-back arc or an oscillation).
        s_grid = np.asarray(getattr(jnt_traj, "_ss", []), dtype=float)
        t_grid = np.asarray(getattr(jnt_traj, "_ts", []), dtype=float)
        have_param = s_grid.size >= 2 and s_grid.size == t_grid.size

        # Output waypoint grid (uniform in optimized time)
        if self.total_time / self.min_waypoint_dt > self.max_waypoint_count:
            self.output_waypoint_count = self.max_waypoint_count
            self.output_waypoint_dt = self.total_time / self.max_waypoint_count
        else:
            self.output_waypoint_dt = self.min_waypoint_dt
            self.output_waypoint_count = int(np.ceil(self.total_time / self.min_waypoint_dt)) + 1

        waypoint_times = np.linspace(0, self.total_time, self.output_waypoint_count)

        # Map each gripper action: path parameter s -> optimized time -> waypoint.
        self.gripper_dense = np.full(len(t_dense), -1.0)
        gripper_dense = self.gripper_dense
        output_gripper_map = {}

        if gripper_s_map and not have_param and self.verbose_logging:
            print("Warning: TOPPRA parameterization unavailable; "
                  "falling back to nearest-configuration gripper timing.")

        for s_action, gripper_angle in gripper_s_map.items():
            if have_param:
                # Deterministic: invert the monotonic s(t) for the exact time.
                t_opt = float(np.interp(s_action, s_grid, t_grid))
            else:
                # Fallback (older/other TOPPRA): nearest configuration in time.
                target_position = path.eval(s_action)[:3]
                distances = np.linalg.norm(q_dense[:, :3] - target_position, axis=1)
                t_opt = float(t_dense[int(np.argmin(distances))])

            # Map to the nearest output waypoint (for the Arduino command)
            out_idx = int(np.argmin(np.abs(waypoint_times - t_opt)))
            output_gripper_map[out_idx] = gripper_angle

            # Mark the dense trajectory too (used by plot_results)
            dense_idx = min(int(np.searchsorted(t_dense, t_opt)), len(t_dense) - 1)
            gripper_dense[dense_idx] = gripper_angle

            if self.verbose_logging:
                print(f"Gripper {gripper_angle}° at s={s_action:.4f} -> t={t_opt:.3f}s "
                      f"-> output waypoint {out_idx} (t={waypoint_times[out_idx]:.3f}s)")

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
    
    def get_arduino_command(self) -> str:
        """
        Generate Arduino command string from planned waypoints.
        
        Returns:
            Command string in format: "wn{count}d{time_us},t{theta}a{alpha}b{beta}m{mu}g{gripper},..."
        """
        if not self.planned_waypoints:
            raise ValueError("No trajectory planned yet. Call plan_trajectory() first.")
        
        time_us = round(self.output_waypoint_dt * 1e6)
        output_parts = [f"wn{self.output_waypoint_count}d{time_us}"]
        
        for waypoint in self.planned_waypoints:
            theta, alpha, beta, mu, gripper = waypoint
            waypoint_str = f"t{theta:.1f}a{alpha:.1f}b{beta:.1f}m{np.rad2deg(mu):.1f}g{gripper:.1f}"
            output_parts.append(waypoint_str)
        
        return ",".join(output_parts)
    
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
                # Plot input waypoints and interpolation
                waypoint_indices = np.arange(len(self.input_cartesian_waypoints))
                
                # Normalize time axis proportionally to waypoint indices
                axes[j, 0].scatter(waypoint_indices, self.input_cartesian_waypoints[:, j], 
                                 color='violet', s=5, marker='o', zorder=10, label='Input waypoints' if j == 0 else '')
                axes[j, 0].plot(waypoint_indices, self.input_cartesian_waypoints[:, j], 
                               'r--', alpha=0.5, linewidth=1)
                
                # Plot interpolation if available
                if self.interpolated_trajectory_func is not None:
                    t_interp = np.linspace(0, 1, 501)
                    cartesian_interp = np.array([self.interpolated_trajectory_func(t) for t in t_interp])
                    # Map normalized time to waypoint indices for x-axis
                    waypoint_scale = len(self.input_cartesian_waypoints) - 1
                    x_axis = t_interp * waypoint_scale
                    axes[j, 0].plot(x_axis, cartesian_interp[:, j], 'b-', label='Linear interpolation' if j == 0 else '')
                
                axes[j, 0].set_title(f"{cartesian_labels[j]} Cartesian waypoints")
                axes[j, 0].set_ylabel(f"{cartesian_labels[j]} (mm)")
                axes[j, 0].set_xlabel('Waypoint index')
                if j == 0:
                    axes[j, 0].legend(loc='best')
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
                # Plot joint space from input waypoints
                waypoint_indices = np.arange(len(self.input_cartesian_waypoints))
                
                # Apply IK to input waypoints
                joint_waypoints_input = []
                for pos in self.input_cartesian_waypoints:
                    mu = self.mu_func(pos[0], pos[1], pos[2])
                    joints = self.inverse_kinematics(pos[0], pos[1], pos[2], mu)
                    joint_waypoints_input.append(joints[:3])
                joint_waypoints_input = np.array(joint_waypoints_input)
                
                axes[j, 1].scatter(waypoint_indices, joint_waypoints_input[:, j], 
                                 color='violet', s=5, marker='o', zorder=10, label='Input waypoints' if j == 0 else '')
                axes[j, 1].plot(waypoint_indices, joint_waypoints_input[:, j], 
                               'r--', alpha=0.5, linewidth=1)
                
                # Plot interpolated joint trajectory if available
                if self.interpolated_trajectory_func is not None:
                    t_interp = np.linspace(0, 1, 501)
                    joint_interp = []
                    for t in t_interp:
                        cart_pos = self.interpolated_trajectory_func(t)
                        mu = self.mu_func(cart_pos[0], cart_pos[1], cart_pos[2])
                        joints = self.inverse_kinematics(cart_pos[0], cart_pos[1], cart_pos[2], mu)
                        joint_interp.append(joints[:3])
                    joint_interp = np.array(joint_interp)
                    
                    waypoint_scale = len(self.input_cartesian_waypoints) - 1
                    x_axis = t_interp * waypoint_scale
                    axes[j, 1].plot(x_axis, joint_interp[:, j], 'g-', label='Interpolation (IK)' if j == 0 else '')
                
                axes[j, 1].set_title(f"{joints_names[j]} waypoints (IK)")
                axes[j, 1].set_ylabel(f"{joints_names[j]} (deg)")
                axes[j, 1].set_xlabel('Waypoint index')
                if j == 0:
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
    # Minimal example: Circular trajectory
    from kinematics import inverse_kinematics, direct_kinematics
    
    # Joint constraints
    joints_max_speeds = np.array([20.0, 15.0, 15.0])  # deg/s
    joints_max_accel = np.array([60.0, 20.0, 20.0])   # deg/s^2
    
    # IK/FK wrappers
    ik_func = lambda x, y, z, mu: [angle * 180.0/np.pi for angle in inverse_kinematics(x, y, z, mu=mu)]
    
    # Circular trajectory function
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
    
    # Set up trajectory
    trajectory_func = lambda t: circular_trajectory(t, T_total=5.0)
    T_duration = 5.0
    
    # Create planner
    planner = TrajectoryPlanner(
        joints_max_speeds=joints_max_speeds,
        joints_max_accel=joints_max_accel,
        n_waypoints_input=100,
        dt_sample=1e-3,
        inverse_kinematics_func=ik_func,
        mu_func=lambda x,y,z: 0,
        adaptive_sampling=False
    )
    
    # Plan trajectory
    print(f"\n{'='*60}")
    print(f"Planning trajectory...")
    print(f"{'='*60}")
    planned_waypoints = planner.plan_trajectory(trajectory_func, T_duration)
    
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
    
    # Show plots
    planner.plot_results(trajectory_func, T_duration)

