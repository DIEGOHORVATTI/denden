import math

from .config import ICONS_DIR
from .ffmpeg import MIC_SOURCE, PC_AUDIO_SOURCE, audio_args
from .shape import circle_region

ICON_FILES = ("denden.svg", "denden-tray.svg", "denden-rec.svg")


def run():
    for size in (120, 261, 600):
        _check_circle(size)
    _checkaudio_args_mapping()
    assert all((ICONS_DIR / name).exists() for name in ICON_FILES)
    print("ok")


def _check_circle(size):
    region = circle_region(size)
    rects = [region.get_rectangle(index) for index in range(region.num_rectangles())]
    area = sum(rect.width * rect.height for rect in rects)
    assert abs(area - math.pi * (size / 2) ** 2) / area < 0.02, (size, area)
    assert region.contains_point(size // 2, size // 2)
    assert not region.contains_point(0, 0) and not region.contains_point(size - 1, size - 1)


def _checkaudio_args_mapping():
    assert audio_args([]) == []
    assert "1:a" in audio_args([MIC_SOURCE])
    assert "[1:a][2:a]amix=inputs=2:duration=longest:normalize=0[a]" in audio_args([PC_AUDIO_SOURCE, MIC_SOURCE])
