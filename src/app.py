import sys
import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, Gio
from .window import MathwriterWindow


def quit(app):
    for win in app.get_windows(): win.close()

# Actions tied to the application
def makeactions(app):
    close_action = Gio.SimpleAction.new('close', None)
    close_action.connect('activate', lambda action, param: quit(app))
    app.add_action(close_action)
    app.set_accels_for_action('app.close', ['<ctrl>q'])




class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.github.molnarandris.mathwriter',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        makeactions(self)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MathwriterWindow(application=self)
        win.present()

