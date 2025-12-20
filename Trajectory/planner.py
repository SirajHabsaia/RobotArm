import numpy as np
import matplotlib.pyplot as plt

# ---------- User params ----------
n_joints = 3
joints_names = ['theta', 'alpha', 'beta']
joints_max_speeds = np.array([1.0, 0.5, 0.5])   # deg/s
joints_max_accel  = np.array([0.2, 0.3, 0.5])   # deg/s^2

trajectory, T_initial = (lambda t: [
    t if t<10 else 20 - t,                       # theta
    5*np.sin(2*np.pi/20.0 * t),   # alpha
    -t**2/10.0 + 2.0*t            # beta
], 20.0)

dt_waypoints = 0.1
t_waypoints = np.arange(0.0, T_initial + 1e-9, dt_waypoints)
waypoints = np.array([trajectory(t) for t in t_waypoints])   # shape (N_nodes, 3)

n_waypoints = len(waypoints)
n_segs = n_waypoints - 1

# ---------- Build path deltas and directions ----------
dQ = waypoints[1:] - waypoints[:-1]          # (n_segs, n_joints)
ds = np.linalg.norm(dQ, axis=1)              # scalar lengths
u = np.zeros_like(dQ)
nz = ds > 0
u[nz] = dQ[nz] / ds[nz][:, None]

# ---------- Detect direction change nodes ----------
direction_change_nodes = []
for k in range(1, n_waypoints-1):
    # global direction inversion (full vector) - optional
    if ds[k-1] > 0 and ds[k] > 0:
        if np.dot(u[k-1], u[k]) < 0:
            direction_change_nodes.append(k)

# ---------- Per-joint sign flips detection (NEW) ----------
# If any component j flips sign between u[k-1,j] and u[k,j], add node k to zero_nodes
per_joint_flip_nodes = set()
for k in range(1, n_waypoints-1):
    for j in range(n_joints):
        # only check when adjacent segments have length and component not near zero
        if ds[k-1] > 0 and ds[k] > 0:
            a = u[k-1, j]
            b = u[k, j]
            if abs(a) > 1e-12 and abs(b) > 1e-12 and (a * b < 0):
                per_joint_flip_nodes.add(k)
# Merge
direction_change_nodes = sorted(set(direction_change_nodes).union(per_joint_flip_nodes))

# zero nodes: endpoints + any per-joint sign-flip or global reversal nodes
zero_nodes = set([0, n_waypoints-1] + direction_change_nodes)

# ---------- Convert joint limits to path limits ----------
INF_LARGE = 1e12
s_dot_max_seg = np.full(n_segs, INF_LARGE)
s_ddot_max_seg = np.full(n_segs, INF_LARGE)
for i in range(n_segs):
    per_v = []
    per_a = []
    for j in range(n_joints):
        uj = abs(u[i, j])
        if uj > 1e-12:
            per_v.append(joints_max_speeds[j] / uj)
            per_a.append(joints_max_accel[j] / uj)
    if per_v:
        s_dot_max_seg[i] = min(per_v)
    if per_a:
        s_ddot_max_seg[i] = min(per_a)
s_dot_max_seg = np.minimum(s_dot_max_seg, INF_LARGE)
s_ddot_max_seg = np.minimum(s_ddot_max_seg, INF_LARGE)

# ---------- initialize node speeds ----------
v_nodes = np.full(n_waypoints, np.inf)
v_nodes[0] = 0.0
v_nodes[-1] = 0.0
for i in range(1, n_waypoints-1):
    caps = []
    if i-1 >= 0: caps.append(s_dot_max_seg[i-1])
    if i < n_segs: caps.append(s_dot_max_seg[i])
    v_nodes[i] = min(caps) if caps else 0.0
for z in zero_nodes: v_nodes[z] = 0.0

# ---------- forward/backward with node zeros enforced ----------
def enforce_s_limits(ds, v_nodes, s_ddot_max_seg, s_dot_max_seg, zero_nodes, iters=200, tol=1e-9):
    v = v_nodes.copy().astype(float)
    for _ in range(iters):
        prev = v.copy()
        # cap by local segment s_dot
        for i in range(1, len(v)-1):
            caps = []
            if i-1 >= 0: caps.append(s_dot_max_seg[i-1])
            if i < len(s_dot_max_seg): caps.append(s_dot_max_seg[i])
            if caps:
                v[i] = min(v[i], min(caps))
        for z in zero_nodes: v[z] = 0.0
        # forward
        for i in range(0, len(ds)):
            if ds[i] <= 0: continue
            amax = s_ddot_max_seg[i]
            lim = np.sqrt(max(0.0, v[i]**2 + 2.0 * amax * ds[i]))
            lim = min(lim, s_dot_max_seg[i])
            if (i+1) not in zero_nodes:
                v[i+1] = min(v[i+1], lim)
        # backward
        for i in range(len(ds)-1, -1, -1):
            if ds[i] <= 0: continue
            amax = s_ddot_max_seg[i]
            lim = np.sqrt(max(0.0, v[i+1]**2 + 2.0 * amax * ds[i]))
            lim = min(lim, s_dot_max_seg[i])
            if i not in zero_nodes:
                v[i] = min(v[i], lim)
        for z in zero_nodes: v[z] = 0.0
        if np.max(np.abs(v - prev)) < tol:
            break
    return v

v_nodes = enforce_s_limits(ds, v_nodes, s_ddot_max_seg, s_dot_max_seg, zero_nodes, iters=500)

# ---------- compute seg times ----------
seg_times = np.zeros(n_segs)
for i in range(n_segs):
    if ds[i] <= 0:
        seg_times[i] = 0.0
        continue
    denom = v_nodes[i] + v_nodes[i+1]
    if denom > 1e-12:
        seg_times[i] = 2.0 * ds[i] / denom
    else:
        a = s_ddot_max_seg[i]
        seg_times[i] = 0.0 if a < 1e-12 else 2.0 * np.sqrt(ds[i] / a)

total_time = np.sum(seg_times)
node_times = np.concatenate(([0.0], np.cumsum(seg_times)))

# ---------- reconstruct q(t) ----------
dt_sample = 1e-3
t_dense = np.arange(0.0, total_time + dt_sample/2.0, dt_sample) if total_time>0 else np.array([0.0])
q_dense = np.zeros((len(t_dense), n_joints))
qdot_dense = np.zeros_like(q_dense)

for k,t in enumerate(t_dense):
    seg = np.searchsorted(node_times, t, side='right') - 1
    seg = max(0, min(seg, n_segs-1))
    t_local = t - node_times[seg]
    Ti = seg_times[seg]
    v0 = v_nodes[seg]; v1 = v_nodes[seg+1]
    a_s = 0.0 if Ti<=1e-12 else (v1-v0)/Ti
    s_local = v0 * t_local + 0.5 * a_s * t_local**2
    sdot_local = v0 + a_s * t_local
    q_dense[k] = waypoints[seg] + u[seg] * s_local
    qdot_dense[k] = u[seg] * sdot_local

if t_dense.size>0:
    q_dense[-1] = waypoints[-1]
    qdot_dense[-1] = np.zeros(n_joints)

# ---------- diagnostics & plots ----------
print("per-joint sign-flip nodes:", sorted(list(per_joint_flip_nodes)))
print("global reversal nodes:", direction_change_nodes)
print("zero_nodes enforced:", sorted(list(zero_nodes)))
print("total_time:", total_time)

fig, axes = plt.subplots(n_joints, 3, figsize=(15,10))
for j in range(n_joints):
    # theoretical
    axes[j,0].plot(np.linspace(0,T_initial,501), [trajectory(tt)[j] for tt in np.linspace(0,T_initial,501)])
    axes[j,0].scatter(np.arange(0, T_initial+1e-9, dt_waypoints), [trajectory(tt)[j] for tt in np.arange(0, T_initial+1e-9, dt_waypoints)], color='r')
    axes[j,0].set_title(f"{joints_names[j]} theoretical")
    # generated position
    axes[j,1].plot(t_dense, q_dense[:,j])
    axes[j,1].scatter(node_times, waypoints[:,j], color='red', s=30)
    axes[j,1].set_title(f"{joints_names[j]} generated pos")
    # generated signed speed
    axes[j,2].plot(t_dense, qdot_dense[:,j])
    axes[j,2].axhline(joints_max_speeds[j], color='r', linestyle='--')
    axes[j,2].axhline(-joints_max_speeds[j], color='r', linestyle='--')
    axes[j,2].set_title(f"{joints_names[j]} signed speed")
for ax in axes.flatten(): ax.grid(True)
plt.tight_layout()
plt.show()
