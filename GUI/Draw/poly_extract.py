import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from typing import List, Tuple


class ImageToPolylines:
    """
    Convert an image to polylines for robot arm drawing.
    
    This class processes an image using edge detection and extracts
    separate polylines that the robot arm can draw.
    """
    
    def __init__(self, 
                 image_path: str,
                 drawing_z: float = 20.0,
                 pen_lift_z: float = 40.0,
                 square_size: float = 200.0,
                 center_x: float = 0.0,
                 center_y: float = 0.0,
                 canny_threshold1: int = 50,
                 canny_threshold2: int = 150,
                 min_contour_length: int = 10,
                 closing_kernel_size: int = 0,
                 endpoint_merge_distance: float = 0.0,
                 simplification_epsilon: float = 1.5):
        """
        Initialize the image to polylines converter.
        
        Args:
            image_path: Path to the input image file
            drawing_z: Z coordinate when pen is down (drawing)
            pen_lift_z: Z coordinate when pen is up (moving between polylines)
            square_size: Side length of the square drawing area
            center_x: X coordinate of the square's center
            center_y: Y coordinate of the square's center
            canny_threshold1: Lower threshold for Canny edge detection
            canny_threshold2: Upper threshold for Canny edge detection
            min_contour_length: Minimum number of points for a valid contour
            closing_kernel_size: Kernel size for morphological closing (0 to disable)
                                Fills small gaps in edges. Try 3-7 to connect nearby edges.
            endpoint_merge_distance: Max distance (in pixels) to merge polyline endpoints (0 to disable)
                                    Connects polylines with nearby endpoints. Try 5-20.
            simplification_epsilon: Tolerance for Douglas-Peucker simplification in pixels (0 to disable)
                                   Higher values = more simplification. Try 0.5-3.0 for good results.
        """
        self.image_path = image_path
        self.drawing_z = drawing_z
        self.pen_lift_z = pen_lift_z
        self.square_size = square_size
        self.center_x = center_x
        self.center_y = center_y
        self.canny_threshold1 = canny_threshold1
        self.canny_threshold2 = canny_threshold2
        self.min_contour_length = min_contour_length
        self.closing_kernel_size = closing_kernel_size
        self.endpoint_merge_distance = endpoint_merge_distance
        self.simplification_epsilon = simplification_epsilon
        
        self.image = None
        self.edges = None
        self.polylines = []
        self.scaled_polylines = []
        
    def load_and_process_image(self):
        """Load the image and perform edge detection."""
        # Load image
        self.image = cv2.imread(self.image_path)
        if self.image is None:
            raise ValueError(f"Could not load image from {self.image_path}")
        
        # Convert to grayscale
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 1.4)
        
        # Perform Canny edge detection
        self.edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)
        
        # Apply morphological closing to fill small gaps if requested
        if self.closing_kernel_size > 0:
            kernel = np.ones((self.closing_kernel_size, self.closing_kernel_size), np.uint8)
            self.edges = cv2.morphologyEx(self.edges, cv2.MORPH_CLOSE, kernel)
        
        return self.edges
    
    def _merge_nearby_polylines(self, polylines: List[np.ndarray], max_distance: float) -> List[np.ndarray]:
        """
        Merge polylines that have endpoints within max_distance of each other.
        
        Args:
            polylines: List of polylines to potentially merge
            max_distance: Maximum distance between endpoints to consider merging
            
        Returns:
            List of merged polylines
        """
        if not polylines:
            return polylines
        
        merged = True
        merged_polylines = polylines.copy()
        
        while merged:
            merged = False
            i = 0
            
            while i < len(merged_polylines):
                j = i + 1
                while j < len(merged_polylines):
                    poly_i = merged_polylines[i]
                    poly_j = merged_polylines[j]
                    
                    # Get endpoints
                    i_start, i_end = poly_i[0], poly_i[-1]
                    j_start, j_end = poly_j[0], poly_j[-1]
                    
                    # Check all possible connections
                    connections = [
                        (np.linalg.norm(i_end - j_start), 'end-start', False, False),
                        (np.linalg.norm(i_end - j_end), 'end-end', False, True),
                        (np.linalg.norm(i_start - j_start), 'start-start', True, False),
                        (np.linalg.norm(i_start - j_end), 'start-end', True, True)
                    ]
                    
                    # Find closest connection
                    min_dist, conn_type, flip_i, flip_j = min(connections, key=lambda x: x[0])
                    
                    if min_dist <= max_distance:
                        # Merge the polylines
                        if flip_i:
                            poly_i = np.flip(poly_i, axis=0)
                        if flip_j:
                            poly_j = np.flip(poly_j, axis=0)
                        
                        # Concatenate
                        new_polyline = np.vstack([poly_i, poly_j])
                        
                        # Replace poly_i with merged version and remove poly_j
                        merged_polylines[i] = new_polyline
                        merged_polylines.pop(j)
                        
                        merged = True
                        break
                    else:
                        j += 1
                
                if merged:
                    break
                i += 1
        
        return merged_polylines
    
    def extract_polylines(self):
        """Extract polylines (contours) from the edge-detected image."""
        if self.edges is None:
            self.load_and_process_image()
        
        # Find contours
        contours, _ = cv2.findContours(self.edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        # Convert contours to polylines and filter by minimum length
        self.polylines = []
        original_point_count = 0
        simplified_point_count = 0
        
        for contour in contours:
            if len(contour) >= self.min_contour_length:
                # Apply Douglas-Peucker simplification if requested
                if self.simplification_epsilon > 0:
                    # approxPolyDP expects epsilon as max distance from contour to approximated contour
                    simplified_contour = cv2.approxPolyDP(contour, self.simplification_epsilon, closed=False)
                    original_point_count += len(contour)
                    simplified_point_count += len(simplified_contour)
                    contour = simplified_contour
                
                # Reshape contour from (n, 1, 2) to (n, 2)
                polyline = contour.reshape(-1, 2)
                
                # Only keep if still meets minimum length after simplification
                if len(polyline) >= self.min_contour_length:
                    self.polylines.append(polyline)
        
        # Print simplification statistics if simplification was applied
        if self.simplification_epsilon > 0 and original_point_count > 0:
            reduction = 100 * (1 - simplified_point_count / original_point_count)
            print(f"[Simplification] Reduced points from {original_point_count} to {simplified_point_count} ({reduction:.1f}% reduction)")
        
        # Merge polylines with nearby endpoints if requested
        if self.endpoint_merge_distance > 0:
            self.polylines = self._merge_nearby_polylines(self.polylines, self.endpoint_merge_distance)
        
        return self.polylines
    
    def scale_to_workspace(self):
        """
        Scale polylines from image coordinates to robot workspace coordinates.
        Maintains aspect ratio and centers the drawing in the square.
        """
        if not self.polylines:
            self.extract_polylines()
        
        if not self.polylines:
            raise ValueError("No polylines found in image")
        
        # Get image dimensions
        img_height, img_width = self.edges.shape
        
        # Calculate scaling factor (maintain aspect ratio)
        # Scale until the image touches one pair of square sides
        scale_x = self.square_size / img_width
        scale_y = self.square_size / img_height
        scale = min(scale_x, scale_y)  # Use smaller scale to fit within square
        
        # Calculate the scaled image dimensions
        scaled_width = img_width * scale
        scaled_height = img_height * scale
        
        # Calculate offset to center the scaled image in the square
        offset_x = self.center_x - scaled_width / 2
        offset_y = self.center_y - scaled_height / 2
        
        # Transform all polylines
        self.scaled_polylines = []
        for polyline in self.polylines:
            # Scale and flip Y (image coordinates have Y increasing downward)
            scaled = polyline * scale
            
            # Flip Y coordinate (image Y goes down, robot Y goes up)
            scaled[:, 1] = scaled_height - scaled[:, 1]
            
            # Translate to center position
            scaled[:, 0] += offset_x
            scaled[:, 1] += offset_y
            
            self.scaled_polylines.append(scaled)
        
        return self.scaled_polylines
    
    def get_waypoints_with_pen_control(self) -> List[List[Tuple[float, float, float]]]:
        """
        Get waypoints organized as separate polylines with pen control.
        
        Returns:
            List of polylines, where each polyline is a list of (x, y, z) tuples.
            Each polyline starts with pen lift at first point, contains drawing 
            points at drawing_z, and ends with pen lift at last point.
        """
        if not self.scaled_polylines:
            self.scale_to_workspace()
        
        polylines_with_control = []
        
        for polyline in self.scaled_polylines:
            polyline_waypoints = []
            
            # Start with pen lifted at the first point (approach position)
            first_x, first_y = polyline[0]
            polyline_waypoints.append((first_x, first_y, self.pen_lift_z))
            
            # Add all points in the polyline at drawing height
            for point in polyline:
                x, y = point
                polyline_waypoints.append((x, y, self.drawing_z))
            
            # End with pen lifted at the last point
            last_x, last_y = polyline[-1]
            polyline_waypoints.append((last_x, last_y, self.pen_lift_z))
            
            polylines_with_control.append(polyline_waypoints)
        
        return polylines_with_control
    
    def get_polylines_only(self) -> List[List[Tuple[float, float, float]]]:
        """
        Get polylines as separate lists (without pen control movements).
        
        Returns:
            List of polylines, where each polyline is a list of (x, y, z) tuples
        """
        if not self.scaled_polylines:
            self.scale_to_workspace()
        
        polylines_3d = []
        for polyline in self.scaled_polylines:
            polyline_3d = [(x, y, self.drawing_z) for x, y in polyline]
            polylines_3d.append(polyline_3d)
        
        return polylines_3d
    
    def visualize(self, show_square=True):
        """
        Visualize the extracted polylines with different colors.
        
        Args:
            show_square: Whether to show the drawing square boundary
        """
        if not self.scaled_polylines:
            self.scale_to_workspace()
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 7))
        
        # Show original edge-detected image
        axes[0].imshow(self.edges, cmap='gray')
        axes[0].set_title('Edge Detection Result')
        axes[0].axis('off')
        
        # Show polylines in workspace coordinates
        ax = axes[1]
        ax.set_aspect('equal')
        ax.set_title(f'Polylines in Robot Workspace ({len(self.scaled_polylines)} polylines)')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        
        # Generate colors for each polyline
        colors = plt.cm.rainbow(np.linspace(0, 1, len(self.scaled_polylines)))
        
        # Draw each polyline with a different color
        for polyline, color in zip(self.scaled_polylines, colors):
            ax.plot(polyline[:, 0], polyline[:, 1], color=color, linewidth=0.5, alpha=0.8)
        
        # Draw the square boundary if requested
        if show_square:
            half_size = self.square_size / 2
            square_x = [self.center_x - half_size, self.center_x + half_size,
                       self.center_x + half_size, self.center_x - half_size,
                       self.center_x - half_size]
            square_y = [self.center_y - half_size, self.center_y - half_size,
                       self.center_y + half_size, self.center_y + half_size,
                       self.center_y - half_size]
            ax.plot(square_x, square_y, 'k--', linewidth=2, label='Drawing Area')
            ax.legend()
        
        # Set equal aspect and margins
        ax.margins(0.1)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def save_waypoints(self, output_path: str):
        """
        Save waypoints to a text file.
        
        Args:
            output_path: Path to save the waypoints
        """
        polylines = self.get_waypoints_with_pen_control()
        total_waypoints = sum(len(p) for p in polylines)
        
        with open(output_path, 'w') as f:
            f.write(f"# Robot Arm Drawing Waypoints\n")
            f.write(f"# Generated from: {self.image_path}\n")
            f.write(f"# Total polylines: {len(polylines)}\n")
            f.write(f"# Total waypoints: {total_waypoints}\n")
            f.write(f"# Drawing Z: {self.drawing_z}, Pen Lift Z: {self.pen_lift_z}\n")
            f.write(f"# Format: X, Y, Z\n")
            f.write(f"# Each polyline starts and ends with a pen lift point\n\n")
            
            for i, polyline in enumerate(polylines, 1):
                f.write(f"# Polyline {i}\n")
                for x, y, z in polyline:
                    f.write(f"{x:.3f}, {y:.3f}, {z:.3f}\n")
                f.write("\n")
        
        print(f"Waypoints saved to {output_path}")


def main():
    """Example usage of the ImageToPolylines class."""
    
    # Create converter instance
    converter = ImageToPolylines(
        image_path="GUI/Draw/images/amongus.jpg",
        drawing_z=10.0,      # Z height when drawing (pen down)
        pen_lift_z=30.0,       # Z height when moving (pen up)
        square_size=200.0,    # 200mm square drawing area
        center_x=400.0,         # Center of square at origin
        center_y=0.0,
        canny_threshold1=50,  # Lower Canny threshold (adjust for more/fewer edges)
        canny_threshold2=100, # Upper Canny threshold
        min_contour_length=10,# Minimum points in a polyline
        closing_kernel_size=5,# Kernel size for morphological closing (0 to disable)
        endpoint_merge_distance=0,  # Max pixel distance to merge polylines (0 to disable)
        simplification_epsilon=1.5  # Douglas-Peucker simplification tolerance (0 to disable)
    )
    
    # Process the image
    print("Loading and processing image...")
    converter.load_and_process_image()
    
    print("Extracting polylines...")
    converter.extract_polylines()
    
    print("Scaling to workspace...")
    converter.scale_to_workspace()
    
    print(f"Found {len(converter.scaled_polylines)} polylines")
    
    # Get waypoints with pen control
    polylines_with_control = converter.get_waypoints_with_pen_control()
    total_waypoints = sum(len(p) for p in polylines_with_control)
    print(f"Generated {len(polylines_with_control)} polylines")
    print(f"Total waypoints: {total_waypoints} (including pen control)")
    
    # Get polylines only (without pen control movements)
    polylines_only = converter.get_polylines_only()
    print(f"Total drawing points: {sum(len(p) for p in polylines_only)}")
    
    # Save waypoints to file
    converter.save_waypoints("GUI/Draw/waypoints.txt")
    
    # Visualize
    print("Displaying visualization...")
    converter.visualize(show_square=True)


if __name__ == "__main__":
    main()
