import numpy as np
import matplotlib.pyplot as plt

# Initialisation

n_joints = 3
joints_names = ['theta', 'alpha', 'beta']
joints_max_speeds = np.array([1.0, 2., 3.])   # deg/s
joints_max_accel  = np.array([0.5, 1.0, 1.0])   # deg/s^2

initial_point = np.array([0.0, 0.0, 0.0])
final_point   = np.array([-10.0, 15.0, 5.0])

distances = np.abs(final_point - initial_point)

# Synchronized time calculation

min_times = np.zeros(n_joints)
for j in range(n_joints):
    d = distances[j]
    vmax = joints_max_speeds[j]
    a = joints_max_accel[j]
    d_min_trap = vmax**2 / a
    if d >= d_min_trap:
        t = d / vmax + vmax / a
    else:
        t = 2 * np.sqrt(d / a)
    min_times[j] = t

T = np.max(min_times)

# Solve for speed
t_acc = np.zeros(n_joints)
t_cru = np.zeros(n_joints)
t_dec = np.zeros(n_joints)
v_peak = np.zeros(n_joints)

for j in range(n_joints):
    d = distances[j]
    a = joints_max_accel[j]

    delta = (a * T) ** 2 - 4 * a * d
    if -1e-9 < delta < 0: delta = 0.0 # numerical tolerance

    v = (a * T - np.sqrt(delta)) / 2.0
    t_a = v / a
    t_c = T - 2.0 * t_a

    # numerical tolerance
    if t_c < 0 and t_c > -1e-9: t_c = 0.0
    if v < 0 and v > -1e-9: v = 0.0

    t_acc[j] = t_a
    t_cru[j] = t_c
    t_dec[j] = t_a
    v_peak[j] = v

# Build profiles (simple forward integration)
dt = 0.01
times = np.arange(0, T + dt, dt)
vel = np.zeros((n_joints, len(times)))
pos = np.zeros((n_joints, len(times)))

for j in range(n_joints):
    direction = np.sign(final_point[j] - initial_point[j]) if final_point[j] != initial_point[j] else 1.0
    a = joints_max_accel[j]
    v = v_peak[j]
    t_a = t_acc[j]
    t_c = t_cru[j]
    t_d_start = t_a + t_c
    for i, t in enumerate(times):
        if t < t_a:
            vel_val = a * t
        elif t < t_d_start:
            vel_val = v
        else:
            vel_val = a * max(0.0, T - t)
        vel[j, i] = vel_val * direction
    pos[j] = initial_point[j] + np.cumsum(vel[j] * dt)

# Diagnostics
final_positions = pos[:, -1]
errors = final_positions - final_point
print("T (synchronized) =", T)
for j in range(n_joints):
    print(f"Joint {j} ({joints_names[j]}): d={distances[j]:.6f}, a={joints_max_accel[j]:.6f}")
    print(f"  v_peak={v_peak[j]:.6f}, t_acc={t_acc[j]:.6f}, t_cru={t_cru[j]:.6f}, final_pos={final_positions[j]:.6f}, error={errors[j]:.6e}")

# Plot
fig, axes = plt.subplots(n_joints, 2, figsize=(12, 4 * n_joints))
for j in range(n_joints):
    axes[j, 0].plot(times, vel[j])
    axes[j, 0].set_title(f"{joints_names[j]} - Velocity (peak {v_peak[j]:.3f})")
    axes[j, 0].grid(True)
    axes[j, 1].plot(times, pos[j])
    axes[j, 1].axhline(final_point[j], color='k', linestyle='--', linewidth=0.8)
    axes[j, 1].set_title(f"{joints_names[j]} - Position (final {final_positions[j]:.3f})")
    axes[j, 1].grid(True)
plt.tight_layout(h_pad=2.0)  # Increase vertical gap between graphs
plt.show()
