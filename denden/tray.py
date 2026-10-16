from gi.repository import Gio, Gtk

from .config import APP_NAME, ICONS_DIR


class Tray:
    def __init__(self, on_open_menu):
        self._icon = Gtk.StatusIcon()
        self._icon.set_title(APP_NAME)
        self._icon.connect("activate", lambda _icon: on_open_menu(0, Gtk.get_current_event_time()))
        self._icon.connect("popup-menu", lambda _icon, button, time: on_open_menu(button, time))

    def show_idle(self):
        self._show("denden-tray.svg", APP_NAME)

    def show_recording(self, elapsed):
        self._show("denden-rec.svg", f"{APP_NAME}: gravando {elapsed}")

    def popup(self, menu, button, time):
        menu.popup(None, None, Gtk.StatusIcon.position_menu, self._icon, button, time)

    def _show(self, icon_file, tooltip):
        self._icon.set_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(str(ICONS_DIR / icon_file))))
        self._icon.set_tooltip_text(tooltip)
