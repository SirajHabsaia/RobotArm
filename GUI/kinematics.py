import numpy as np

def inverse_kinematics(x_abs, y_abs, z_abs, l1=250, l2=200, l3=150, mu=0):
    theta = np.arctan2(y_abs, x_abs) if x_abs !=0 else (1 if y_abs>0 else -1) * np.pi/2
    x_abs = np.sqrt(x_abs**2+y_abs**2)
    x = x_abs - l3*np.cos(mu)
    z = z_abs - l3*np.sin(mu)
    r = np.sqrt(x**2 + z**2)
    a = np.arccos((-l2**2 + l1**2 + r**2)/(2*l1*r))
    b = np.arccos((l1**2 + l2**2 - r**2)/(2*l1*l2))
    atn = np.arctan2(z, x)

    return [
        theta, #theta
        np.pi - a - b - atn, #alpha
        np.pi/2 - a - atn, #beta
        mu + np.pi - a - b - atn #gamma
    ]

def direct_kinematics(theta, alpha, beta, gamma, l1=250, l2=200, l3=150):
    q1 = np.pi/2 - beta
    q2 = -alpha
    q3 = gamma - alpha

    x_plane = (
        l1 * np.cos(q1) +
        l2 * np.cos(q2) +
        l3 * np.cos(q3)
    )
    z_plane = (
        l1 * np.sin(q1) +
        l2 * np.sin(q2) +
        l3 * np.sin(q3)
    )

    x = x_plane * np.cos(theta)
    y = x_plane * np.sin(theta)
    z = z_plane
    return np.array([x, y, z])

#test
if __name__ == "__main__":
    x_target = 200
    y_target = 100
    z_target = 100
    mu = 0  # End effector orientation

    angles = inverse_kinematics(x_target, y_target, z_target, mu=mu)
    print("Inverse Kinematics Angles (radians):\n", *angles)

    position = direct_kinematics(*angles)
    print("Direct Kinematics Position:\n", position)