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

smoothing_window = 21  # Default smoothing window size


# =========================
# MATPLOTLIB CANVAS
# =========================
class PlotCanvas(FigureCanvasQTAgg):
    def __init__(self):
        fig = Figure(figsize=(10, 6))
        self.ax = [
            fig.add_subplot(2, 2, 1), fig.add_subplot(2, 2, 2),
            fig.add_subplot(2, 2, 3), fig.add_subplot(2, 2, 4),
        ]
        super().__init__(fig)
        fig.tight_layout()


# =========================
# CALCULATION FUNCTIONS
# =========================
def calculate_smoothed_data(time, a, b, window=smoothing_window):
    """
    Calculate smoothed position and velocity data.
    
    Args:
        time: Array of time values
        a: Array of joint A position values
        b: Array of joint B position values
        window: Smoothing window size (default: 7)
    
    Returns:
        Dictionary containing smoothed and raw data for both joints
    """
    t = np.array(time)
    a = np.array(a)
    b = np.array(b)
    
    pad = window // 2
    
    # Pad the data at edges to avoid edge artifacts
    a_padded = np.pad(a, pad, mode='edge')
    b_padded = np.pad(b, pad, mode='edge')
    
    # Convolve and remove padding
    a_smooth = np.convolve(a_padded, np.ones(window)/window, mode='valid')
    b_smooth = np.convolve(b_padded, np.ones(window)/window, mode='valid')
    
    # Calculate velocities
    va = np.gradient(a_smooth, t)
    vb = np.gradient(b_smooth, t)
    
    # Smooth velocity to reduce jitter
    va_padded = np.pad(va, pad, mode='edge')
    vb_padded = np.pad(vb, pad, mode='edge')
    
    va_smooth = np.convolve(va_padded, np.ones(window)/window, mode='valid')
    vb_smooth = np.convolve(vb_padded, np.ones(window)/window, mode='valid')
    
    return {
        't': t,
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
def update_plots(canvas, time, a, b, window=smoothing_window, 
                 show_raw=True, show_smoothed=True):
    """
    Update all plots with the given data.
    
    Args:
        canvas: PlotCanvas instance with ax array
        time: List or array of time values
        a: List or array of joint A position values
        b: List or array of joint B position values
        window: Smoothing window size (default: 7)
        show_raw: Whether to plot raw data (default: True)
        show_smoothed: Whether to plot smoothed data (default: True)
    """
    if len(time) < 3:
        return
    
    data = calculate_smoothed_data(time, a, b, window)
    
    ax = canvas.ax
    
    # Clear all axes
    for axis in ax:
        axis.clear()
    
    # Joint A Position
    if show_raw:
        ax[0].plot(data['t'], data['a'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[0].plot(data['t'], data['a_smooth'], 'r-', label='Smoothed')
    ax[0].set_title("Joint A Position")
    ax[0].legend()
    
    # Joint A Velocity
    if show_raw:
        ax[2].plot(data['t'], data['va'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[2].plot(data['t'], data['va_smooth'], 'r-', label='Smoothed')
    ax[2].axhline(VEL_LIMIT_A, linestyle="--", color='gray')
    ax[2].axhline(-VEL_LIMIT_A, linestyle="--", color='gray')
    ax[2].set_title("Joint A Velocity")
    ax[2].legend()
    
    # Joint B Position
    if show_raw:
        ax[1].plot(data['t'], data['b'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[1].plot(data['t'], data['b_smooth'], 'r-', label='Smoothed')
    ax[1].set_title("Joint B Position")
    ax[1].legend()
    
    # Joint B Velocity
    if show_raw:
        ax[3].plot(data['t'], data['vb'], 'b-', alpha=0.5, label='Raw')
    if show_smoothed:
        ax[3].plot(data['t'], data['vb_smooth'], 'r-', label='Smoothed')
    ax[3].axhline(VEL_LIMIT_B, linestyle="--", color='gray')
    ax[3].axhline(-VEL_LIMIT_B, linestyle="--", color='gray')
    ax[3].set_title("Joint B Velocity")
    ax[3].legend()
    
    canvas.draw_idle()
