import sys
import os
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QGroupBox
)
from PySide6.QtCore import Qt

# Add GUI folder to path to import kinematics
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'GUI'))
from kinematics import inverse_kinematics, direct_kinematics  # type: ignore


# =========================
# MAIN WINDOW
# =========================
class KinematicsConverter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kinematics Converter")
        
        # Default link lengths
        self.l1 = 250
        self.l2 = 200
        self.l3 = 150
        
        # Create main layout
        main_layout = QHBoxLayout()
        
        # Cartesian Space Group
        cartesian_group = QGroupBox("Cartesian Space")
        cartesian_layout = QGridLayout()
        
        cartesian_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_input = QLineEdit("200")
        cartesian_layout.addWidget(self.x_input, 0, 1)
        
        cartesian_layout.addWidget(QLabel("Y:"), 1, 0)
        self.y_input = QLineEdit("100")
        cartesian_layout.addWidget(self.y_input, 1, 1)
        
        cartesian_layout.addWidget(QLabel("Z:"), 2, 0)
        self.z_input = QLineEdit("100")
        cartesian_layout.addWidget(self.z_input, 2, 1)
        
        cartesian_layout.addWidget(QLabel("μ (mu):"), 3, 0)
        self.mu_input = QLineEdit("0")
        cartesian_layout.addWidget(self.mu_input, 3, 1)
        
        self.cartesian_to_joint_btn = QPushButton("→ Inverse Kinematics →")
        self.cartesian_to_joint_btn.clicked.connect(self.cartesian_to_joint)
        cartesian_layout.addWidget(self.cartesian_to_joint_btn, 4, 0, 1, 2)
        
        cartesian_group.setLayout(cartesian_layout)
        main_layout.addWidget(cartesian_group)
        
        # Joint Space Group
        joint_group = QGroupBox("Joint Space (degrees)")
        joint_layout = QGridLayout()
        
        joint_layout.addWidget(QLabel("Theta (θ):"), 0, 0)
        self.theta_input = QLineEdit("0")
        joint_layout.addWidget(self.theta_input, 0, 1)
        
        joint_layout.addWidget(QLabel("Alpha (α):"), 1, 0)
        self.alpha_input = QLineEdit("0")
        joint_layout.addWidget(self.alpha_input, 1, 1)
        
        joint_layout.addWidget(QLabel("Beta (β):"), 2, 0)
        self.beta_input = QLineEdit("0")
        joint_layout.addWidget(self.beta_input, 2, 1)
        
        joint_layout.addWidget(QLabel("Gamma (γ):"), 3, 0)
        self.gamma_input = QLineEdit("0")
        joint_layout.addWidget(self.gamma_input, 3, 1)
        
        self.joint_to_cartesian_btn = QPushButton("← Direct Kinematics ←")
        self.joint_to_cartesian_btn.clicked.connect(self.joint_to_cartesian)
        joint_layout.addWidget(self.joint_to_cartesian_btn, 4, 0, 1, 2)
        
        joint_group.setLayout(joint_layout)
        main_layout.addWidget(joint_group)
        
        # Link Lengths Group
        links_group = QGroupBox("Link Lengths (mm)")
        links_layout = QGridLayout()
        
        links_layout.addWidget(QLabel("L1:"), 0, 0)
        self.l1_input = QLineEdit(str(self.l1))
        self.l1_input.textChanged.connect(self.update_link_lengths)
        links_layout.addWidget(self.l1_input, 0, 1)
        
        links_layout.addWidget(QLabel("L2:"), 1, 0)
        self.l2_input = QLineEdit(str(self.l2))
        self.l2_input.textChanged.connect(self.update_link_lengths)
        links_layout.addWidget(self.l2_input, 1, 1)
        
        links_layout.addWidget(QLabel("L3:"), 2, 0)
        self.l3_input = QLineEdit(str(self.l3))
        self.l3_input.textChanged.connect(self.update_link_lengths)
        links_layout.addWidget(self.l3_input, 2, 1)
        
        links_group.setLayout(links_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Complete layout
        container_layout = QVBoxLayout()
        container_layout.addLayout(main_layout)
        container_layout.addWidget(links_group)
        container_layout.addWidget(self.status_label)
        
        container = QWidget()
        container.setLayout(container_layout)
        self.setCentralWidget(container)
    
    def update_link_lengths(self):
        """Update link length values from input fields."""
        try:
            self.l1 = float(self.l1_input.text())
            self.l2 = float(self.l2_input.text())
            self.l3 = float(self.l3_input.text())
        except ValueError:
            pass
    
    def cartesian_to_joint(self):
        """Convert from Cartesian space to Joint space using inverse kinematics."""
        try:
            x = float(self.x_input.text())
            y = float(self.y_input.text())
            z = float(self.z_input.text())
            mu = float(self.mu_input.text())
            
            # Convert mu from degrees to radians for backend
            mu_rad = np.radians(mu)
            angles_rad = inverse_kinematics(x, y, z, self.l1, self.l2, self.l3, mu_rad)
            
            # Convert angles from radians to degrees for display
            self.theta_input.setText(f"{np.degrees(angles_rad[0]):.3f}")
            self.alpha_input.setText(f"{np.degrees(angles_rad[1]):.3f}")
            self.beta_input.setText(f"{np.degrees(angles_rad[2]):.3f}")
            self.gamma_input.setText(f"{np.degrees(angles_rad[3]):.3f}")
            
            self.status_label.setText(f"✓ Inverse Kinematics: X={x}, Y={y}, Z={z} → Angles computed")
            self.status_label.setStyleSheet("color: green;")
            
        except ValueError as e:
            self.status_label.setText(f"✗ Error: Invalid input values")
            self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            self.status_label.setText(f"✗ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
    
    def joint_to_cartesian(self):
        """Convert from Joint space to Cartesian space using direct kinematics."""
        try:
            # Get angles in degrees from user
            theta_deg = float(self.theta_input.text())
            alpha_deg = float(self.alpha_input.text())
            beta_deg = float(self.beta_input.text())
            gamma_deg = float(self.gamma_input.text())
            
            # Convert to radians for backend
            theta_rad = np.radians(theta_deg)
            alpha_rad = np.radians(alpha_deg)
            beta_rad = np.radians(beta_deg)
            gamma_rad = np.radians(gamma_deg)
            
            position = direct_kinematics(theta_rad, alpha_rad, beta_rad, gamma_rad, self.l1, self.l2, self.l3)
            
            self.x_input.setText(f"{position[0]:.3f}")
            self.y_input.setText(f"{position[1]:.3f}")
            self.z_input.setText(f"{position[2]:.3f}")
            
            self.status_label.setText(f"✓ Direct Kinematics: Angles → X={position[0]:.2f}, Y={position[1]:.2f}, Z={position[2]:.2f}")
            self.status_label.setStyleSheet("color: green;")
            
        except ValueError as e:
            self.status_label.setText(f"✗ Error: Invalid input values")
            self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            self.status_label.setText(f"✗ Error: {str(e)}")
            self.status_label.setStyleSheet("color: red;")


# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = KinematicsConverter()
    win.resize(700, 350)
    win.show()
    sys.exit(app.exec())
