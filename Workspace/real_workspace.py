import numpy as np
import matplotlib.pyplot as plt
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'GUI'))
from kinematics import inverse_kinematics, direct_kinematics  # type: ignore

l1 = 250
l2 = 200
l3 = 150
PI = np.pi

def is_reachable(x, z, mu=0):
    """
    Check if a point (x, z) is reachable by the robot.
    Returns True if inverse kinematics is valid, False otherwise.
    
    For the workspace in the plane theta=0, we set y=0.
    """
    x_adj = x - l3 * np.cos(mu)
    z_adj = z - l3 * np.sin(mu)
    r = np.sqrt(x_adj**2 + z_adj**2)
    if r > (l1 + l2) or r < abs(l1 - l2):
        return False
    arg_a = (-l2**2 + l1**2 + r**2) / (2 * l1 * r)
    arg_b = (l1**2 + l2**2 - r**2) / (2 * l1 * l2)
    if abs(arg_a) > 1 or abs(arg_b) > 1:
        return False
    # Calculate alpha and beta using the same formulas as in inverse_kinematics
    try:
        a = np.arccos(arg_a)
        b = np.arccos(arg_b)
        atn = np.arctan2(z_adj, x_adj)
        alpha = PI - a - b - atn
        beta = PI/2 - a - atn
        # Convert to degrees for comparison
        alpha_deg = np.degrees(alpha)
        beta_deg = np.degrees(beta)
        expr_deg = np.degrees(PI/2 + beta - alpha)
        if not (alpha_deg > -15):
            return False
        if not (beta_deg < 90):
            return False
        if not (expr_deg > 35):
            return False
    except Exception:
        return False
    return True

def generate_workspace_envelope(x_range, z_range, resolution=500):
    """
    Generate the workspace envelope by testing points in the x-z plane.
    
    Args:
        x_range: tuple (x_min, x_max)
        z_range: tuple (z_min, z_max)
        resolution: number of points to test in each dimension
    
    Returns:
        workspace_mask: 2D boolean array indicating reachable points
        X, Z: meshgrid arrays for plotting
    """
    x_vals = np.linspace(x_range[0], x_range[1], resolution)
    z_vals = np.linspace(z_range[0], z_range[1], resolution)
    
    X, Z = np.meshgrid(x_vals, z_vals)
    workspace_mask = np.zeros_like(X, dtype=bool)
    
    for i in range(resolution):
        for j in range(resolution):
            workspace_mask[i, j] = is_reachable(X[i, j], Z[i, j])
    
    return workspace_mask, X, Z

def find_boundary_points(mu, resolution=1000):
    """
    Find the exact boundary points of the workspace envelope for a given mu.
    Uses polar coordinates for more accurate boundary detection.
    """
    # Only consider angles that produce x > 0
    angles = np.linspace(-PI/2, PI/2, resolution)
    boundary_points = []
    
    for angle in angles:
        # Binary search for the maximum reachable distance at this angle
        r_min = 0
        r_max = l1 + l2 + l3 + 50  # Start with maximum possible reach
        
        while r_max - r_min > 0.1:  # Precision of 0.1 units
            r_mid = (r_min + r_max) / 2
            x = r_mid * np.cos(angle)
            z = r_mid * np.sin(angle)
            
            if is_reachable(x, z, mu):
                r_min = r_mid
            else:
                r_max = r_mid
        
        if r_min > 0:  # Valid boundary point found
            x = r_min * np.cos(angle)
            z = r_min * np.sin(angle)
            boundary_points.append([x, z])
    
    return np.array(boundary_points)

def visualize_workspace():
    """
    Visualize the robot workspace envelope in the x-z plane for all mu values from -90 to 90 degrees.
    """
    print("Generating workspace envelope for mu from -90° to 90°...")
    
    # Generate mu values from -90 to 90 degrees
    mu_values = np.linspace(np.radians(-90), np.radians(90), 20)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Collect all boundary points for all mu values
    all_points = []
    
    for i, mu in enumerate(mu_values):
        print(f"Finding boundary points for μ = {np.degrees(mu):.1f}°...")
        boundary_points = find_boundary_points(mu, resolution=300)
        
        if len(boundary_points) > 0:
            all_points.extend(boundary_points)
            # Plot each mu's boundary with different transparency
            alpha_val = 0.3 if i % 2 == 0 else 0.2
            ax.plot(boundary_points[:, 0], boundary_points[:, 1], 
                    '-', linewidth=1, alpha=alpha_val, color='blue')
    
    # Fill the overall workspace region
    if len(all_points) > 0:
        all_points = np.array(all_points)
        ax.fill(all_points[:, 0], all_points[:, 1], 
                color='lightblue', alpha=0.3, label='Espace atteint (μ: -90° à 90°)')
    
    # Add circles showing theoretical limits
    circle_outer = plt.Circle((0, 0), l1 + l2 + l3, 
                             color='red', fill=False, linestyle='--', 
                             linewidth=1.5, alpha=0.7, label=f'Limite ext (L1+L2+L3={l1+l2+l3})')
    circle_inner = plt.Circle((0, 0), abs(l1 - l2) - l3, 
                             color='orange', fill=False, linestyle='--', 
                             linewidth=1.5, alpha=0.7, label=f'Limite int')
    
    ax.add_patch(circle_outer)
    ax.add_patch(circle_inner)
    
    # Draw robot arm at a sample configuration (mu=0)
    x_sample, z_sample = 350, 200
    try:
        angles = inverse_kinematics(x_sample, 0, z_sample, l1=l1, l2=l2, l3=l3, mu=0)
        theta, alpha, beta, gamma = angles
        joint0 = np.array([0, 0])
        q1 = np.pi/2 - beta
        joint1 = np.array([l1 * np.cos(q1), l1 * np.sin(q1)])
        q2 = -alpha
        joint2 = joint1 + np.array([l2 * np.cos(q2), l2 * np.sin(q2)])
        q3 = gamma - alpha
        end_effector = joint2 + np.array([l3 * np.cos(q3), l3 * np.sin(q3)])
    except:
        alpha = np.pi/4
        beta = np.pi/6
        joint0 = np.array([0, 0])
        joint1 = joint0 + np.array([l1 * np.cos(alpha), l1 * np.sin(alpha)])
        joint2 = joint1 + np.array([l2 * np.cos(alpha + beta), l2 * np.sin(alpha + beta)])
        end_effector = joint2 + np.array([l3 * np.cos(alpha + beta), l3 * np.sin(alpha + beta)])
    
    ax.plot([joint0[0], joint1[0]], [joint0[1], joint1[1]], 
            'r-', linewidth=4, label=f'Link 1 (L={l1})', zorder=5)
    ax.plot([joint1[0], joint2[0]], [joint1[1], joint2[1]], 
            'g-', linewidth=4, label=f'Link 2 (L={l2})', zorder=5)
    ax.plot([joint2[0], end_effector[0]], [joint2[1], end_effector[1]], 
            'purple', linewidth=4, label=f'Link 3 (L={l3})', zorder=5)
    ax.plot(joint0[0], joint0[1], 'ko', markersize=12, zorder=6, label='Base')
    ax.plot(joint1[0], joint1[1], 'ko', markersize=10, zorder=6)
    ax.plot(joint2[0], joint2[1], 'ko', markersize=10, zorder=6)
    ax.plot(end_effector[0], end_effector[1], 'mo', markersize=8, zorder=6)
    
    # Draw rectangle with top-left (150, 100) and bottom-right (350, -200)
    from matplotlib.patches import Rectangle
    rect_x = 150
    rect_y = -200
    rect_width = 350 - 150
    rect_height = 100 - (-200)
    rectangle = Rectangle((rect_x, rect_y), rect_width, rect_height,
                          linewidth=2, edgecolor='green', facecolor='none',
                          linestyle='-', label='Zone cible')
    ax.add_patch(rectangle)
    
    ax.set_xlabel('X (mm)', fontsize=12)
    ax.set_ylabel('Z (mm)', fontsize=12)
    ax.set_title(f"Espace de travail complet: θ=0, y=0, μ ∈ [-90°, 90°], x>0", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.axis('equal')
    ax.legend(loc='upper left', fontsize=10)
    plt.tight_layout()
    plt.show()
    
    # Print workspace statistics
    print("\n" + "="*50)
    print("WORKSPACE STATISTICS")
    print("="*50)
    print(f"Robot parameters:")
    print(f"  Link 1 (l1): {l1} mm")
    print(f"  Link 2 (l2): {l2} mm")
    print(f"  Link 3 (l3): {l3} mm")
    print(f"\nMu range: -90° to 90°")
    print(f"\nTheoretical reach:")
    print(f"  Maximum: {l1 + l2 + l3} mm")
    print(f"  Minimum: {abs(l1 - l2) - l3} mm")
    
    if len(all_points) > 0:
        distances = np.sqrt(all_points[:, 0]**2 + all_points[:, 1]**2)
        print(f"\nActual workspace boundary:")
        print(f"  Maximum reach: {np.max(distances):.2f} mm")
        print(f"  Minimum reach: {np.min(distances):.2f} mm")
        print(f"  Total boundary points sampled: {len(all_points)}")
    
    print("="*50)

if __name__ == "__main__":
    visualize_workspace()