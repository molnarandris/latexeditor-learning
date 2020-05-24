import gi
import os
import re

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from .documentmanager import Documentmanager
from .processrunner import ProcessRunner

gi.require_version('GtkSource', '3.0')
from gi.repository import GtkSource
gi.require_version('EvinceDocument', '3.0')
from gi.repository import EvinceDocument, EvinceView


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
        self.current_file = settings.get_string("file")

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
        msg = win.docmanager.open_file(self.current_file)
        if msg is None:
            win.header_bar.set_subtitle(self.current_file)
        else:
            print("Error opening last file\n"+msg)
            self.current_file = ""
        
    def on_file_save(self,f):
        self.current_file = f

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
        settings.set_string("file", self.current_file)
        return False



@Gtk.Template(filename="src/window.ui")
class MathwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'MathwriterWindow'

    # Tell builder about GtkSource and my PdfViewer    
    GObject.type_register(GtkSource.View)
    #GObject.type_register(PdfViewer)

    # import all
    sourceview = Gtk.Template.Child()
    header_bar = Gtk.Template.Child()
    paned      = Gtk.Template.Child()
    pdf_scroll = Gtk.Template.Child()
    open_dialog= Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Setting up Evince as Pdf viewer
        EvinceDocument.init()
        #self.pdf_viewer=PdfViewer(self)
        self.pdf_viewer = EvinceView.View()
        model = EvinceView.DocumentModel()
        self.pdf_viewer.set_model(model)
        self.pdf_viewer.model = model
        self.pdf_scroll.add(self.pdf_viewer)
        
        
        # Get different components from .ui file and add the rest
        self.buffer = self.sourceview.get_buffer()
        lang_manager = GtkSource.LanguageManager()
        self.buffer.set_language(lang_manager.get_language('latex'))
        self.docmanager = Documentmanager(self, self.buffer, self.pdf_viewer)
        self.state_saver = WindowStateSaver(self)
        # EvinceView emits sync-source on CTRL+left click, I cannot change that. (It's hard-coded.)
        # To have better synctex support (not only line), 
        # one has to either preprocess the tex file before compile to contain more rows,
        # or intercept CTRL+click, look for the word under the pointer
        # And then find that in the current line
        self.pdf_viewer.connect("sync-source",self.on_sync_source)
        # Add actions
        self.makeactions()
        # Without this, the pdf viewer does not show
        self.show_all()
        
    # File chooser, then pass the selected file to the doc manager
    def on_open(self, action, value):
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
                self.state_saver.on_file_save(filename)
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
    def on_save(self, action, value):
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

    def on_compile(self, action, value):
        self.on_save(action, value)
        cmd = ['/usr/bin/latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory='+self.docmanager.dir, self.docmanager.tex]
        proc = ProcessRunner(cmd)
        proc.connect('finished', self.on_compile_finished)

    def on_compile_finished(self,sender):
        if sender.result == 0:
            print("Compile succesful")
            self.pdf_viewer.reload()
            i = self.buffer.get_iter_at_offset(self.buffer.props.cursor_position)
            sl = EvinceDocument.SourceLink.new(self.docmanager.tex,i.get_line(),i.get_line_offset())
            print("sl finished")
            self.pdf_viewer.highlight_forward_search(sl)
            print("synctex agruments: line: " + str(i.get_line()) + " offset: " + str(i.get_line_offset()))
#            cmd = ['/usr/bin/synctex', 'view', '-i', str(i.get_line()) + ":" + str(i.get_line_offset()) + ":" + self.docmanager.tex, '-o', self.docmanager.pdf]
#            proc = ProcessRunner(cmd)
#            proc.connect('finished', self.on_synctex_finished)
        else: 
            print("Compile failed")
            print("output:\n ------------------------- \n"+sender.stdout)
            print("err\n-------------------\n"+sender.stderr)
            
    def on_sync_source(self,sender,sourcelink):
        line = sourcelink.line -1
        col = sourcelink.col
        print("Synctex edit. Line: " + str(line) + " col: " + str(col))
        if col <0:
            col=0
        it = self.buffer.get_iter_at_line_offset(line,col)
        self.buffer.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,False,0,0)
        self.sourceview.grab_focus()
        
    def makeactions(self):
        action = Gio.SimpleAction.new('compile', None)
        action.connect('activate', self.on_compile)
        self.add_action(action)
        self.get_application().set_accels_for_action('win.compile', ['F5'])
            
        action = Gio.SimpleAction.new('open', None)
        action.connect('activate', self.on_open)
        self.add_action(action)
        self.get_application().set_accels_for_action('win.open', ['<ctrl>o'])

        action = Gio.SimpleAction.new('save', None)
        action.connect('activate', self.on_save)
        self.add_action(action)
        self.get_application().set_accels_for_action('win.save', ['<ctrl>s'])

