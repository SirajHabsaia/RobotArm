#!/usr/bin/env bash
# Build a single-file Linux distributable: dist/RobotArmGUI-x86_64.AppImage
#
# Wraps the PyInstaller onedir bundle (see build_linux.sh) into an AppImage that
# uses the "uruntime" runtime, which auto-falls back to extract-and-run when the
# host lacks libfuse2. The result runs on any x86-64 Linux machine with no deps.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/robotarm-appimage-tools"
APPIMAGETOOL="$CACHE/appimagetool"
URUNTIME="$CACHE/uruntime"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
URUNTIME_URL="https://github.com/VHSgunzo/uruntime/releases/download/v0.5.8/uruntime-appimage-squashfs-x86_64"

mkdir -p "$CACHE"
[[ -x "$APPIMAGETOOL" ]] || { echo "Downloading appimagetool..."; curl -fSL -o "$APPIMAGETOOL" "$APPIMAGETOOL_URL"; chmod +x "$APPIMAGETOOL"; }
[[ -x "$URUNTIME"     ]] || { echo "Downloading uruntime...";     curl -fSL -o "$URUNTIME"     "$URUNTIME_URL";     chmod +x "$URUNTIME"; }

# 1. Make sure the PyInstaller bundle exists.
if [[ ! -x "dist/RobotArmGUI/RobotArmGUI" ]]; then
    echo "PyInstaller bundle missing; building it first..."
    ./build_linux.sh
fi

# 2. Scaffold the AppDir (hardlink the heavy payload — fast, no duplication).
APPDIR="build/RobotArmGUI.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -al dist/RobotArmGUI/RobotArmGUI dist/RobotArmGUI/_internal "$APPDIR/usr/bin/"
cp images/robot.png "$APPDIR/RobotArmGUI.png"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec "$HERE/usr/bin/RobotArmGUI" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/RobotArmGUI.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=RobotArmGUI
Comment=Chess-playing robot arm control and visualization
Exec=RobotArmGUI
Icon=RobotArmGUI
Categories=Utility;
Terminal=false
EOF

# 3. Build the AppImage. APPIMAGE_EXTRACT_AND_RUN lets appimagetool itself run
#    without libfuse2 on this build host. Use max-level zstd with a large block
#    size to minimize the output file size.
rm -f dist/RobotArmGUI-x86_64.AppImage
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" \
    --comp zstd \
    --mksquashfs-opt -Xcompression-level --mksquashfs-opt 22 \
    --mksquashfs-opt -b --mksquashfs-opt 1M \
    --runtime-file "$URUNTIME" "$APPDIR" dist/RobotArmGUI-x86_64.AppImage

echo
echo "Done. Single-file app: dist/RobotArmGUI-x86_64.AppImage"
echo "Run it with:  chmod +x dist/RobotArmGUI-x86_64.AppImage && ./dist/RobotArmGUI-x86_64.AppImage"
