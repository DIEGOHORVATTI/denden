from gi.repository import Gtk

from .system import open_videos_dir


def build_menu(recorder, bubble, on_record, on_quit):
    menu = Gtk.Menu()
    idle = not recorder.active
    _add_item(menu, _record_label(recorder), on_record)
    _add_check(menu, "Áudio do PC", recorder.pc_audio, recorder.toggle_pc_audio, enabled=idle)
    _add_check(menu, "Microfone", recorder.mic, recorder.toggle_mic, enabled=idle)
    menu.append(Gtk.SeparatorMenuItem())
    _add_check(menu, "Mostrar câmera", bubble.camera_on, bubble.toggle_camera)
    _add_check(menu, "Espelhar câmera", bubble.mirror, bubble.toggle_mirror)
    _add_item(menu, "Abrir pasta de vídeos", open_videos_dir)
    menu.append(Gtk.SeparatorMenuItem())
    _add_item(menu, "Sair", on_quit)
    menu.show_all()
    return menu


def _record_label(recorder):
    return f"■ Parar gravação ({recorder.elapsed})" if recorder.active else "● Gravar tela"


def _add_item(menu, label, on_activate):
    _append(menu, Gtk.MenuItem(label=label), on_activate)


def _add_check(menu, label, active, on_toggle, enabled=True):
    item = Gtk.CheckMenuItem(label=label, active=active)
    item.set_sensitive(enabled)
    _append(menu, item, on_toggle)


def _append(menu, item, callback):
    item.connect("activate", lambda _item: callback())
    menu.append(item)
