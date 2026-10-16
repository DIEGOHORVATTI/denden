import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from gi.repository import Gdk, GLib

from .config import APP_NAME, ICONS_DIR


def videos_dir():
    folder = _snap_videos_dir() or _user_videos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def open_videos_dir():
    subprocess.Popen(["xdg-open", str(videos_dir())])


def notify(message):
    print(message, file=sys.stderr)
    if shutil.which("notify-send"):
        icon = str(ICONS_DIR / "denden.svg")
        subprocess.Popen(["notify-send", "-a", APP_NAME, "-i", icon, APP_NAME, message])


def screen_size():
    root = Gdk.get_default_root_window()
    return _even(root.get_width()), _even(root.get_height())


def work_area():
    try:
        return _i3_focused_workspace()
    except (OSError, ValueError, KeyError, StopIteration, subprocess.SubprocessError):
        return _primary_monitor()


def _snap_videos_dir():
    real_home = os.environ.get("SNAP_REAL_HOME")
    return Path(real_home) / "Videos" if real_home else None


def _user_videos_dir():
    folder = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
    return Path(folder) if folder else Path.home() / "Videos"


def _i3_focused_workspace():
    output = subprocess.run(["i3-msg", "-t", "get_workspaces"], capture_output=True, timeout=2).stdout
    rect = next(workspace["rect"] for workspace in json.loads(output) if workspace["focused"])
    return rect["x"], rect["y"], rect["width"], rect["height"]


def _primary_monitor():
    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor() or display.get_monitor(0)
    geometry = monitor.get_geometry()
    return geometry.x, geometry.y, geometry.width, geometry.height


def _even(number):
    return number - number % 2
