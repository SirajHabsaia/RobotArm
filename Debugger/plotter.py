import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


# =========================
# HARD-CODED LIMITS
# =========================
VEL_LIMIT_A = 10.0
ACC_LIMIT_A = 10.0

VEL_LIMIT_B = 10.0
ACC_LIMIT_B = 10.0

VEL_LIMIT_THETA = 10.0
ACC_LIMIT_THETA = 10.0

smoothing_window = 21  # Default smoothing window size


# =========================
# MATPLOTLIB CANVAS
# =========================
class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        fig = Figure(figsize=(12, 8))
        self.ax = [
            fig.add_subplot(3, 2, 1), fig.add_subplot(3, 2, 2),
            fig.add_subplot(3, 2, 3), fig.add_subplot(3, 2, 4),
            fig.add_subplot(3, 2, 5), fig.add_subplot(3, 2, 6),
        ]
        super().__init__(fig)
        fig.tight_layout()


# =========================
# CALCULATION FUNCTIONS
# =========================
def calculate_smoothed_data(time, theta, a, b, window=smoothing_window):
    """
    Calculate smoothed position and velocity data.
    
    Args:
        time: Array of time values
        theta: Array of theta (joint 0) position values
        a: Array of joint A position values
        b: Array of joint B position values
        window: Smoothing window size (default: 7)
    
    Returns:
        Dictionary containing smoothed and raw data for all joints
    """
    t = np.array(time)
    theta = np.array(theta)
    a = np.array(a)
    b = np.array(b)
    
    pad = window // 2
    
    # Pad the data at edges to avoid edge artifacts
    theta_padded = np.pad(theta, pad, mode='edge')
    a_padded = np.pad(a, pad, mode='edge')
    b_padded = np.pad(b, pad, mode='edge')
    
    # Convolve and remove padding
    theta_smooth = np.convolve(theta_padded, np.ones(window)/window, mode='valid')
    a_smooth = np.convolve(a_padded, np.ones(window)/window, mode='valid')
    b_smooth = np.convolve(b_padded, np.ones(window)/window, mode='valid')
    
    # Calculate velocities
    vtheta = np.gradient(theta_smooth, t)
    va = np.gradient(a_smooth, t)
    vb = np.gradient(b_smooth, t)
    
    # Smooth velocity to reduce jitter
    vtheta_padded = np.pad(vtheta, pad, mode='edge')
    va_padded = np.pad(va, pad, mode='edge')
    vb_padded = np.pad(vb, pad, mode='edge')
    
    vtheta_smooth = np.convolve(vtheta_padded, np.ones(window)/window, mode='valid')
    va_smooth = np.convolve(va_padded, np.ones(window)/window, mode='valid')
    vb_smooth = np.convolve(vb_padded, np.ones(window)/window, mode='valid')
    
    return {
        't': t,
        'theta': theta,
        'theta_smooth': theta_smooth,
        'vtheta': vtheta,
        'vtheta_smooth': vtheta_smooth,
        'a': a,
        'a_smooth': a_smooth,
        'va': va,
        'va_smooth': va_smooth,
        'b': b,
        'b_smooth': b_smooth,
        'vb': vb,
        'vb_smooth': vb_smooth,
    }


# =========================
# PLOTTING FUNCTIONS
# =========================
def update_plots(canvas, time, theta, a, b, window=smoothing_window, 
                 show_raw=True, show_smoothed=True):
    """
    Update all plots with the given data.
    
    Args:
        canvas: PlotCanvas instance with ax array
        time: List or array of time values
        theta: List or array of theta (joint 0) position values
        a: List or array of joint A position values
        b: List or array of joint B position values
        window: Smoothing window size (default: 7)
        show_raw: Whether to plot raw data (default: True)
        show_smoothed: Whether to plot smoothed data (default: True)
    """
    if len(time) < 3:
        return
    
    data = calculate_smoothed_data(time, theta, a, b, window)
    
    ax = canvas.ax
    
    # Clear all axes
    for axis in ax:
        axis.clear()
    
    # Theta Position (left column, top)
    if show_raw:
        ax[0].plot(data['t'], data['theta'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[0].plot(data['t'], data['theta_smooth'], 'r-', label='Smoothed')
    ax[0].set_title("Theta Position")
    ax[0].legend()
    
    # Theta Velocity (right column, top)
    if show_raw:
        ax[1].plot(data['t'], data['vtheta'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[1].plot(data['t'], data['vtheta_smooth'], 'r-', label='Smoothed')
    ax[1].axhline(VEL_LIMIT_THETA, linestyle="--", color='gray')
    ax[1].axhline(-VEL_LIMIT_THETA, linestyle="--", color='gray')
    ax[1].set_title("Theta Velocity")
    ax[1].legend()
    
    # Joint A Position (left column, middle)
    if show_raw:
        ax[2].plot(data['t'], data['a'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[2].plot(data['t'], data['a_smooth'], 'r-', label='Smoothed')
    ax[2].set_title("Joint A Position")
    ax[2].legend()
    
    # Joint A Velocity (right column, middle)
    if show_raw:
        ax[3].plot(data['t'], data['va'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[3].plot(data['t'], data['va_smooth'], 'r-', label='Smoothed')
    ax[3].axhline(VEL_LIMIT_A, linestyle="--", color='gray')
    ax[3].axhline(-VEL_LIMIT_A, linestyle="--", color='gray')
    ax[3].set_title("Joint A Velocity")
    ax[3].legend()
    
    # Joint B Position (left column, bottom)
    if show_raw:
        ax[4].plot(data['t'], data['b'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[4].plot(data['t'], data['b_smooth'], 'r-', label='Smoothed')
    ax[4].set_title("Joint B Position")
    ax[4].legend()
    
    # Joint B Velocity (right column, bottom)
    if show_raw:
        ax[5].plot(data['t'], data['vb'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[5].plot(data['t'], data['vb_smooth'], 'r-', label='Smoothed')
    ax[5].axhline(VEL_LIMIT_B, linestyle="--", color='gray')
    ax[5].axhline(-VEL_LIMIT_B, linestyle="--", color='gray')
    ax[5].set_title("Joint B Velocity")
    ax[5].legend()
    
    canvas.draw_idle()
