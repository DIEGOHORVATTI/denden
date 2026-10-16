import os
from pathlib import Path

APP_ID = "dev.horvatti.DenDen"
APP_NAME = "Den Den"
ICONS_DIR = Path(__file__).resolve().parent.parent / "icons"

CAMERA_DEVICE = os.environ.get("DENDEN_CAM", "/dev/video0")
VAAPI_DEVICE = "/dev/dri/renderD128"
CAPTURE_SIZE = 480

BUBBLE_SIZE = 260
MIN_BUBBLE_SIZE = 120
MAX_BUBBLE_SIZE = 600
RESIZE_STEP = 20
SCREEN_MARGIN = 30
HOVER_OPACITY = 0.15
