import signal

from gi.repository import Gio, GLib, Gtk

from .bubble import Bubble
from .config import APP_ID
from .menu import build_menu
from .recorder import Recorder
from .tray import Tray


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.recorder = Recorder()
        self._open_menu = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        self.bubble = Bubble(on_record=self.toggle_record, on_menu=self._popup_at_pointer)
        self.tray = Tray(on_open_menu=self._popup_from_tray)
        self._register_actions()
        self._refresh_tray()
        GLib.timeout_add_seconds(1, self._tick)
        for signum in (signal.SIGINT, signal.SIGTERM):
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signum, self.quit_app)

    def do_activate(self):
        self.bubble.show_camera()

    def toggle_record(self):
        self.recorder.toggle()
        self._refresh_tray()

    def quit_app(self):
        if self.recorder.active:
            self.recorder.stop()
        self.bubble.hide_camera()
        self.quit()
        return GLib.SOURCE_REMOVE

    def _register_actions(self):
        actions = {"record": self.toggle_record, "camera": self.bubble.toggle_camera, "quit": self.quit_app}
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_, run=callback: run())
            self.add_action(action)

    def _tick(self):
        self.bubble.keep_on_top()
        if self.recorder.crashed:
            self.recorder.stop()
        self._refresh_tray()
        return GLib.SOURCE_CONTINUE

    def _refresh_tray(self):
        if self.recorder.active:
            self.tray.show_recording(self.recorder.elapsed)
        else:
            self.tray.show_idle()

    def _build_menu(self):
        self._open_menu = build_menu(self.recorder, self.bubble, self.toggle_record, self.quit_app)
        return self._open_menu

    def _popup_at_pointer(self, event):
        self._build_menu().popup_at_pointer(event)

    def _popup_from_tray(self, button, time):
        self.tray.popup(self._build_menu(), button, time)
