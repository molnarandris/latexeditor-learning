import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
gi.require_version('EvinceView', '3.0')
from gi.repository import EvinceView, EvinceDocument
import os


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

    def reload(self):
        doc = EvinceDocument.Document.factory_get_document("file://"+self.pdf)
        self.model.set_document(doc)
        self.doc = doc

    def open_file(self, pdf):
        if not os.path.exists(pdf):
            return
        self.pdf = pdf
        self.reload()

