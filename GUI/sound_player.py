"""
Lightweight sound playback using the operating system's own tools.

No third-party libraries are used (nothing from pip). Playback is asynchronous
(non-blocking) and best-effort: a missing player or file never raises.

  - Windows: PowerShell's System.Media.SoundPlayer (.NET, ships with Windows)
  - Linux:   aplay (ALSA) / paplay (PulseAudio) / ffplay, whichever exists
"""

import os
import sys
import shutil
import subprocess


def play_sound(path: str) -> None:
    """Play a .wav file asynchronously via an OS command (best-effort)."""
    if not path or not os.path.isfile(path):
        return

    try:
        if sys.platform.startswith("win"):
            # PlaySync() plays the whole clip inside the spawned PowerShell
            # process; we don't wait on it, so it's non-blocking for us.
            ps_path = path.replace("'", "''")  # escape single quotes for PS
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 f"(New-Object System.Media.SoundPlayer '{ps_path}').PlaySync()"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            # Linux: use the first available command-line player.
            player = (shutil.which("aplay")
                      or shutil.which("paplay")
                      or shutil.which("ffplay"))
            if player is None:
                return
            if player.endswith("ffplay"):
                args = [player, "-nodisp", "-autoexit", "-loglevel", "quiet", path]
            else:
                args = [player, path]
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        # Sound is non-essential; never let it break the app.
        pass
