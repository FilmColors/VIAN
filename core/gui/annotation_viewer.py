import os

from PyQt5 import QtCore, uic
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QTreeWidgetItem, QDialog

from core.data.computation import ms_to_string
from core.data.containers import Annotation
from core.data.interfaces import IProjectChangeNotify
from core.gui.ewidgetbase import EDialogWidget
from core.gui.ewidgetbase import EDockWidget


class NewLayerDialog(EDialogWidget):
    def __init__(self, parent, t_start, t_end):
        super(NewLayerDialog, self).__init__(parent)
        path = os.path.abspath("qt_ui/Dialog_CreateLayer.ui")
        uic.loadUi(path, self)

        self.annotation_viewer = parent
        self.t_start = t_start
        self.t_end = t_end

        self.text_Start.setText(str(t_start))
        self.text_End.setText(str(t_end))

        self.validator = QIntValidator(self)
        self.text_Start.setValidator(self.validator)
        self.text_End.setValidator(self.validator)

        self.text_Start.editingFinished.connect(self.validate_movie_time)
        self.text_End.editingFinished.connect(self.validate_movie_time)
        self.btn_OK.clicked.connect(self.on_ok)
        self.btn_Cancel.clicked.connect(self.on_cancel)


    def on_ok(self):
        self.annotation_viewer.add_layer(self.text_Name.text(),
                                         int(self.text_Start.text()),
                                         int(self.text_End.text()))
        self.close()

    def on_cancel(self):
        self.close()

    def validate_movie_time(self):
        if int(self.text_Start.text()) > int(self.text_End.text()):
            self.text_End.setText(self.text_Start.text())


class EditLayerDialog(QDialog):
    def __init__(self, parent, annotation):
        super(EditLayerDialog, self).__init__(parent)
        path = os.path.abspath("qt_ui/Dialog_CreateLayer.ui")
        uic.loadUi(path, self)

        self.annotation_viewer = parent
        self.annotation = annotation


        self.text_Start.setText(str(self.annotation.t_start))
        self.text_End.setText(str(self.annotation.t_end))

        self.validator = QIntValidator(self)
        self.text_Start.setValidator(self.validator)
        self.text_End.setValidator(self.validator)

        self.connect(self.text_Start, QtCore.SIGNAL("editingFinished()"), self.validate_movie_time)
        self.connect(self.text_End, QtCore.SIGNAL("editingFinished()"), self.validate_movie_time)
        self.connect(self.btn_OK, QtCore.SIGNAL("clicked()"), self.on_ok)
        self.connect(self.btn_Cancel, QtCore.SIGNAL("clicked()"), self.on_cancel)


    def on_ok(self):
        self.annotation.name = self.text_Name.text()
        self.annotation.t_start = int(self.text_Start.text())
        self.annotation.t_end = int(self.text_End.text())
        self.annotation_viewer.update_list()
        self.close()

    def on_cancel(self):
        self.close()

    def validate_movie_time(self):
        if int(self.text_Start.text()) > int(self.text_End.text()):
            self.text_End.setText(self.text_Start.text())