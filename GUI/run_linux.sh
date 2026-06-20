#!/usr/bin/env bash
# Dev launcher: runs the GUI from source on Linux.
# Works from any directory and prefers the project's .venv if present.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Pick the interpreter: project venv first, then whatever python is on PATH.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
else
    PYTHON="$(command -v python3 || command -v python)"
fi

# Force the X11 (xcb) Qt platform; works on both X11 and Wayland (via XWayland).
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

cd "$REPO_ROOT"
exec "$PYTHON" GUI/main.py "$@"
