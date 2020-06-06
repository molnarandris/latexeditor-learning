import gi, os, re

from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from .processrunner import ProcessRunner
from .completion import LatexCompletionProvider
#from .logparser import LatexLogParser

gi.require_version('GtkSource', '4')
from gi.repository import GtkSource

gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
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
        if self.current_file != "":
            win.on_tex_open(None,self.current_file)
    
    # Hmm, so far I call this externally. I don't like it. Should be automatic.    
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


# Now this is the main window that is being displayed.
@Gtk.Template(filename="src/window.ui")
class MathwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'MathwriterWindow'

    # Tell builder about GtkSource and my PdfViewer    
    GObject.type_register(GtkSource.View)
    #GObject.type_register(PdfViewer)

    # import all used components from the template
    sourceview = Gtk.Template.Child()
    header_bar = Gtk.Template.Child()
    paned      = Gtk.Template.Child()
    pdf_scroll = Gtk.Template.Child()
    log_view   = Gtk.Template.Child()
    view_stack = Gtk.Template.Child()

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
        # EvinceView emits sync-source on CTRL+left click, I cannot change that. (It's hard-coded.)
        # To have better synctex support (not only line), 
        # one has to either preprocess the tex file before compile to contain more rows,
        # or intercept CTRL+click, look for the word under the pointer
        # And then find that in the current line
        self.pdf_viewer.connect("sync-source",self.on_sync_source)
        
        
        # Get different components from .ui file and add the rest
        self.buffer = self.sourceview.get_buffer()
        lang_manager = GtkSource.LanguageManager()
        self.buffer.set_language(lang_manager.get_language('latex'))
        self.tex = None
        # Adding the command completion. So far it just completes \begin{equation}. 
        self.completion = self.sourceview.get_completion()
        latex_completion_provider = LatexCompletionProvider()
        self.completion.add_provider(latex_completion_provider)
        self.latex_completion_provider = latex_completion_provider        

        self.log_buffer = self.log_view.get_buffer()
        
        self.state_saver = WindowStateSaver(self)
        # Add actions
        self.makeactions()
        # Without this, the pdf viewer does not show
        self.show_all()
        
    # Open callback. If value is None, then do choose a file. Otherwise open value.
    def on_tex_open(self, action, value):
        if value is None:
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

            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.ACCEPT:
                filename = dialog.get_filename()
            else:
                return
        else:
            filename = value
            
        f = GtkSource.File.new()
        f.set_location(Gio.File.new_for_path(filename))
        loader = GtkSource.FileLoader.new(self.buffer,f)
        loader.load_async(GLib.PRIORITY_DEFAULT,None,None,None,self.on_tex_open_finish,None)

    # Callback for GtkSource to finish the async loading of the latex file
    def on_tex_open_finish(self,loader,result,data):
        if loader.load_finish(result):
            filename = loader.get_location().get_path()
            self.tex = filename
            print("Loading the tex file finished succesfully.")
            self.header_bar.set_subtitle(filename)
            self.state_saver.on_file_save(filename)
            self.pdf_reload()
        else:
            msg = "File loading failed"
            dialog = Gtk.MessageDialog(
                self,
                0,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                msg,)
            dialog.run()
            dialog.destroy()
            
    # Reload the pdf. 
    def pdf_reload(self):
            pdfname = os.path.splitext(self.tex)[0] + '.pdf'
            #should do error check here. 
            pdf = Gio.File.new_for_path(pdfname)
            pdf_loader = EvinceView.JobLoadGFile.new(pdf,EvinceDocument.DocumentLoadFlags.NONE)
            pdf_loader.connect("finished", self.on_pdf_load_finished)
            pdf_loader.run()
        
    # Callback for Evince's async pdf loader.
    def on_pdf_load_finished(self,job):
        if job.is_failed():
            print("Loading the Pdf has failed")
        else:
            self.pdf_viewer.model.set_document(job.document)
            
    # If no file opened, then set the file with file chooser. Call file saver
    # of doc manager. The file writing can also fail. In that case, choose
    # another file.
    def on_save(self, action, value):
        filename = self.tex
        if filename is None:
            dialog = Gtk.FileChooserNative.new(
                    "Please choose a file",
                    self,
                    Gtk.FileChooserAction.SAVE,
            )
            response = dialog.run()
            if response == Gtk.ResponseType.ACCEPT:
                filename = dialog.get_filename()
            dialog.destroy()
            
        f = GtkSource.File.new()
        f.set_location(Gio.File.new_for_path(filename))
        saver = GtkSource.FileSaver.new(self.buffer,f)
        saver.save_async(GLib.PRIORITY_DEFAULT,None,None,None,self.on_save_finished,None)

    # Callback for GtkSource's async file saver. Saves the latex file.
    def on_save_finished(self,source,result,data):
        # Did the file saving succeed?
        if source.save_finish(result):
            # Set the self.tex field to point to the tex file 
            self.tex = source.get_location().get_path()
            # And display the filename in the subtitle of the window
            self.header_bar.set_subtitle(self.tex)
        else:
            # File saving failed, tell the user about it but do nothing else.
            msg = "File saving failed"
            dialog = Gtk.MessageDialog(
                self,
                0,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                msg,)
            dialog.run()
            dialog.destroy()
            
    # The callback when compilation requested. Wired into the compile button 
    # in the UI. 
    def on_compile(self, action, value):
        self.on_save(action, value)
        directory = os.path.dirname(self.tex)
        cmd = ['/usr/bin/latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory=' + directory, self.tex]
        proc = ProcessRunner(cmd)
        proc.connect('finished', self.on_compile_finished)

    # Callback for the compile async processrunner: 
    # gets called when the compilation is finished. 
    def on_compile_finished(self,sender):
        # load the log file.
        logname = os.path.splitext(self.tex)[0] + '.log'
        l = GtkSource.File.new()
        l.set_location(Gio.File.new_for_path(logname))
        log_loader = GtkSource.FileLoader.new(self.log_buffer,l)
        log_loader.load_async(GLib.PRIORITY_DEFAULT,None,None,None,self.on_log_load_finished,None)
        
        if sender.result == 0:
            # Compilation was successful
            self.pdf_reload()
            self.view_stack.set_visible_child_name("pdf")
            i = self.buffer.get_iter_at_offset(self.buffer.props.cursor_position)
            sl = EvinceDocument.SourceLink.new(self.tex,i.get_line(),i.get_line_offset())
            self.pdf_viewer.highlight_forward_search(sl)
            # I should undo the highlight... Goes away by click, I don't know how to get rid of it without click.
        else: 
            # Compilation failed
            print("Compile failed")
            print("output:\n ------------------------- \n"+sender.stdout+"\n-------------------------")
            #print("err\n-------------------\n"+sender.stderr)
            self.view_stack.set_visible_child_name("log")
            # regexp looking for errors in latexmk output
            r = re.compile("^! (.*)\nl\.([0-9]*)(.*?$)",re.MULTILINE|re.DOTALL)
            m = re.search(r,sender.stdout)
            if m:
                print(m.group(1))
                print(m.group(2))
                print(m.group(3))
                it = self.buffer.get_iter_at_line_offset(int(m.group(2))-1,0)
                self.buffer.place_cursor(it)
                self.sourceview.scroll_to_iter(it,0,False,0,0)
                self.sourceview.grab_focus()                
            else:
                print("did not find regexp")
            
    
    # Callback for the async log loader. For now, it does nothing.
    def on_log_load_finished(self, loader, result, data):
        loader.load_finish(result)
        print("Log loading finished")
        
            
    # callback for Evince doing Synctex from pdf to source.
    # Go to the corresponding line. This needs to be refined. 
    def on_sync_source(self,sender,sourcelink):
        # Fix the line numbering.
        line = sourcelink.line -1
        col = sourcelink.col
        if col <0:
            col=0
        it = self.buffer.get_iter_at_line_offset(line,col)
        self.buffer.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,False,0,0)
        self.sourceview.grab_focus()
        
    # Set up Actions, add shortcuts to it. 
    def makeactions(self):
        action = Gio.SimpleAction.new('compile', None)
        action.connect('activate', self.on_compile)
        self.add_action(action)
        self.get_application().set_accels_for_action('win.compile', ['F5'])
            
        action = Gio.SimpleAction.new('open', None)
        action.connect('activate', self.on_tex_open)
        self.add_action(action)
        self.get_application().set_accels_for_action('win.open', ['<ctrl>o'])

        action = Gio.SimpleAction.new('save', None)
        action.connect('activate', self.on_save)
        self.add_action(action)
        self.get_application().set_accels_for_action('win.save', ['<ctrl>s'])

