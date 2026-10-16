import sys

from gi.repository import Gio, GLib

from . import selftest
from .app import App
from .config import APP_ID, APP_NAME

REMOTE_ACTIONS = {"--gravar": "record", "--camera": "camera"}


def main(argv):
    option = argv[1] if len(argv) > 1 else None
    if option == "--selftest":
        return selftest.run()
    if option in REMOTE_ACTIONS:
        return send_to_running_instance(REMOTE_ACTIONS[option])
    GLib.set_prgname("denden")
    GLib.set_application_name(APP_NAME)
    return App().run(argv[:1])


def send_to_running_instance(action):
    client = Gio.Application(application_id=APP_ID)
    try:
        client.register(None)
    except GLib.Error:
        sys.exit(f"{APP_NAME} não respondeu")
    if not client.get_is_remote():
        sys.exit(f"{APP_NAME} não está aberto")
    client.activate_action(action, None)
    client.get_dbus_connection().flush_sync(None)
