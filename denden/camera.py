import subprocess
import threading

from .config import CAPTURE_SIZE
from .ffmpeg import camera_command

FRAME_BYTES = CAPTURE_SIZE * CAPTURE_SIZE * 3


class Camera:
    def __init__(self, on_frame):
        self._process = subprocess.Popen(camera_command(), stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
        threading.Thread(target=self._read_frames, args=(on_frame,), daemon=True).start()

    def stop(self):
        self._process.terminate()

    def _read_frames(self, on_frame):
        while len(frame := self._process.stdout.read(FRAME_BYTES)) == FRAME_BYTES:
            on_frame(frame)
