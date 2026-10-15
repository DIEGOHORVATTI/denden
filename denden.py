#!/usr/bin/env python3
"""Den Den: câmera redonda flutuante + gravador de tela para X11/i3.

A bolha: arrastar com o botão esquerdo, tamanho na rodinha, botão do meio grava/para,
botão direito abre o menu; com o mouse em cima ela fica transparente.
Bandeja (i3bar): qualquer clique abre o menu.
CLI: `denden --gravar` e `denden --camera` controlam a instância aberta (bom para bindsym).
"""
import json
import math
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

# ponytail: Gtk.StatusIcon é deprecado, mas é o único que fala XEmbed, o protocolo da bandeja do i3bar
warnings.simplefilter("ignore", DeprecationWarning)

APP_ID = "dev.horvatti.DenDen"
ICONS = Path(__file__).resolve().parent / "icons"
CAM = os.environ.get("DENDEN_CAM", "/dev/video0")
VAAPI = "/dev/dri/renderD128"
CAP = 480  # ponytail: captura fixa e o cairo escala; bolha > 480px fica levemente borrada
HOVER_OPACITY = 0.15
MIN_SIZE, MAX_SIZE, STEP = 120, 600, 20


def circle_region(size):
    """Região X Shape em forma de círculo, montada linha a linha."""
    r = size / 2
    region = cairo.Region()
    for y in range(size):
        dy = y + 0.5 - r
        half = math.sqrt(max(r * r - dy * dy, 0))
        x0 = round(r - half)
        if (w := round(r + half) - x0) > 0:
            region.union(cairo.RectangleInt(x0, y, w, 1))
    return region


def videos_dir():
    d = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) or str(Path.home() / "Videos")
    Path(d).mkdir(parents=True, exist_ok=True)
    return Path(d)


def work_area():
    """Área do workspace focado sem a i3bar (o i3 não publica _NET_WORKAREA)."""
    try:
        out = subprocess.run(["i3-msg", "-t", "get_workspaces"], capture_output=True, timeout=2).stdout
        r = next(ws["rect"] for ws in json.loads(out) if ws["focused"])
        return r["x"], r["y"], r["width"], r["height"]
    except Exception:
        mon = Gdk.Display.get_default().get_primary_monitor() or Gdk.Display.get_default().get_monitor(0)
        g = mon.get_geometry()
        return g.x, g.y, g.width, g.height


def notify(msg):
    print(msg, file=sys.stderr)
    if shutil.which("notify-send"):
        subprocess.Popen(["notify-send", "-a", "Den Den", "-i", str(ICONS / "denden.svg"), "Den Den", msg])


def file_icon(name):
    return Gio.FileIcon.new(Gio.File.new_for_path(str(ICONS / name)))


class Camera:
    def __init__(self, on_frame):
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-f", "v4l2", "-i", CAM,
             "-vf", f"crop=ih:ih,scale={CAP}:{CAP}:flags=fast_bilinear",
             "-fps_mode", "passthrough",  # facetimehd manda timestamps tortos; sem isso o ffmpeg descarta ~99% dos frames
             "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
            stdout=subprocess.PIPE, stdin=subprocess.DEVNULL,
        )
        threading.Thread(target=self._loop, args=(on_frame,), daemon=True).start()

    def _loop(self, on_frame):
        n = CAP * CAP * 3
        while len(chunk := self.proc.stdout.read(n)) == n:
            on_frame(chunk)

    def stop(self):
        self.proc.terminate()


class Recorder:
    proc = None
    path = None
    started = 0.0
    pc_audio = True  # monitor da saída padrão = o que toca no PC
    mic = True

    @property
    def active(self):
        return self.proc is not None

    @property
    def elapsed(self):
        s = int(time.monotonic() - self.started)
        return f"{s // 60:02d}:{s % 60:02d}"

    def start(self):
        root = Gdk.get_default_root_window()
        w, h = root.get_width() & ~1, root.get_height() & ~1
        self.path = videos_dir() / time.strftime("tela-%Y-%m-%d_%H-%M-%S.mp4")
        grab = ["-f", "x11grab", "-framerate", "30", "-video_size", f"{w}x{h}",
                "-thread_queue_size", "512", "-i", os.environ.get("DISPLAY", ":0")]
        srcs = [s for s, on in (("@DEFAULT_MONITOR@", self.pc_audio), ("default", self.mic)) if on]
        audio = [a for s in srcs for a in ("-f", "pulse", "-thread_queue_size", "512", "-i", s)]
        if len(srcs) == 2:
            audio += ["-filter_complex", "[1:a][2:a]amix=inputs=2:duration=longest:normalize=0[a]",
                      "-map", "0:v", "-map", "[a]"]
        elif srcs:
            audio += ["-map", "0:v", "-map", "1:a"]
        audio_enc = ["-c:a", "aac", "-b:a", "160k"] if srcs else []
        if os.path.exists(VAAPI):
            pre = ["-vaapi_device", VAAPI]
            enc = ["-vf", "format=nv12,hwupload", "-c:v", "h264_vaapi", "-qp", "24"]
        else:  # ponytail: x264 em CPU esquenta; só cai aqui sem GPU Intel/AMD
            pre = []
            enc = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p"]
        cmd = ["ffmpeg", "-loglevel", "error", "-y", *pre, *grab, *audio, *enc, *audio_enc,
               "-movflags", "+faststart", str(self.path)]
        env = {**os.environ, "LIBVA_DRIVER_NAME": os.environ.get("LIBVA_DRIVER_NAME", "i965")}
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, env=env)
        self.started = time.monotonic()

    def stop(self):
        proc, self.proc = self.proc, None
        try:
            proc.communicate(b"q", timeout=20)  # "q" fecha o mp4 direito; kill corromperia o arquivo
        except subprocess.TimeoutExpired:
            proc.kill()
        if proc.returncode == 0 and self.path.exists():
            notify(f"Gravação salva: {self.path}")
        else:
            notify(f"ffmpeg falhou ({proc.returncode}); rode `denden` no terminal para ver o erro")


class Bubble(Gtk.Window):
    def __init__(self, app):
        # POPUP = override-redirect: o i3 não gerencia, então fica em todo workspace e por cima de tela cheia
        super().__init__(type=Gtk.WindowType.POPUP, title="Den Den")
        self.app = app
        self.size = 260
        self.frame = None
        self.mirror = True
        self.drag = None
        self.cam = None

        screen = self.get_screen()
        if (visual := screen.get_rgba_visual()) and screen.is_composited():
            self.set_visual(visual)  # com picom a borda do círculo sai suave
        self.set_app_paintable(True)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK
                        | Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("button-release-event", self.on_release)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("scroll-event", self.on_scroll)
        self.connect("enter-notify-event", lambda *_: Gtk.Widget.set_opacity(self, HOVER_OPACITY))
        self.connect("leave-notify-event", lambda *_: self.drag or Gtk.Widget.set_opacity(self, 1.0))

        self.apply_size()
        x, y, w, h = work_area()
        self.move(x + w - self.size - 30, y + h - self.size - 30)

    @property
    def shown(self):
        return self.cam is not None

    def show_cam(self):
        if not self.shown:
            self.cam = Camera(self.on_frame)
            self.show_all()

    def hide_cam(self):
        if self.shown:
            self.hide()
            self.cam.stop()  # escondida = câmera desligada (luz apaga, CPU zera)
            self.cam = self.frame = None

    def apply_size(self):
        self.set_size_request(self.size, self.size)
        self.resize(self.size, self.size)
        self.shape_combine_region(circle_region(self.size))
        self.queue_draw()

    def on_frame(self, chunk):  # thread da câmera
        self.frame = chunk
        GLib.idle_add(self.queue_draw)

    def on_draw(self, _w, cr):
        s = self.size
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.arc(s / 2, s / 2, s / 2, 0, 2 * math.pi)
        cr.clip()
        if frame := self.frame:
            pb = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(frame), GdkPixbuf.Colorspace.RGB,
                                                 False, 8, CAP, CAP, CAP * 3)
            if self.mirror:
                cr.translate(s, 0)
                cr.scale(-1, 1)
            cr.scale(s / CAP, s / CAP)
            Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        else:
            cr.set_source_rgb(0.15, 0.15, 0.15)
        cr.paint()
        return True  # nada de indicador na bolha: ela sai no vídeo

    def on_press(self, _w, e):
        if e.button == 1:
            x, y = self.get_position()
            self.drag = (e.x_root - x, e.y_root - y)
            Gtk.Widget.set_opacity(self, 1.0)
        elif e.button == 2:
            self.app.toggle_record()
        elif e.button == 3:
            self.app.popup_menu(event=e)
        return True

    def on_release(self, _w, e):
        if e.button == 1:
            self.drag = None
        return True

    def on_motion(self, _w, e):
        if self.drag:
            self.move(int(e.x_root - self.drag[0]), int(e.y_root - self.drag[1]))
        return True

    def on_scroll(self, _w, e):
        d = {Gdk.ScrollDirection.UP: STEP, Gdk.ScrollDirection.DOWN: -STEP}.get(e.direction, 0)
        if e.direction == Gdk.ScrollDirection.SMOOTH:
            d = -STEP if e.delta_y > 0 else STEP
        new = max(MIN_SIZE, min(MAX_SIZE, self.size + d))
        if new != self.size:
            x, y = self.get_position()
            half = (new - self.size) // 2
            self.size = new
            self.move(x - half, y - half)  # cresce a partir do centro
            self.apply_size()
        return True


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.rec = Recorder()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()  # vive pela bandeja mesmo com a bolha escondida
        for name, fn in (("record", self.toggle_record), ("camera", self.toggle_camera), ("quit", self.quit_app)):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_, f=fn: f())
            self.add_action(action)

        self.bubble = Bubble(self)
        self.tray = Gtk.StatusIcon()
        self.tray.set_title("Den Den")
        self.tray.connect("activate", lambda icon: self.popup_menu(t=Gtk.get_current_event_time()))
        self.tray.connect("popup-menu", lambda icon, button, t: self.popup_menu(button, t))
        self.update_tray()

        GLib.timeout_add_seconds(1, self.tick)
        for sig in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, sig, self.quit_app)

    def do_activate(self):
        self.bubble.show_cam()  # abrir de novo pelo launcher só traz a bolha de volta

    def update_tray(self):
        if self.rec.active:
            self.tray.set_from_gicon(file_icon("denden-rec.svg"))
            self.tray.set_tooltip_text(f"Den Den: gravando {self.rec.elapsed}")
        else:
            self.tray.set_from_gicon(file_icon("denden-tray.svg"))
            self.tray.set_tooltip_text("Den Den")

    def tick(self):
        if (win := self.bubble.get_window()) and self.bubble.shown and not self.bubble.drag:
            win.raise_()  # ponytail: i3 reempilha ao focar tela cheia; raise a cada 1s basta
        if self.rec.active and self.rec.proc.poll() is not None:  # ffmpeg morreu sozinho
            self.rec.stop()
        self.update_tray()
        return True

    def popup_menu(self, button=0, t=0, event=None):
        m = Gtk.Menu()

        def item(label, fn, check=None, sensitive=True):
            it = Gtk.CheckMenuItem(label=label, active=check) if check is not None else Gtk.MenuItem(label=label)
            it.set_sensitive(sensitive)
            it.connect("activate", lambda _i: fn())
            m.append(it)

        item(f"■ Parar gravação ({self.rec.elapsed})" if self.rec.active else "● Gravar tela", self.toggle_record)
        idle = not self.rec.active  # áudio só muda entre gravações
        item("Áudio do PC", lambda: setattr(self.rec, "pc_audio", not self.rec.pc_audio), self.rec.pc_audio, idle)
        item("Microfone", lambda: setattr(self.rec, "mic", not self.rec.mic), self.rec.mic, idle)
        m.append(Gtk.SeparatorMenuItem())
        item("Mostrar câmera", self.toggle_camera, check=self.bubble.shown)
        item("Espelhar câmera", self.toggle_mirror, check=self.bubble.mirror)
        item("Abrir pasta de vídeos", lambda: subprocess.Popen(["xdg-open", str(videos_dir())]))
        m.append(Gtk.SeparatorMenuItem())
        item("Sair", self.quit_app)
        m.show_all()
        if event:
            m.popup_at_pointer(event)
        else:
            m.popup(None, None, Gtk.StatusIcon.position_menu, self.tray, button, t)
        self._menu = m  # mantém referência viva enquanto aberto

    def toggle_record(self):
        self.rec.stop() if self.rec.active else self.rec.start()
        self.update_tray()

    def toggle_camera(self):
        self.bubble.hide_cam() if self.bubble.shown else self.bubble.show_cam()

    def toggle_mirror(self):
        self.bubble.mirror = not self.bubble.mirror
        self.bubble.queue_draw()

    def quit_app(self):
        if self.rec.active:
            self.rec.stop()
        self.bubble.hide_cam()
        self.quit()
        return False


def remote(action):
    """Manda a ação para o Den Den já aberto, sem abrir outra."""
    cli = Gio.Application(application_id=APP_ID)
    cli.register(None)
    if not cli.get_is_remote():
        sys.exit("Den Den não está aberto")
    cli.activate_action(action, None)
    cli.get_dbus_connection().flush_sync(None)


def selftest():
    for s in (120, 261, 600):
        reg = circle_region(s)
        rects = [reg.get_rectangle(i) for i in range(reg.num_rectangles())]
        area = sum(r.width * r.height for r in rects)
        assert abs(area - math.pi * (s / 2) ** 2) / area < 0.02, (s, area)
        assert reg.contains_point(s // 2, s // 2)
        assert not reg.contains_point(0, 0) and not reg.contains_point(s - 1, s - 1)
    assert all((ICONS / f).exists() for f in ("denden.svg", "denden-tray.svg", "denden-rec.svg"))
    print("ok")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--selftest":
        return selftest()
    if arg in ("--gravar", "--camera"):
        return remote({"--gravar": "record", "--camera": "camera"}[arg])
    GLib.set_prgname("denden")
    GLib.set_application_name("Den Den")
    return App().run(sys.argv[:1])


if __name__ == "__main__":
    sys.exit(main())
