import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QPushButton
from PySide6.QtCore import Qt

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkActor, vtkPolyDataMapper
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray
from vtkmodules.vtkCommonCore import vtkFloatArray, vtkPoints, vtkUnsignedCharArray
from vtkmodules.vtkCommonTransforms import vtkTransform
import vtkmodules.vtkRenderingOpenGL2  # Required for rendering

from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.XCAFApp import XCAFApp_Application
from OCP.TDocStd import TDocStd_Document
from OCP.TCollection import TCollection_ExtendedString
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ColorGen, XCAFDoc_ColorSurf
from OCP.TDF import TDF_LabelSequence
from OCP.Quantity import Quantity_Color
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

import time

def import_dec(func):
    """Decorator to time functions"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Import {args[0].name} executed in {end_time - start_time:.2f} seconds")
        return result
    return wrapper


class RobotPart:
    def __init__(self, step_file):
        self.actor = None
        self.load_step_with_colors(step_file)

    @import_dec 
    def load_step_with_colors(self, step_file):
        """Load STEP file with colors using XCAF + VTK"""
        
        if not step_file.exists():
            print(f"  Error: File not found: {step_file}")
            return

        # Create XCAF document
        app = XCAFApp_Application.GetApplication_s()
        doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
        app.InitDocument(doc)

        # Read STEP file with colors
        reader = STEPCAFControl_Reader()
        reader.SetColorMode(True)
        reader.SetNameMode(True)
        status = reader.ReadFile(str(step_file))
        if status != 1:  # IFSelect_RetDone
            print(f"  Error: Failed to read file (status={status})")
            return
        
        if not reader.Transfer(doc):
            print(f"  Error: Failed to transfer data")
            return

        # Get tools
        shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        color_tool = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())

        # Build face color list using the same approach as OpenGL viewer
        face_color_list = []
        
        # Check all non-free shapes (components in assemblies)
        all_labels = TDF_LabelSequence()
        shape_tool.GetShapes(all_labels)
        
        for i in range(1, all_labels.Length() + 1):
            comp_label = all_labels.Value(i)
            
            if shape_tool.IsFree_s(comp_label):
                continue
            
            color = Quantity_Color()
            comp_color = None
            
            if color_tool.GetColor_s(comp_label, XCAFDoc_ColorGen, color):
                comp_color = [color.Red(), color.Green(), color.Blue()]
            elif color_tool.GetColor_s(comp_label, XCAFDoc_ColorSurf, color):
                comp_color = [color.Red(), color.Green(), color.Blue()]
            
            if comp_color is not None:
                comp_shape = shape_tool.GetShape_s(comp_label)
                explorer = TopExp_Explorer(comp_shape, TopAbs_FACE)
                while explorer.More():
                    face = TopoDS.Face_s(explorer.Current())
                    face_color_list.append((face, comp_color))
                    explorer.Next()
            
            # Always check sub-shapes
            sub_labels = TDF_LabelSequence()
            shape_tool.GetSubShapes_s(comp_label, sub_labels)
            for j in range(1, sub_labels.Length() + 1):
                sub_label = sub_labels.Value(j)
                sub_color = None
                
                if color_tool.GetColor_s(sub_label, XCAFDoc_ColorGen, color):
                    sub_color = [color.Red(), color.Green(), color.Blue()]
                elif color_tool.GetColor_s(sub_label, XCAFDoc_ColorSurf, color):
                    sub_color = [color.Red(), color.Green(), color.Blue()]
                
                if sub_color is not None:
                    if comp_color is None or sub_color != comp_color:
                        sub_shape = shape_tool.GetShape_s(sub_label)
                        explorer = TopExp_Explorer(sub_shape, TopAbs_FACE)
                        while explorer.More():
                            face = TopoDS.Face_s(explorer.Current())
                            face_color_list.append((face, sub_color))
                            explorer.Next()
        
        # Check free shapes and their sub-shapes
        free_labels = TDF_LabelSequence()
        shape_tool.GetFreeShapes(free_labels)
        
        for i in range(1, free_labels.Length() + 1):
            free_label = free_labels.Value(i)
            
            # Check if free shape has color
            color = Quantity_Color()
            free_color = None
            if color_tool.GetColor_s(free_label, XCAFDoc_ColorGen, color):
                free_color = [color.Red(), color.Green(), color.Blue()]
            elif color_tool.GetColor_s(free_label, XCAFDoc_ColorSurf, color):
                free_color = [color.Red(), color.Green(), color.Blue()]
            
            if free_color is not None:
                free_shape = shape_tool.GetShape_s(free_label)
                explorer = TopExp_Explorer(free_shape, TopAbs_FACE)
                while explorer.More():
                    face = TopoDS.Face_s(explorer.Current())
                    face_color_list.append((face, free_color))
                    explorer.Next()
            
            # Check sub-shapes
            sub_labels = TDF_LabelSequence()
            shape_tool.GetSubShapes_s(free_label, sub_labels)
            for j in range(1, sub_labels.Length() + 1):
                sub_label = sub_labels.Value(j)
                color = Quantity_Color()
                sub_color = None
                
                if color_tool.GetColor_s(sub_label, XCAFDoc_ColorGen, color):
                    sub_color = [color.Red(), color.Green(), color.Blue()]
                elif color_tool.GetColor_s(sub_label, XCAFDoc_ColorSurf, color):
                    sub_color = [color.Red(), color.Green(), color.Blue()]
                
                if sub_color is not None:
                    sub_shape = shape_tool.GetShape_s(sub_label)
                    explorer = TopExp_Explorer(sub_shape, TopAbs_FACE)
                    while explorer.More():
                        face = TopoDS.Face_s(explorer.Current())
                        face_color_list.append((face, sub_color))
                        explorer.Next()
        
        # Get the top-level shape to mesh
        free_labels_mesh = TDF_LabelSequence()
        shape_tool.GetFreeShapes(free_labels_mesh)
        
        if free_labels_mesh.Length() == 0:
            print("No shapes found")
            return
        
        main_shape = shape_tool.GetShape_s(free_labels_mesh.Value(1))
        
        # Mesh the shape
        mesh = BRepMesh_IncrementalMesh(main_shape, 0.1, True)
        mesh.Perform()
        
        # Create VTK polydata
        vtk_points = vtkPoints()
        vtk_triangles = vtkCellArray()
        vtk_colors = vtkUnsignedCharArray()
        vtk_colors.SetNumberOfComponents(3)
        vtk_colors.SetName("Colors")
        
        default_color = [0.7, 0.7, 0.8]
        vertex_offset = 0
        colored_faces = 0
        total_faces = 0
        
        # Track color usage for debugging
        color_usage = {}
        
        # Explore faces and match using IsPartner
        explorer = TopExp_Explorer(main_shape, TopAbs_FACE)
        while explorer.More():
            face = TopoDS.Face_s(explorer.Current())
            location = face.Location()
            facing = BRep_Tool.Triangulation_s(face, location)
            
            if facing:
                total_faces += 1
                transform = location.Transformation()
                
                # Find matching color using IsPartner
                face_color = default_color
                for comp_face, comp_color in face_color_list:
                    if face.IsPartner(comp_face):
                        face_color = comp_color
                        colored_faces += 1
                        break
                
                # Track color usage
                color_key = tuple(face_color)
                color_usage[color_key] = color_usage.get(color_key, 0) + 1
                
                # Convert to 0-255 range
                color_255 = [int(face_color[0] * 255), int(face_color[1] * 255), int(face_color[2] * 255)]
                
                # Add vertices
                for i in range(1, facing.NbNodes() + 1):
                    pnt = facing.Node(i)
                    pnt.Transform(transform)
                    vtk_points.InsertNextPoint(pnt.X(), pnt.Y(), pnt.Z())
                    # Add color per vertex
                    vtk_colors.InsertNextTuple3(color_255[0], color_255[1], color_255[2])
                
                # Add triangles
                for i in range(1, facing.NbTriangles() + 1):
                    triangle = facing.Triangle(i)
                    n1, n2, n3 = triangle.Get()
                    
                    vtk_triangles.InsertNextCell(3)
                    vtk_triangles.InsertCellPoint(vertex_offset + n1 - 1)
                    vtk_triangles.InsertCellPoint(vertex_offset + n2 - 1)
                    vtk_triangles.InsertCellPoint(vertex_offset + n3 - 1)
                
                vertex_offset += facing.NbNodes()
            
            explorer.Next()
        
        # print(f"  Colored {colored_faces}/{total_faces} faces, {vtk_points.GetNumberOfPoints()} vertices")
        # print(f"  Color distribution: {len(color_usage)} unique colors")
        # for color_rgb, count in sorted(color_usage.items(), key=lambda x: -x[1])[:5]:
        #     print(f"    RGB{color_rgb}: {count} faces")
        
        # Create polydata
        polydata = vtkPolyData()
        polydata.SetPoints(vtk_points)
        polydata.SetPolys(vtk_triangles)
        polydata.GetPointData().SetScalars(vtk_colors)
        
        # Create mapper
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        mapper.SetScalarModeToUsePointData()
        mapper.SetColorModeToDirectScalars()  # Use colors directly without lookup table
        mapper.ScalarVisibilityOn()
        
        # Create actor
        self.actor = vtkActor()
        self.actor.SetMapper(mapper)
        
        # Enable lighting for better appearance but set ambient to see colors clearly
        self.actor.GetProperty().SetAmbient(0.5)
        self.actor.GetProperty().SetDiffuse(0.5)
        self.actor.GetProperty().SetSpecular(0.1)

        self.name = step_file.stem


class RobotVTKWidget(QWidget):
    
    CAMERA_POSITION = [854.7, 472.8, 1039.5]
    CAMERA_FOCAL_POINT = [16.6, 268.2, 35.0]
    CAMERA_VIEW_UP = [-0.108724, 0.987913, -0.110486]
    CAMERA_ZOOM = 1.0

    def __init__(self, parent=None, interactive=True):
        super().__init__(parent)
        
        # Store interactive mode
        self.interactive = interactive
        
        # VTK widget
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        
        # Setup renderer
        self.renderer = vtkRenderer()
        self.renderer.SetBackground(0.2, 0.2, 0.2)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        
        # Setup interactor style (interactive or fixed)
        if interactive:
            style = vtkInteractorStyleTrackballCamera()
            self.vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(style)
        else:
            # Completely disable interaction for embedded view
            # Remove interactor style
            self.vtk_widget.GetRenderWindow().GetInteractor().SetInteractorStyle(None)
            # Disable the interactor
            self.vtk_widget.GetRenderWindow().GetInteractor().Disable()
            # Disable mouse tracking
            self.vtk_widget.setEnabled(False)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.vtk_widget)
        
        # Robot parts
        self.support_nacelle = None
        self.nacelle = None
        self.manivelle = None
        self.bras1 = None
        self.bras2 = None
        self.bielle = None
        self.pince = None
        self.gear_right = None
        self.gear_left = None
        self.link_right = None
        self.link_left = None
        self.finger_right = None
        self.finger_left = None
        
        # Joint angles
        self.theta_angle = 0
        self.alpha_angle = 0
        self.beta_angle = 0
        self.mu_angle = 0
        self.gripper_angle = 0
        
        # User-adjustable values
        self.user_x = 0
        self.user_y = 0
        self.user_z = 0
    
    def load_models(self, models_dir):
        """Load robot STEP models"""
        support_file = models_dir / "support_nacelle.STEP"
        if support_file.exists():
            self.support_nacelle = RobotPart(support_file)
            if self.support_nacelle.actor:
                self.renderer.AddActor(self.support_nacelle.actor)
        
        nacelle_file = models_dir / "nacelle.STEP"
        if nacelle_file.exists():
            self.nacelle = RobotPart(nacelle_file)
            if self.nacelle.actor:
                self.renderer.AddActor(self.nacelle.actor)
        
        manivelle_file = models_dir / "manivelle.STEP"
        if manivelle_file.exists():
            self.manivelle = RobotPart(manivelle_file)
            if self.manivelle.actor:
                self.renderer.AddActor(self.manivelle.actor)
        
        bras1_file = models_dir / "bras1.STEP"
        if bras1_file.exists():
            self.bras1 = RobotPart(bras1_file)
            if self.bras1.actor:
                self.renderer.AddActor(self.bras1.actor)

        bras2_file = models_dir / "bras2.STEP"
        if bras2_file.exists():
            self.bras2 = RobotPart(bras2_file)
            if self.bras2.actor:
                self.renderer.AddActor(self.bras2.actor)
        
        bielle_file = models_dir / "bielle.STEP"
        if bielle_file.exists():
            self.bielle = RobotPart(bielle_file)
            if self.bielle.actor:
                self.renderer.AddActor(self.bielle.actor)

        pince_file = models_dir / "pince.STEP"
        if pince_file.exists():
            self.pince = RobotPart(pince_file)
            if self.pince.actor:
                self.renderer.AddActor(self.pince.actor)

        gear_right_file = models_dir / "gear.STEP"
        if gear_right_file.exists():
            self.gear_right = RobotPart(gear_right_file)
            if self.gear_right.actor:
                self.renderer.AddActor(self.gear_right.actor)

        gear_left_file = models_dir / "gear.STEP"
        if gear_left_file.exists():
            self.gear_left = RobotPart(gear_left_file)
            if self.gear_left.actor:
                self.renderer.AddActor(self.gear_left.actor)

        link_right_file = models_dir / "link.STEP"
        if link_right_file.exists():
            self.link_right = RobotPart(link_right_file)
            if self.link_right.actor:
                self.renderer.AddActor(self.link_right.actor)

        link_left_file = models_dir / "link.STEP"
        if link_left_file.exists():
            self.link_left = RobotPart(link_left_file)
            if self.link_left.actor:
                self.renderer.AddActor(self.link_left.actor)

        finger_right_file = models_dir / "finger.STEP"
        if finger_right_file.exists():
            self.finger_right = RobotPart(finger_right_file)
            if self.finger_right.actor:
                self.renderer.AddActor(self.finger_right.actor)

        finger_left_file = models_dir / "finger.STEP"
        if finger_left_file.exists():
            self.finger_left = RobotPart(finger_left_file)
            if self.finger_left.actor:
                self.renderer.AddActor(self.finger_left.actor)

        # Apply initial transforms
        self.update_transforms()
        
        # Setup camera
        if not self.interactive:
            # Set fixed camera view for embedded mode
            self.set_fixed_camera()
        else:
            # Reset camera for interactive mode
            self.renderer.ResetCamera()
        
        self.vtk_widget.GetRenderWindow().Render()
    
    def set_theta(self, angle):
        self.theta_angle = angle
        self.update_transforms()
    
    def set_alpha(self, angle):
        self.alpha_angle = angle
        self.update_transforms()
    
    def set_beta(self, angle):
        self.beta_angle = angle
        self.update_transforms()
    
    def set_mu(self, angle):
        self.mu_angle = angle
        self.update_transforms()
    
    def set_gripper(self, angle):
        self.gripper_angle = angle
        self.update_transforms()
    
    def set_user_x(self, value):
        self.user_x = value
        self.update_transforms()
    
    def set_user_y(self, value):
        self.user_y = value
        self.update_transforms()
    
    def set_user_z(self, value):
        self.user_z = value
        self.update_transforms()
    
    def update_transforms(self):
        """Update robot transformations based on joint angles"""
        if self.support_nacelle and self.support_nacelle.actor:
            transform = vtkTransform()
            self.support_nacelle.actor.SetUserTransform(transform)
        
        if self.nacelle and self.nacelle.actor:
            transform = vtkTransform()
            transform.Translate(0, 125, 0)
            transform.RotateY(self.theta_angle)
            
            self.nacelle.actor.SetUserTransform(transform)
        
        if self.manivelle and self.manivelle.actor:
            transform = vtkTransform()
            transform.Translate(-45, 157, 0)
            transform.Translate(45, 0, 0)
            transform.RotateY(self.theta_angle)
            transform.Translate(-45, 0, 0)
            transform.RotateX(self.alpha_angle)
            
            self.manivelle.actor.SetUserTransform(transform)
        
        if self.bras1 and self.bras1.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            
            self.bras1.actor.SetUserTransform(transform)
        
        if self.bras2 and self.bras2.actor:
            transform = vtkTransform()
            transform.Translate(0, 407, 0)
            transform.RotateY(self.theta_angle)
            transform.Translate(0, -250, 0)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(self.alpha_angle)
            transform.RotateX(-self.beta_angle)
            
            self.bras2.actor.SetUserTransform(transform)
        
        if self.bielle and self.bielle.actor:
            transform = vtkTransform()
            transform.RotateY(self.theta_angle)
            transform.Translate(-18, 157, -59)

            transform.Translate(0, 0, 59)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, -59)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(self.beta_angle)
            
            self.bielle.actor.SetUserTransform(transform)

        if self.pince and self.pince.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)
            
            self.pince.actor.SetUserTransform(transform)

        if self.gear_right and self.gear_right.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)

            transform.Translate(-16.5, -14, 85.5)
            transform.RotateY(-90)
            transform.RotateY(self.gripper_angle)
            
            self.gear_right.actor.SetUserTransform(transform)

        if self.gear_left and self.gear_left.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)

            transform.Translate(16.5, -14, 85.5)
            transform.RotateY(90)
            transform.RotateY(-self.gripper_angle)
            
            self.gear_left.actor.SetUserTransform(transform)

        if self.link_right and self.link_right.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)

            transform.Translate(-10, -14, 123)
            transform.RotateY(180)
            transform.RotateY(self.gripper_angle)
            
            self.link_right.actor.SetUserTransform(transform)

        if self.link_left and self.link_left.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)

            transform.Translate(10, -14, 123)
            transform.RotateY(-self.gripper_angle)
            
            self.link_left.actor.SetUserTransform(transform)

        if self.finger_right and self.finger_right.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)

            transform.Translate(-46.5, -24, 85.5)
            transform.Translate(30, 0, 0)
            transform.RotateY(self.gripper_angle)
            transform.Translate(-30, 0, 0)
            transform.RotateY(-self.gripper_angle)
            
            self.finger_right.actor.SetUserTransform(transform)

        if self.finger_left and self.finger_left.actor:
            transform = vtkTransform()
            transform.Translate(0, 157, 0)
            transform.RotateY(self.theta_angle)
            transform.RotateX(self.beta_angle)
            transform.Translate(0, 250, 0)
            transform.RotateX(-self.beta_angle)
            transform.RotateX(self.alpha_angle)
            transform.Translate(0, 0, 200)
            transform.RotateX(-self.alpha_angle)
            transform.RotateX(-self.mu_angle)
            
            transform.RotateZ(180)
            transform.Translate(-46.5, 24, 85.5)
            transform.Translate(30, 0, 0)
            transform.RotateY(self.gripper_angle)
            transform.Translate(-30, 0, 0)
            transform.RotateY(-self.gripper_angle)
            
            self.finger_left.actor.SetUserTransform(transform)

        self.vtk_widget.GetRenderWindow().Render()
    
    def set_fixed_camera(self):
        """Set camera to fixed position and orientation"""
        camera = self.renderer.GetActiveCamera()
        camera.SetPosition(self.CAMERA_POSITION[0], self.CAMERA_POSITION[1], self.CAMERA_POSITION[2])
        camera.SetFocalPoint(self.CAMERA_FOCAL_POINT[0], self.CAMERA_FOCAL_POINT[1], self.CAMERA_FOCAL_POINT[2])
        camera.SetViewUp(self.CAMERA_VIEW_UP[0], self.CAMERA_VIEW_UP[1], self.CAMERA_VIEW_UP[2])
        camera.Zoom(self.CAMERA_ZOOM)
        self.renderer.ResetCameraClippingRange()
    
    def print_camera_parameters(self):
        """Print current camera parameters for copying to constants"""
        camera = self.renderer.GetActiveCamera()
        position = camera.GetPosition()
        focal_point = camera.GetFocalPoint()
        view_up = camera.GetViewUp()
        
        print("\n" + "="*60)
        print("CAMERA PARAMETERS")
        print("="*60)
        print(f"CAMERA_POSITION = [{position[0]:.1f}, {position[1]:.1f}, {position[2]:.1f}]")
        print(f"CAMERA_FOCAL_POINT = [{focal_point[0]:.1f}, {focal_point[1]:.1f}, {focal_point[2]:.1f}]")
        print(f"CAMERA_VIEW_UP = [{view_up[0]:.6f}, {view_up[1]:.6f}, {view_up[2]:.6f}]")
        print("="*60 + "\n")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot STEP Viewer - VTK")
        self.setGeometry(100, 100, 1200, 800)

        self.setStyleSheet("background-color: rgb(51, 51, 51);")

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # VTK viewer
        self.viewer = RobotVTKWidget()
        main_layout.addWidget(self.viewer, stretch=3)

        # Controls panel
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        main_layout.addWidget(controls, stretch=1)

        # Joint 1 slider
        controls_layout.addWidget(QLabel("Theta:"))
        self.theta_slider = QSlider(Qt.Horizontal)
        self.theta_slider.setRange(-180, 180)
        self.theta_slider.setValue(0)
        self.theta_slider.valueChanged.connect(self.on_theta_changed)
        controls_layout.addWidget(self.theta_slider)
        self.theta_label = QLabel("0°")
        controls_layout.addWidget(self.theta_label)

        # Joint 2 slider
        controls_layout.addWidget(QLabel("alpha:"))
        self.alpha_slider = QSlider(Qt.Horizontal)
        self.alpha_slider.setRange(-90, 90)
        self.alpha_slider.setValue(0)
        self.alpha_slider.valueChanged.connect(self.on_alpha_changed)
        controls_layout.addWidget(self.alpha_slider)
        self.alpha_label = QLabel("0°")
        controls_layout.addWidget(self.alpha_label)

        # Joint 3 slider
        controls_layout.addWidget(QLabel("beta"))
        self.beta_slider = QSlider(Qt.Horizontal)
        self.beta_slider.setRange(-90, 90)
        self.beta_slider.setValue(0)
        self.beta_slider.valueChanged.connect(self.on_beta_changed)
        controls_layout.addWidget(self.beta_slider)
        self.beta_label = QLabel("0°")
        controls_layout.addWidget(self.beta_label)

        # Mu slider
        controls_layout.addWidget(QLabel("mu:"))
        self.mu_slider = QSlider(Qt.Horizontal)
        self.mu_slider.setRange(-90, 90)
        self.mu_slider.setValue(0)
        self.mu_slider.valueChanged.connect(self.on_mu_changed)
        controls_layout.addWidget(self.mu_slider)
        self.mu_label = QLabel("0°")
        controls_layout.addWidget(self.mu_label)

        # Gripper slider
        controls_layout.addWidget(QLabel("gripper:"))
        self.gripper_slider = QSlider(Qt.Horizontal)
        self.gripper_slider.setRange(-90, 90)
        self.gripper_slider.setValue(0)
        self.gripper_slider.valueChanged.connect(self.on_gripper_changed)
        controls_layout.addWidget(self.gripper_slider)
        self.gripper_label = QLabel("0°")
        controls_layout.addWidget(self.gripper_label)

        # User X slider
        controls_layout.addWidget(QLabel("User X:"))
        self.user_x_slider = QSlider(Qt.Horizontal)
        self.user_x_slider.setRange(-100, 100)
        self.user_x_slider.setValue(0)
        self.user_x_slider.valueChanged.connect(self.on_user_x_changed)
        controls_layout.addWidget(self.user_x_slider)
        self.user_x_label = QLabel("0")
        controls_layout.addWidget(self.user_x_label)

        # User Y slider
        controls_layout.addWidget(QLabel("User Y:"))
        self.user_y_slider = QSlider(Qt.Horizontal)
        self.user_y_slider.setRange(-100, 100)
        self.user_y_slider.setValue(0)
        self.user_y_slider.valueChanged.connect(self.on_user_y_changed)
        controls_layout.addWidget(self.user_y_slider)
        self.user_y_label = QLabel("0")
        controls_layout.addWidget(self.user_y_label)

        # User Z slider
        controls_layout.addWidget(QLabel("User Z:"))
        self.user_z_slider = QSlider(Qt.Horizontal)
        self.user_z_slider.setRange(-100, 100)
        self.user_z_slider.setValue(0)
        self.user_z_slider.valueChanged.connect(self.on_user_z_changed)
        controls_layout.addWidget(self.user_z_slider)
        self.user_z_label = QLabel("0")
        controls_layout.addWidget(self.user_z_label)

        controls_layout.addStretch()
        
        # Print Camera button
        self.print_camera_btn = QPushButton("Print Camera Parameters")
        self.print_camera_btn.clicked.connect(self.on_print_camera)
        controls_layout.addWidget(self.print_camera_btn)

        # Load models
        models_dir = Path(__file__).parent / "Models"
        if models_dir.exists():
            self.viewer.load_models(models_dir)
        else:
            print(f"Models directory not found: {models_dir}")

    def on_theta_changed(self, value):
        self.theta_label.setText(f"{value}°")
        self.viewer.set_theta(value)

    def on_alpha_changed(self, value):
        self.alpha_label.setText(f"{value}°")
        self.viewer.set_alpha(value)

    def on_beta_changed(self, value):
        self.beta_label.setText(f"{value}°")
        self.viewer.set_beta(value)

    def on_mu_changed(self, value):
        self.mu_label.setText(f"{value}°")
        self.viewer.set_mu(value)

    def on_gripper_changed(self, value):
        self.gripper_label.setText(f"{value}°")
        self.viewer.set_gripper(value)

    def on_user_x_changed(self, value):
        self.user_x_label.setText(f"{value}")
        self.viewer.set_user_x(value)

    def on_user_y_changed(self, value):
        self.user_y_label.setText(f"{value}")
        self.viewer.set_user_y(value)

    def on_user_z_changed(self, value):
        self.user_z_label.setText(f"{value}")
        self.viewer.set_user_z(value)
    
    def on_print_camera(self):
        """Print current camera parameters"""
        self.viewer.print_camera_parameters()


def main():
    """Standalone mode with controls"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
