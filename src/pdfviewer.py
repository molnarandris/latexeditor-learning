import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('EvinceView', '3.0')
from gi.repository import EvinceView, EvinceDocument
import os
import math


class PdfViewer(EvinceView.View):
    __gtype_name__ = 'PdfViewer'
   
    def __init__(self,win):
        super().__init__()
        EvinceDocument.init()

        self.model = EvinceView.DocumentModel()
        self.set_model(self.model)
        self.pdf = None
        self.doc = None
        self.zoom = 1
        self.win = win

        self.cmenu = Gtk.Menu()
        self.cm_fit_width = Gtk.MenuItem.new_with_label('Fit width')
        self.cmenu.append(self.cm_fit_width)
        self.cm_fit_text = Gtk.MenuItem.new_with_label('Fit text width')
        self.cmenu.append(self.cm_fit_text)
        self.cmenu.show_all()
        
        self.cm_fit_width.connect("activate", self.fit_width)
        self.cm_fit_text.connect("activate", self.fit_text)
        #self.cm_sync.connect("activate", self.sync_edit)
        
        self.connect("button-press-event",self.on_click)

    # I think this is essentially OK. Still might be a bit off.
    # I don't really understand though.
    # Is there no built-in function for this?
    """
    def screen_coord_to_pdf(self,x,y):
        # something random to not get an error
        # I can get the real y coordinate:
        scroll = self.get_parent()
        y = y + scroll.get_vadjustment().get_value()
        # I guess I have to rescale:
        x = x/self.model.get_scale()
        y = y/self.model.get_scale()
        # Get the page size. Just suppose for now that the page size is uniform.
        px,py = self.doc.get_page_size(1)
        print(py)
        w = 0.0
        h = 0.0
        b = Gtk.Border()
        EvinceDocument.Document.misc_get_page_border_size(w,h,b)
        py = py+(b.top+b.bottom)
        print(b.top+b.bottom)
        # Here I am definitely missing the space between the pages
        page = math.floor(y/py)
        y = y - page*py
        return page,x,y        
    """
        
    def reload(self):
        doc = EvinceDocument.Document.factory_get_document("file://"+self.pdf)
        self.model.set_document(doc)
        self.doc = doc

    def open_file(self, pdf):
        if not os.path.exists(pdf):
            return
        self.pdf = pdf
        self.reload()

    def on_click(self,widget,event):
        if event.button ==3:
            self.cmenu.popup_at_pointer()
            x,y = event.get_coords()
            self.cmenu.x = x
            self.cmenu.y = y
            
    def fit_width(self,widget):
        self.model.set_sizing_mode(EvinceView.SizingMode.FIT_WIDTH)

    def fit_text(self,widget):
        self.model.set_sizing_mode(EvinceView.SizingMode.BEST_FIT)        

    """    
    def sync_edit(self,widget):
        page = 3
        x = self.cmenu.x
        y = self.cmenu.y
        #page,x,y = self.screen_coord_to_pdf(x,y)
        #print("Page: " + str(page)+ " x: " + str(x) + " y: " + str(y))
        #print(self.model.get_page())
        #p = self.model.get_page()
        sourcelink = self.doc.synctex_backward_search(self.model.get_page(),x,y)
        self.emit("sync-source",sourcelink)
   """
