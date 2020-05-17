import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('Poppler', '0.18')
from gi.repository import Poppler	
import math
import os

class PdfViewer(Gtk.EventBox):
    __gtype_name__ = 'PdfViewer'
   
    def __init__(self):
        super().__init__()
        self.layout = Gtk.Layout()
        self.scroll = Gtk.ScrolledWindow()
        self.add(self.scroll)
        self.scroll.add(self.layout)
        self.pdf = None
        self.nPages = None
        self.page_height = None
        self.doc_height = None
        self.doc_width = None
        self.doc = None
        self.zoom = 1
        self.page_sep = 5

        self.scroll.connect("size-allocate", self.on_scroll_size_allocate)
        self.layout.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_click)

    def reload(self):
        doc = Poppler.Document.new_from_file("file://"+self.pdf)
        self.nPages = doc.get_n_pages()
        self.page_height = doc.get_page(0).get_size()[1]
        self.doc_height = self.nPages*(self.page_height + self.page_sep)
        self.doc_width = doc.get_page(0).get_size()[0]
        self.pages = [doc.get_page(i) for i in range(self.nPages)]
        self.doc = doc
        self.layout.set_size(self.doc_width*self.zoom,
                             self.doc_height*self.zoom)
        

    def open_file(self, pdf):
        if not os.path.exists(pdf):
            return
        self.pdf = pdf
        self.reload()

    def pages_to_render(self):
        y_min = self.layout.get_vadjustment().get_value()
        y_max = y_min + self.layout.get_allocated_height()
        return [i for i in range(self.nPages) if
                (i+1)*(self.page_height+self.page_sep)*self.zoom >= y_min
                and i*(self.page_height+self.page_sep)*self.zoom <= y_max]

    def pdf_coord_to_scroll(self, p, x, y):
        return [self.zoom*(self.doc_width-x),
                self.zoom*(p*self.page_height-y)]

    def show_coord(self, p, x, y):
        [x, y] = self.pdf_coord_to_scroll(p, x, y)
        vadj = self.layout.get_vadjustment()
        vadj.set_value(y)
        self.layout.set_vadjustment(vadj)
        self.layout.queue_draw()

    def on_draw(self, widget, ctx):
        if self.doc is not None:
            v = self.layout.get_vadjustment().get_value()
            ctx.translate(0, -v)
            ctx.scale(self.zoom, self.zoom)
            ctx.set_source_rgb(1, 1, 1);
            for p in range(self.nPages):
                if p in self.pages_to_render():
                    ctx.rectangle(0, 0, self.doc_width, self.page_height)
                    ctx.fill()
                    self.pages[p].render(ctx)
                ctx.translate(0, self.page_height+self.page_sep)

    def on_click(self, widget, event):
        print("Clicked")
        (x, y) = event.get_coords()
        y = y + self.layout.get_vadjustment().get_value()
        y = y/self.zoom
        x = x/self.zoom
        p = math.floor(y/(self.page_height+self.page_sep))
        y = y % (self.page_height+self.page_sep)
        for l in self.pages[p].get_link_mapping():
            if x > l.area.x1 and x < l.area.x2 and \
               self.page_height-y < l.area.y2 and self.page_height-y > l.area.y1:
                action = l.action   # Otherwise it does not work....
                dest = self.doc.find_dest(action.goto_dest.dest.named_dest)
                self.show_coord(dest.page_num, dest.left, dest.top)

    def on_scroll_size_allocate(self, widget, allocation):
        if self.doc_width:
            self.zoom = widget.get_allocated_width()/self.doc_width
            self.layout.set_size(self.doc_width*self.zoom,
                                 self.doc_height*self.zoom)

