#!/usr/bin/env bash
# Build a portable Linux app bundle into dist/RobotArmGUI/ (PyInstaller onedir:
# one launcher executable + an _internal/ folder with all libs and assets).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Prefer the project venv; fall back to system python.
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3 || command -v python)"

# PyInstaller is a build-time tool, not a runtime dependency.
"$PYTHON" -m PyInstaller --version >/dev/null 2>&1 || "$PYTHON" -m pip install pyinstaller

rm -rf build dist
"$PYTHON" -m PyInstaller RobotArmGUI.spec --noconfirm

echo
echo "Done. Portable app bundle: dist/RobotArmGUI/"
echo "Run it with:  ./dist/RobotArmGUI/RobotArmGUI"
echo "Distribute by zipping the whole dist/RobotArmGUI/ folder."
