import os
import subprocess
from functools import cache

from .config import CAMERA_DEVICE, CAPTURE_SIZE, VAAPI_DEVICE

PC_AUDIO_SOURCE = "@DEFAULT_MONITOR@"
MIC_SOURCE = "default"
AAC_ENCODER = ["-c:a", "aac", "-b:a", "160k"]


def ffmpeg_env():
    return {**os.environ, "LIBVA_DRIVER_NAME": os.environ.get("LIBVA_DRIVER_NAME", "i965")}


def camera_command():
    square = f"crop=ih:ih,scale={CAPTURE_SIZE}:{CAPTURE_SIZE}:flags=fast_bilinear"
    return ["ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", CAMERA_DEVICE, "-vf", square,
            "-fps_mode", "passthrough", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]


def recording_command(output, screen, audio_sources):
    return ["ffmpeg", "-loglevel", "error", "-y", *_hardware_device(), *_screen_input(screen),
            *audio_args(audio_sources), *_video_encoder(), "-movflags", "+faststart", str(output)]


@cache
def vaapi_available():
    if not os.path.exists(VAAPI_DEVICE):
        return False
    probe = ["ffmpeg", "-v", "error", "-vaapi_device", VAAPI_DEVICE, "-f", "lavfi", "-i", "nullsrc=s=64x64",
             "-frames:v", "1", "-vf", "format=nv12,hwupload", "-c:v", "h264_vaapi", "-f", "null", "-"]
    return subprocess.run(probe, capture_output=True, env=ffmpeg_env(), timeout=10).returncode == 0


def _hardware_device():
    return ["-vaapi_device", VAAPI_DEVICE] if vaapi_available() else []


def _screen_input(screen):
    width, height = screen
    return ["-f", "x11grab", "-framerate", "30", "-video_size", f"{width}x{height}",
            "-thread_queue_size", "512", "-i", os.environ.get("DISPLAY", ":0")]


def audio_args(sources):
    if not sources:
        return []
    inputs = [arg for source in sources for arg in ("-f", "pulse", "-thread_queue_size", "512", "-i", source)]
    return [*inputs, *_audio_mapping(len(sources)), *AAC_ENCODER]


def _audio_mapping(count):
    if count == 1:
        return ["-map", "0:v", "-map", "1:a"]
    streams = "".join(f"[{index}:a]" for index in range(1, count + 1))
    mix = f"{streams}amix=inputs={count}:duration=longest:normalize=0[a]"
    return ["-filter_complex", mix, "-map", "0:v", "-map", "[a]"]


def _video_encoder():
    if vaapi_available():
        return ["-vf", "format=nv12,hwupload", "-c:v", "h264_vaapi", "-qp", "24"]
    return ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p"]
