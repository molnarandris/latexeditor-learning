import os

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GLib


# This class is a wrapper to run processes. 
# Planned use: compilation and synctex.
# Should make it such that compilation does not block the UI
# One has to be able to cancel.
class GAsyncSpawn(GObject.GObject):
    """ GObject class to wrap GLib.spawn_async().

    Use:
        s = GAsyncSpawn()
        s.connect('process-done', mycallback)
        s.run(command)
            #command: list of strings
    """
    __gsignals__ = {
        'process-done': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                         (GObject.TYPE_INT, )),
        'stdout-data': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                        (GObject.TYPE_STRING, )),
        'stderr-data': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                        (GObject.TYPE_STRING, )),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self.fout = None
        self.ferr = None

    def run(self, cmd):
        r = GLib.spawn_async(cmd,
                             flags=GLib.SPAWN_DO_NOT_REAP_CHILD,
                             standard_output=True,
                             standard_error=True)
        self.pid, idin, idout, iderr = r
        self.fout = os.fdopen(idout, "r")
        self.ferr = os.fdopen(iderr, "r")

        GLib.child_watch_add(self.pid, self._on_done)
        self.outwatch = GLib.io_add_watch(self.fout, GLib.IO_IN, self._on_stdout)
        self.errwatch = GLib.io_add_watch(self.ferr, GLib.IO_IN, self._on_stderr)
        return self.pid
        
    def my_destroy(self):
        GLib.Source.remove(self.outwatch)
        GLib.Source.remove(self.errwatch)

    def _on_done(self, pid, retval, *argv):
        self.emit("process-done", retval)

    def _emit_std(self, name, value):
        self.emit(name+"-data", value)

    def _on_stdout(self, fobj, cond):
        self._emit_std("stdout", fobj.readline())
        return True

    def _on_stderr(self, fobj, cond):
        self._emit_std("stderr", fobj.readline())
        return True

