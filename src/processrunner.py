from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GLib


# Note that cannot change cwd. If that  is needed, use gio.subprocesslauncher
# Even though I don't get how that works.
# In my case just can specify latexmk output directory.
# No problem with synctex
class ProcessRunner(GObject.GObject):

    __gsignals__ = {
        'finished': (GObject.SIGNAL_RUN_LAST, None, ()),
    }


    def __init__(self,cmd):
        super().__init__()
        
        self.proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE)
        self.cancellable = Gio.Cancellable.new()
        self.proc.communicate_utf8_async(None, self.cancellable, self.callback, None)
        self.result = None
        self.stdout = None
        self.stderr = None

    def callback(self,sucprocess: Gio.Subprocess, result: Gio.AsyncResult, data):
        try:
            _, self.stdout, self.stderr = self.proc.communicate_utf8_finish(result)
            self.result = self.proc.get_exit_status()
            self.emit('finished')
        except GLib.Error as err:
            if err.domain == 'g-io-error-quark':
                return

    def cancel(self):
        self.cancellable.cancel()
