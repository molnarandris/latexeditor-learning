# window.py
#
# Copyright 2020 Andras Molnar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gi
import os

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from .documentmanager import Documentmanager
from .pdfviewer import PdfViewer
from .processrunner import GAsyncSpawn

gi.require_version('GtkSource', '3.0')
from gi.repository import GtkSource




def makeactions(win):
    compile_action = Gio.SimpleAction.new('compile', None)
    compile_action.connect('activate', lambda action, param: win.do_compile())
    win.add_action(compile_action)
    win.get_application().set_accels_for_action('win.compile', ['F5'])

# Saving and reloading window geometry with Gio.settings
class WindowStateSaver:
    def __init__(self, win):

        win.connect("destroy", self.on_destroy)
        win.connect("size-allocate", self.on_size_allocate)
        win.connect("window-state-event", self.on_window_state_event)
        win.paned.connect("size-allocate", self.on_handle_move)

        # Get window geometry from settings
        settings = Gio.Settings.new(
            "com.github.molnarandris.latexeditor.window-state"
        )
        self.current_width = settings.get_int("width")
        self.current_height = settings.get_int("height")
        self.current_maximized = settings.get_boolean('maximized')
        self.current_fullscreen = settings.get_boolean('fullscreen')
        self.current_paned_pos = settings.get_double("paned-position")

        # Set window geometry
        # FIXME: if saved maximized, the unmaximize does not work well.
        # I guess have to set the position first or something...
        win.set_default_size(self.current_width, self.current_height)
        if self.current_maximized:
            win.maximize()
        if self.current_fullscreen:
            win.fullscreen()
        # Careful, after setting maximized: stored the previous state...
        # Ok, no control over order...
        win.paned.set_position(self.current_paned_pos*self.current_width)

    def on_handle_move(self, widget, event):
        self.current_paned_pos = widget.get_position()/widget.get_allocated_width()
        return False

    def on_window_state_event(self, widget, event):
        state = event.get_window().get_state()
        self.current_maximized = bool(state & Gdk.WindowState.MAXIMIZED)
        self.current_fullscreen = bool(state & Gdk.WindowState.FULLSCREEN)
        return False

    def on_size_allocate(self, widget, allocation):
        # if not (self.current_maximized or self.current_fullscreen):
        self.current_width, self.current_height = widget.get_size()
        return False

    # On destroy, save window state. Note that at destroy one should not use
    # window.get_size() and so. This is why the current geometry properties.
    # Panded position needs extra care. We want to save it as percentage maybe.
    def on_destroy(self, widget):
        settings = Gio.Settings.new(
            "com.github.molnarandris.latexeditor.window-state"
        )
        settings.set_int("width", self.current_width)
        settings.set_int("height", self.current_height)
        settings.set_boolean("maximized", self.current_maximized)
        settings.set_boolean("fullscreen", self.current_fullscreen)
        settings.set_double("paned-position", self.current_paned_pos)
        return False



@Gtk.Template(filename="src/window.ui")
class MathwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'MathwriterWindow'

    # Tell builder about GtkSource and my PdfViewer    
    GObject.type_register(GtkSource.View)
    GObject.type_register(PdfViewer)

    # import all
    sourceview = Gtk.Template.Child()
    btn_open   = Gtk.Template.Child()
    btn_save   = Gtk.Template.Child()
    header_bar = Gtk.Template.Child()
    paned      = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #self.init_template()
        
        # Get different components from .ui file and add the rest
        self.buffer = self.sourceview.get_buffer()
        lang_manager = GtkSource.LanguageManager()
        self.buffer.set_language(lang_manager.get_language('latex'))
        self.pdf_viewer=PdfViewer()
        self.paned.add(self.pdf_viewer)
        self.docmanager = Documentmanager(self, self.buffer, self.pdf_viewer)
        self.btn_open.connect("clicked", self.open_callback)
        self.btn_save.connect("clicked", self.save_callback)
        self.state_saver = WindowStateSaver(self)
        # Add actions
        makeactions(self)
        # Without this, the pdf viewer does not show
        self.show_all()

    # File chooser, then pass the selected file to the doc manager
    def open_callback(self, button):
        dialog = Gtk.FileChooserNative.new(
            "Please choose a file",
            self,
            Gtk.FileChooserAction.OPEN,
        )
        # Note that if running from builder, the path will be /run/user/...
        # Unless you install the flatpak app first.

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            msg = self.docmanager.open_file(filename)
            if msg is None:
                self.header_bar.set_subtitle(filename)
            else:
                dialog = Gtk.MessageDialog(
                    self,
                    0,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    msg,)
                dialog.run()
                dialog.destroy()

    # If no file opened, then set the file with file chooser. Call file saver
    # of doc manager. The file writing can also fail. In that case, choose
    # another file.
    def save_callback(self, button):
        if self.docmanager.tex is None:
            dialog = Gtk.FileChooserNative.new(
                    "Please choose a file",
                    self,
                    Gtk.FileChooserAction.SAVE,
            )
            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                self.docmanager.tex = dialog.get_filename()
            dialog.destroy()

        msg = self.docmanager.save_file()
        if msg is None:
            self.header_bar.set_subtitle(self.docmanager.tex)
        else:
            dialog = Gtk.MessageDialog(
                self,
                0,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                msg,)
            dialog.run()
            dialog.destroy()

    def do_compile(self):
        self.save_callback(None)
        spawn = GAsyncSpawn()
#        cmd = ['/usr/bin/ls', self.docmanager.tex]
        cmd = ['/usr/bin/pdflatex', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory', self.docmanager.dir, self.docmanager.tex]
        spawn.connect("process-done", self.on_compile_finish)
        spawn.run(cmd)

    def on_compile_finish(self, sender, ret):
        if ret == 0:
            print("compile finished succesfully")
            self.pdf_viewer.reload()
        else:
            print("compile finished with error")
        sender.disconnect_by_func(self.on_compile_finish)
        sender.my_destroy()
