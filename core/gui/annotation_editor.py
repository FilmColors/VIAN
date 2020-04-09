import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic

from core.container.annotation_body import AnnotationBody, Annotatable

MIME_TYPES = dict(
    Text = AnnotationBody.MIMETYPE_TEXT_PLAIN,
    Citation = AnnotationBody.MIMETYPE_BIBTEX,
    URL = AnnotationBody.MIMETYPE_URL,
)

class AnnotationEditorPopup(QMainWindow):
    def __init__(self, parent, annotation, pos, size = None):
        super(AnnotationEditorPopup, self).__init__(parent)
        self.inner = AnnotationEditor(self, annotation)
        self.setCentralWidget(self.inner)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        if pos is not None:
            self.move(pos)
        if size is not None:
            self.resize(size)
        self.show()


class AnnotationEditor(QWidget):
    EDIT_TEXT_PLAIN = 0
    EDIT_URL = 1

    def __init__(self, parent, annotation:Annotatable):
        super(AnnotationEditor, self).__init__(parent)
        path = os.path.abspath("qt_ui/AnnotationEditor.ui")
        uic.loadUi(path, self)
        self.annotatable = annotation

        self.mime_types = dict()
        for k, v in MIME_TYPES.items():
            self.mime_types[v] = k
            self.comboBox_Type.addItem(k)

        self.comboBox_Type.currentTextChanged.connect(self.on_mimetype_changed)

        # self.annotationList = QListWidget()
        self.annotationList.setSelectionMode(QListWidget.SingleSelection)

        self.entries = dict()
        self.entries_lst = []
        self.update_entries()

        self.annotationList.itemSelectionChanged.connect(self.item_selected)
        self.plainTextEdit.textChanged.connect(self.on_content_changed)
        self.lineEdit_URL.textChanged.connect(self.on_content_changed)
        self.btnAdd.clicked.connect(self.on_add)
        self.btnRemove.clicked.connect(self.on_remove)

        if len(self.entries_lst) == 0:
            self.on_add()

        self.annotationList.setCurrentItem(self.entries_lst[0])
        self.plainTextEdit.setFocus()

    def on_content_changed(self):
        sel = self.annotationList.selectedItems()
        if len(sel) > 0:
            an = self.entries[sel[0].text()]
            if an.mime_type in [AnnotationBody.MIMETYPE_TEXT_PLAIN, AnnotationBody.MIMETYPE_BIBTEX]:
                an.set_content(self.plainTextEdit.toPlainText())
            else:
                an.set_content(self.lineEdit_URL.text())

    def on_mimetype_changed(self):
        sel = self.annotationList.selectedItems()
        if len(sel) > 0:
            an = self.entries[sel[0].text()]
            an.set_mime_type(MIME_TYPES[self.comboBox_Type.currentText()])
            an.set_name(MIME_TYPES[self.comboBox_Type.currentText()])


    def update_entries(self):
        self.entries = dict()
        self.annotationList.clear()
        self.entries_lst = []

        for i, a in enumerate(self.annotatable.get_annotations()):
            t = str(i) + " " + a.name

            itm = QListWidgetItem(t)
            self.entries_lst.append(itm)
            self.entries[t] = a
            self.annotationList.addItem(itm)
        if len(self.entries.keys()) == 0:
            self.widgetEdit.setEnabled(False)
        else:
            self.widgetEdit.setEnabled(False)


    def item_selected(self):
        sel = self.annotationList.selectedItems()
        if len(sel) > 0:
            self.widgetEdit.setEnabled(True)
            an = self.entries[sel[0].text()]
            self.comboBox_Type.setCurrentText(self.mime_types[an.mime_type])
            self.lineEdit_Title.setText(an.name)

            if an.mime_type in [AnnotationBody.MIMETYPE_TEXT_PLAIN, AnnotationBody.MIMETYPE_BIBTEX]:
                self.stackedWidget.setCurrentIndex(self.EDIT_TEXT_PLAIN)
                self.plainTextEdit.setPlainText(an.content)

            else:
                self.stackedWidget.setCurrentIndex(self.EDIT_URL)
                self.lineEdit_URL.setText(an.content)
        else:
            self.widgetEdit.setEnabled(False)

    def on_add(self):
        self.annotatable.add_annotation(AnnotationBody())
        self.update_entries()
        self.annotationList.setCurrentItem((self.entries_lst[len(self.entries_lst) - 1]))

    def on_remove(self):
        sel = self.annotationList.selectedItems()
        if len(sel) > 0:
            an = self.entries[sel[0].text()]
            self.annotatable.remove_annotation(an)
            self.update_entries()

            if len(self.entries_lst) > 0:
                self.annotationList.setCurrentItem((self.entries_lst[len(self.entries_lst) - 1]))


    def showEvent(self, a0: QShowEvent) -> None:
        super(AnnotationEditor, self).showEvent(a0)
        self.plainTextEdit.setFocus()




