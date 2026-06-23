# Chess-Playing Robot Arm

A robotic arm that plays physical chess, built as my third-year engineering project at EMINES. A camera reads the board, Stockfish picks the move, a time-optimal trajectory is planned, and Arduino firmware drives the arm to make the move — all controlled from a PySide6 desktop app.

![Robot arm](images/robot.png)
![GUI Manip](images/gui_manip.png)

## This work includes

<details>
<summary><b>Arduino firmware</b> — real-time arm control (PlatformIO, megaatmega2560)</summary>

Reads a serial waypoint protocol, executes interpolated trajectories, and streams telemetry back.

- [main.cpp](Arduino/RoboticArm/src/main.cpp) — entrypoint: serial loop, trajectory execution, feedback
- [serial_commands.cpp](Arduino/RoboticArm/src/serial_commands.cpp) — protocol parsing & dispatch
- [trajectory.cpp](Arduino/RoboticArm/src/trajectory.cpp) — waypoint scheduling & interpolation
- [cartesian.cpp](Arduino/RoboticArm/src/cartesian.cpp) — line & circle path generators
- [kinematics.cpp](Arduino/RoboticArm/src/kinematics.cpp) — direct/inverse kinematics, mu/gamma helpers
- [control.cpp](Arduino/RoboticArm/src/control.cpp) — stepper control & Dynamixel gripper
- [feedback.cpp](Arduino/RoboticArm/src/feedback.cpp) · [reset.cpp](Arduino/RoboticArm/src/reset.cpp) · [config.cpp](Arduino/RoboticArm/src/config.cpp) — telemetry, homing, hardware config

![Firmware architecture](images/diagram_dark.png)

</details>

<details>
<summary><b>CNN classification & position prediction</b></summary>

- **Square classifier** — labels each of the 64 squares as `black` / `empty` / `white`.
- **Position regression** — locates the true piece centre within its square, so the arm grabs the actual piece instead of the geometric centre.

See [GUI/Chess/board_detector.py](GUI/Chess/board_detector.py) and [AI/Inference/](AI/Inference/).

</details>

<details>
<summary><b>Training scripts</b></summary>

- [AI/train/train_classification.py](AI/train/train_classification.py) — square classifier
- [AI/train/train_position.py](AI/train/train_position.py) — piece-centre regressor
- [AI/label_tool.py](AI/label_tool.py) — labeling helper

</details>

<details>
<summary><b>Trajectory optimization</b></summary>

Chess moves become Cartesian pick-and-place paths, then TOPPRA retimes them into time-optimal joint waypoints that respect motor speed/acceleration limits, with deterministic gripper-action timing. See [GUI/planner.py](GUI/planner.py) and [GUI/kinematics.py](GUI/kinematics.py).

</details>

<details>
<summary><b>Desktop GUI</b> — PySide6 app with 3D view, control, drawing & chess</summary>

Real-time 3D visualization ([GUI/ThreeD.py](GUI/ThreeD.py)) and full robot control from [GUI/main.py](GUI/main.py).

**Menus**
- **Home** — project overview and serial connection menu.
- **Manip** — manual control with live 3D visualization.
- **Program** — save and execute waypoint lists.
- **Chess AI** — vision + engine pipeline and robot move execution ([GUI/Chess/](GUI/Chess/)).
- **Drawing** — draw paths for the arm to follow ([GUI/Draw/](GUI/Draw/)).

</details>

## How to run

1. Download the GUI executable for your OS (Windows / Linux) from the latest release and run it.
2. Flash the firmware (`.ino`) from the same release to the Arduino.

## Build & run from source

<details>
<summary><b>Run from source</b></summary>

```bash
git clone https://github.com/SirajHabsaia/RobotArm.git && cd RobotArm
```

**Firmware** — open [Arduino/RoboticArm/platformio.ini](Arduino/RoboticArm/platformio.ini) in PlatformIO, then build & upload (`megaatmega2560`).

**GUI**
1. Create a virtual environment and install deps:
   ```bash
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt # (make sure to have build tools for TOPPRA)
   ```
2. Download the assets archive from the latest release and merge it into `GUI/` (3D models, CNN weights, sounds).
3. Download the [Stockfish binary](https://github.com/official-stockfish/Stockfish/releases) for your OS into `.stockfish/`. Keep the expected filename (`stockfish-ubuntu-x86-64` on Linux, `stockfish-windows-x86-64.exe` on Windows) or update the path in [GUI/gui.py](GUI/gui.py).
4. Run it:
   ```bash
   python GUI/main.py
   ```

</details>

<details>
<summary><b>Train the models</b></summary>

Download the dataset from the latest release into `AI/`, then:

```bash
python AI/train/train_classification.py   # square classifier  -> model.pth
python AI/train/train_position.py         # piece-centre regressor -> model_position.pth
python AI/export_onnx.py                   # export both to ONNX for the GUI
```

The GUI runs inference with **onnxruntime** (not PyTorch), so after retraining
you must re-run `AI/export_onnx.py` to refresh `GUI/Chess/model.onnx` and
`GUI/Chess/model_position.onnx`. PyTorch is only needed for training/export.

</details>

<details>
<summary><b>Build the GUI executable</b></summary>

PyInstaller produces a portable "onedir" bundle in `dist/RobotArmGUI/`:

```bash
pyinstaller RobotArmGUI.spec      # any platform
./build_linux.sh                  # Linux convenience wrapper
```

Single-file distributable (the whole app as one file):

```bash
./build_appimage_linux.sh         # Linux:   -> dist/RobotArmGUI-x86_64.AppImage
```

```powershell
.\build_windows.ps1               # Windows: -> dist\RobotArmGUI.exe
```

Both single-file builds share the same size-optimized `RobotArmGUI.spec`
(`build_windows.ps1` just sets `ONEFILE=1` for PyInstaller's onefile mode).

On a minimal Linux target you may also need `libxcb-cursor0` (`sudo apt install libxcb-cursor0`).

</details>
