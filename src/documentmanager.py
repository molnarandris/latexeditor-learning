from gi.repository import Gtk
import os
#import sys


class Documentmanager:
    def __init__(self, win, buf, pdfviewer):
        self.win = win
        self.buffer = buf
        self.pdfviewer = pdfviewer
        self.dir = None
        self.tex = None

    @property
    def pdf(self):
        return os.path.splitext(self.tex)[0] + '.pdf'

    def open_file(self, fname):
        if fname is None:
            return "You did not select a file or the file got moved."
        if not os.path.exists(fname):
            return "The selected file does not exist"
        with open(fname, 'r') as f:
            try:
                self.buffer.set_text(f.read())
                self.tex = fname
                self.dir = os.path.dirname(fname)
            except IOError:
                return "Error reading file"
        self.pdfviewer.open_file(self.pdf)
        return None

    def save_file(self):
        if self.tex is None:
            return "There is no file to save"
        # FIXME: I think works now but it's not supposed to be like this
        # see os.access documentation.
        if os.path.exists(self.tex) and not os.access(self.tex, os.W_OK):
            return "Permission error"
        with open(self.tex, 'w+') as f:
            try:
                f.write(
                    self.buffer.get_text(
                        self.buffer.get_start_iter(),
                        self.buffer.get_end_iter(),
                        True
                     )
                )
                print("saved file")
                return None
            except (IOError):
                return "Error writing file"


