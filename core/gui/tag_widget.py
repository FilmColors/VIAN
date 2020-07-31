
import numpy as np

from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QLineEdit, QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QSizePolicy

from core.gui.flow_layout import FlowLayout

class TagWidget(QWidget):
    def __init__(self, parent):
        super(TagWidget, self).__init__(parent)
        self.tags = dict()
        self.setLayout(FlowLayout())

    def add_tag(self, name):
        to_add = [name]
        for k, itm in self.tags.items():
            itm.deleteLater()
            to_add.append(k)

        if name in self.tags:
            w = self.tags[name]
            self.tags.pop(name)
            w.deleteLater()
        self.tags = dict()

        c = np.random.randint(0, 120, 3).tolist()
        last = None
        for name in sorted(to_add):
            cat = ":".join(name.split(":")[:2])
            if cat != last:
                c = np.random.randint(0, 120, 3).tolist()
                last = cat
            t  = Tag(self, name, c)
            self.layout().addWidget(t)
            self.tags[name] = t

    def remove_tag(self, name):
        if name in self.tags:
            w = self.tags[name]
            self.tags.pop(name)
            w.deleteLater()



class Tag(QFrame):
    def __init__(self,parent, lbl, c = None):
        super(Tag, self).__init__(parent)
        if c is None:
            c = np.random.randint(0,120,3).tolist()
        self.setStyleSheet("QFrame{background-color:rgb("+str(c[0])+","+str(c[1])+","+str(c[2])+"); "
                            "border:2px solid white;"
                            "border-radius: 5px; "
                            "margin: 1px; "
                            "padding: 1px;}")

        self.btn_remove = QPushButton("X")
        self.lbl = QLabel(lbl)

        self.lbl.setStyleSheet("QWidget{border:0px solid white; margin: 1px; ""padding: 1px;}")
        self.setLayout(QHBoxLayout())
        self.layout().setSpacing(1)
        self.layout().setContentsMargins(1,1,1,1)
        self.layout().addWidget(self.lbl)
        self.layout().addWidget(self.btn_remove)


