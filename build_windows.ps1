# Build a single-file Windows executable: dist\RobotArmGUI.exe
#
# Windows analogue of build_appimage_linux.sh. Produces one self-contained .exe
# (PyInstaller "onefile") that bundles the Python runtime, Qt/VTK/OCP/onnxruntime
# and all assets, extracting to a temp folder at launch. The target machine needs
# no Python install. Uses the same size-optimized RobotArmGUI.spec as the Linux
# build, just in onefile mode (ONEFILE=1).
#
# Usage (from the repo root, in PowerShell):
#   .\build_windows.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# Prefer the project venv; fall back to whatever python is on PATH.
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

# PyInstaller is a build-time tool, not a runtime dependency.
& $Python -m PyInstaller --version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..."
    & $Python -m pip install pyinstaller
}

if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist)  { Remove-Item -Recurse -Force dist }

# Build in single-file mode (see the ONEFILE branch in RobotArmGUI.spec).
$env:ONEFILE = "1"
try {
    & $Python -m PyInstaller RobotArmGUI.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }
} finally {
    Remove-Item Env:\ONEFILE -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Done. Single-file app: dist\RobotArmGUI.exe"
Write-Host "Distribute that one .exe; no Python needed on the target machine."
