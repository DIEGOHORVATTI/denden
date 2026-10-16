import subprocess
import time

from .ffmpeg import MIC_SOURCE, PC_AUDIO_SOURCE, ffmpeg_env, recording_command
from .system import notify, screen_size, videos_dir


class Recorder:
    def __init__(self):
        self.pc_audio = True
        self.mic = True
        self._process = None
        self._output = None
        self._started_at = 0.0

    @property
    def active(self):
        return self._process is not None

    @property
    def crashed(self):
        return self.active and self._process.poll() is not None

    @property
    def elapsed(self):
        seconds = int(time.monotonic() - self._started_at)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def toggle(self):
        self.stop() if self.active else self.start()

    def toggle_pc_audio(self):
        self.pc_audio = not self.pc_audio

    def toggle_mic(self):
        self.mic = not self.mic

    def start(self):
        self._output = videos_dir() / time.strftime("tela-%Y-%m-%d_%H-%M-%S.mp4")
        command = recording_command(self._output, screen_size(), self._audio_sources())
        self._process = subprocess.Popen(command, stdin=subprocess.PIPE, env=ffmpeg_env())
        self._started_at = time.monotonic()

    def stop(self):
        process, self._process = self._process, None
        _finish_gracefully(process)
        if process.returncode == 0 and self._output.exists():
            notify(f"Gravação salva: {self._output}")
        else:
            notify(f"ffmpeg falhou ({process.returncode}); rode `denden` no terminal para ver o erro")

    def _audio_sources(self):
        wanted = ((PC_AUDIO_SOURCE, self.pc_audio), (MIC_SOURCE, self.mic))
        return [source for source, enabled in wanted if enabled]


def _finish_gracefully(process):
    try:
        process.communicate(b"q", timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
