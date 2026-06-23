# -*- mode: python ; coding: utf-8 -*-
#
# Size-optimized PyInstaller spec.
#
# Key savings vs. a naive build:
#   * PySide6: do NOT collect_all() (that drags in all of Qt — WebEngine, QML,
#     Multimedia, translations, ~600 MB). The app only uses QtCore/QtGui/QtWidgets,
#     so we let PyInstaller's hook pull just those, and exclude the heavy modules.
#   * No PyTorch: inference runs on onnxruntime (models exported to .onnx via
#     AI/export_onnx.py), so torch/torchvision (~600 MB) are excluded entirely.
#   * strip=True: strip debug symbols from all shared libraries (OCP, VTK, Qt,
#     onnxruntime ...) — typically cuts the .so bulk substantially.
#   * Drop Qt translation catalogs (.qm) — not used.
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_all

# ONEFILE=1 -> a single self-extracting executable (the Windows analogue of the
# Linux AppImage: one file, extracts to a temp dir at launch). Default (unset)
# -> the portable onedir bundle in dist/RobotArmGUI/ used by build_linux.sh.
ONEFILE = os.environ.get('ONEFILE', '') == '1'

# Stripping debug symbols meaningfully shrinks the ELF/.so payload on Linux, but
# on Windows it needs GNU binutils (strip.exe) on PATH and does little for PE
# files, so skip it there.
STRIP = sys.platform != 'win32'

datas = [
    ('GUI/params.json', '.'),
    ('GUI/Models', 'Models'),
    ('GUI/Chess/model.onnx', 'Chess'),
    ('GUI/Chess/model_position.onnx', 'Chess'),
    ('GUI/Chess/pieces', 'Chess/pieces'),
    ('GUI/Sounds', 'Sounds'),
    ('.stockfish', '.stockfish'),
]
binaries = []
hiddenimports = ['matplotlib.backends.backend_qtagg']
hiddenimports += collect_submodules('matplotlib.backends')

# VTK: bundle only the modules the 3D viewer (GUI/ThreeD.py) actually uses, plus
# the rendering-factory modules required for an OpenGL render. PyInstaller pulls
# each module's shared-library dependency closure automatically. Collecting *all*
# of vtkmodules instead would drag in ~150 MB of unused VTK-m accelerators,
# filters, IO, imaging, volume rendering, etc. This curated set was verified to
# perform a complete offscreen render on its own.
hiddenimports += [
    'vtkmodules.vtkCommonCore',
    'vtkmodules.vtkCommonDataModel',
    'vtkmodules.vtkCommonTransforms',
    'vtkmodules.vtkRenderingCore',
    'vtkmodules.vtkRenderingOpenGL2',     # concrete OpenGL render window/renderer/actor
    'vtkmodules.vtkRenderingUI',          # interactor/window backend
    'vtkmodules.vtkRenderingFreeType',    # default text/2D property support
    'vtkmodules.vtkInteractionStyle',     # trackball camera interaction
    'vtkmodules.util',
    'vtkmodules.util.numpy_support',
    'vtkmodules.qt',
    'vtkmodules.qt.QVTKRenderWindowInteractor',
]

# OCP (OpenCASCADE) is needed at runtime to load the .STEP arm models; it loads
# implementation libraries dynamically, so collect everything it ships.
tmp_ret = collect_all('OCP')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Qt modules the app never imports. Excluding them keeps PyInstaller's PySide6
# hook from bundling these (very large) libraries and their dependencies.
excludes = [
    # Web stack (QtWebEngineCore alone is ~190 MB)
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick',
    'PySide6.QtWebChannel', 'PySide6.QtWebSockets',
    # QML / Quick
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2',
    # Multimedia / audio / charts / data viz / 3D
    'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtSpatialAudio',
    'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtGraphs',
    'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput', 'PySide6.Qt3DLogic',
    'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
    # PDF, SQL, networking, designer/help/test tooling
    'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtSql', 'PySide6.QtNetwork',
    'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtUiTools', 'PySide6.QtHelp',
    # Connectivity / sensors / misc Qt add-ons
    'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtSensors', 'PySide6.QtPositioning',
    'PySide6.QtSerialPort', 'PySide6.QtSerialBus', 'PySide6.QtRemoteObjects',
    'PySide6.QtScxml', 'PySide6.QtStateMachine', 'PySide6.QtTextToSpeech',
    'PySide6.QtHttpServer',
    # Other GUI toolkits / dev tools never used at runtime
    'PyQt5', 'PyQt6', 'tkinter', '_tkinter', 'pytest', 'IPython',
    # Inference runs on onnxruntime; PyTorch (and its export deps) are only used
    # for training / exporting models, never in the packaged app.
    'torch', 'torchvision', 'onnx', 'onnxscript', 'sympy', 'mpmath',
    # The `vtk` meta-package does `from vtkmodules.all import *`, dragging in ALL
    # of VTK. We use vtkmodules.* directly, so exclude it. OCP's VTK bridge
    # (OCP.IVtk*) imports `vtk`; the 3D viewer never uses it (OCP is only used to
    # read STEP files), so exclude those too. This keeps VTK to the curated set.
    'vtk', 'OCP.IVtk', 'OCP.IVtkOCC', 'OCP.IVtkTools', 'OCP.IVtkVTK',
]

a = Analysis(
    [os.path.join('GUI', 'main.py')],
    pathex=['GUI'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

# --- Prune runtime-irrelevant payload from the collected trees ----------------
# Match on the in-bundle destination path (first tuple element).
_PRUNE_SUBSTRINGS = (
    # Qt translation catalogs (.qm) and leftover web/qml resources, if any
    'PySide6/Qt/translations/', 'PySide6\\Qt\\translations\\',
    'PySide6/translations/', 'PySide6\\translations\\',
    'qtwebengine', 'QtWebEngine', 'Qt/qml/', 'Qt\\qml\\',
)


def _prune(entries):
    kept = []
    for entry in entries:
        dest = entry[0].replace('\\', '/')
        if any(s.replace('\\', '/') in dest for s in _PRUNE_SUBSTRINGS):
            continue
        kept.append(entry)
    return kept


a.datas = _prune(a.datas)
a.binaries = _prune(a.binaries)

pyz = PYZ(a.pure)

if ONEFILE:
    # Single self-contained executable: dist/RobotArmGUI(.exe). All binaries and
    # data files are packed into the EXE and extracted to a temp dir at launch.
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='RobotArmGUI',
        debug=False,
        bootloader_ignore_signals=False,
        strip=STRIP,
        upx=False,
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    # Portable onedir bundle: dist/RobotArmGUI/ (launcher + _internal/).
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='RobotArmGUI',
        debug=False,
        bootloader_ignore_signals=False,
        strip=STRIP,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=STRIP,
        upx=False,
        upx_exclude=[],
        name='RobotArmGUI',
    )
