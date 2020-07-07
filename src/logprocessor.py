import gi, re, os

from gi.repository import Gtk, Gio

gi.require_version('GtkSource', '4')
from gi.repository import GtkSource
###########################################################################
# Processing the log file. TODO: change it to async. 

class ListBoxRowWithData(Gtk.ListBoxRow):
    def __init__(self, data):
        super(Gtk.ListBoxRow, self).__init__()
        self.data = data


class LogProcessor:
    def __init__(self,srcview,log_list):
        self.log_list   = log_list
        self.sourceview = srcview
        self.buffer     = self.sourceview.get_buffer()
        self.logname = None
        
        # The regexps to look for in the log file
        self.badbox = re.compile("^Overfull.* ([0-9]+)\-\-[0-9]+\n",re.MULTILINE)
        self.warn   = re.compile("^LaTeX Warning: (Reference|Citation) `(.*)'.* ([0-9]*)\.\n",re.MULTILINE)

        # Setting up the marks to use
        icon_theme = Gtk.IconTheme.get_default()
        # Error mark 
        pixbuf = icon_theme.load_icon("dialog-error",24,0)
        mark_attr = GtkSource.MarkAttributes.new()
        mark_attr.set_pixbuf(pixbuf)
        mark_attr.connect("query-tooltip-text", lambda obj,mark: "Error")
        self.sourceview.set_mark_attributes("Error",mark_attr,0)            
        # Warning mark
        pixbuf = icon_theme.load_icon("dialog-warning",24,0)
        mark_attr = GtkSource.MarkAttributes.new()
        mark_attr.set_pixbuf(pixbuf)
        mark_attr.connect("query-tooltip-text", lambda obj,mark: "Warning")
        self.sourceview.set_mark_attributes("Warning",mark_attr,0)  

        # tags to use
        self.buffer.create_tag("Error", background ="#ff6666")
        self.buffer.create_tag("Warning", background ="#fae0a0")

        self.log_list.connect("row-activated", self.on_row_activated)
        
    def update_name(self,filename):
        self.logname = os.path.splitext(filename)[0] + '.log'
        
    def run(self):
        # load the log file.
        l = Gio.File.new_for_path(self.logname)
        l.load_contents_async(None, self._log_load_cb, None)
    
    def _log_load_cb(self,src,res,data):
        success, contents, etag = src.load_contents_finish(res)
        try:
            decoded = contents.decode("UTF-8")
        except UnicodeDecodeError:
            print("Error: Unknown character encoding of the log file. Expecting UTF-8")
        self.process(decoded)

    def process(self,log):
        self.clearup()
        r = re.compile("^! (.*)\nl\.([0-9]*)(.*?$)",re.MULTILINE|re.DOTALL)
        it = re.finditer(r,log)
        place_cursor = True
        for m in it:
            msg    = m.group(1)
            line   = int(m.group(2))-1
            detail = m.group(3)[4:]
            self.process_line(msg,line,detail,"Error",place_cursor)
            place_cursor = False
        place_cursor = False
        
        r = re.compile("^LaTeX Warning: (Reference|Citation) `(.*)'.* ([0-9]*)\.\n",re.MULTILINE)
        it = re.finditer(r,log)
        for m in it:
            msg    = m.group(1)
            line   = int(m.group(3))-1
            detail = m.group(2)
            if msg == "Reference":
                detail = "\\ref{" + detail + "}"
            else:
                detail = "\\cite{" + detail + "}"
            msg    = "Undefined " + msg
            self.process_line(msg,line,detail,"Warning",place_cursor)

        r = re.compile("^Overfull.* ([0-9]+)\-\-[0-9]+\n",re.MULTILINE)
        it = re.finditer(r,log)
        for m in it:
            msg    = "Overful hbox"
            line   = int(m.group(1))-1
            detail = ""
            self.process_line(msg,line,detail,"Warning",place_cursor)

        self.log_list.show_all()
        
    def clearup(self):
        # remove the inserted error marks.
        s = self.buffer.get_start_iter()
        e = self.buffer.get_end_iter()
        self.buffer.remove_source_marks(s, e, "Error")
        self.buffer.remove_source_marks(s, e, "Warning")
        self.buffer.remove_tag_by_name("Error", s, e)
        self.buffer.remove_tag_by_name("Warning", s, e)
        # Delete the list
        self.log_list.foreach(self.log_list.remove)
    
        
    def process_line(self,msg,line,detail,typ,place_cursor):
        it = self.buffer.get_iter_at_line_offset(line,0)
        self.buffer.create_source_mark(None, typ, it) 
        limit = self.buffer.get_iter_at_line_offset(line+1,0)
        row = ListBoxRowWithData(line)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        row.add(hbox)
        hbox.pack_start(Gtk.Label(typ, xalign=0), True, True, 0)
        hbox.pack_start(Gtk.Label(msg, xalign=0), False, True, 0)
        hbox.pack_start(Gtk.Label(detail, xalign=0), False, True, 0)
        self.log_list.add(row)
        if place_cursor:
            self.buffer.place_cursor(it)
            self.sourceview.scroll_to_iter(it,0,True,0,0.5)
            self.sourceview.grab_focus()   
        # Add the marks
        if detail:
            limit = self.buffer.get_iter_at_line_offset(line+1,0)
            result = it.forward_search(detail,Gtk.TextSearchFlags.TEXT_ONLY,limit)
            print(detail)
            if result:
                [start_it,end_it] = result
                self.buffer.apply_tag_by_name(typ,start_it,end_it)
                
    def on_row_activated(self,listbox,row):
        it = self.buffer.get_iter_at_line_offset(row.data,0)
        self.buffer.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,True,0,0.5)
        self.sourceview.grab_focus()   
        
