
import os

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QPoint

from core.gui.ewidgetbase import EDialogWidget


class ColorPicker(QFrame):
    colorChanged = pyqtSignal(tuple)
    def __init__(self, parent):
        super(ColorPicker, self).__init__(parent)
        path = os.path.abspath("qt_ui/ColorPicker.ui")
        uic.loadUi(path, self)

        self.chosen_color = (255,255,255)

        self.btn_Col1.clicked.connect(self.on_click1)
        self.btn_Col2.clicked.connect(self.on_click2)
        self.btn_Col3.clicked.connect(self.on_click3)
        self.btn_Col4.clicked.connect(self.on_click4)
        self.btn_Col5.clicked.connect(self.on_click5)
        self.btn_Col6.clicked.connect(self.on_click6)
        self.btn_Col7.clicked.connect(self.on_click7)
        self.btn_Col8.clicked.connect(self.on_click8)
        self.btn_Col9.clicked.connect(self.on_click9)

    def color(self):
        return self.chosen_color

    def on_click1(self):
        self.chosen_color = (255, 204, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click2(self):
        self.chosen_color = (255, 102, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click3(self):
        self.chosen_color = (255, 0, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click4(self):
        self.chosen_color = (0, 170, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click5(self):
        self.chosen_color = (6, 122, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click6(self):
        self.chosen_color = (0, 85, 0)
        self.colorChanged.emit(self.chosen_color)

    def on_click7(self):
        self.chosen_color = (85, 0, 255)
        self.colorChanged.emit(self.chosen_color)

    def on_click8(self):
        self.chosen_color = (85, 170, 255)
        self.colorChanged.emit(self.chosen_color)

    def on_click9(self):
        self.chosen_color = (255, 85, 255)
        self.colorChanged.emit(self.chosen_color)


class DialogPrompt(EDialogWidget):
    def __init__(self, parent, text):
        super(DialogPrompt, self).__init__(parent)
        path = os.path.abspath("qt_ui/DialogPrompt.ui")
        uic.loadUi(path, self)
        self.label.setText(text)
        self.show()


class StringList(QWidget):
    def __init__(self, parent):
        super(StringList, self).__init__(parent)
        path = os.path.abspath("qt_ui/SimpleStringList.ui")
        uic.loadUi(path, self)

        self.entries = []
        self.btn_Add.clicked.connect(self.on_add)
        self.btn_Remove.clicked.connect(self.on_remove)

        self.list = EListWidget(self)
        self.list.onNameChanged.connect(self.on_name_changed)
        self.widget.layout().addWidget(self.list)

        self.list.installEventFilter(self)

    def setTitle(self, title):
        self.lbl_Title.setText(title)

    def get_entries(self):
        return self.entries

    def on_add(self):
        self.entries.append("New Entry")
        self.update_widget()

    @pyqtSlot(str, str)
    def on_name_changed(self, a, b):
        if a in self.entries:
            idx = self.entries.index(a)
            self.entries.pop(idx)
            self.entries.insert(idx, b)
        self.update_widget()

    def update_widget(self):
        self.list.clear()
        for e in self.entries:
            self.list.addItem(StringListitem(self.list, e))

    def on_remove(self):
        if self.list.currentItem() is not None:
            if self.list.currentItem().text() in self.entries:
                self.entries.remove(self.list.currentItem().text())
            self.update_widget()


class StringListitem(QListWidgetItem):
    def __init__(self, parent, text):
        super(StringListitem, self).__init__(parent)
        self.setText(text)


class EListWidget(QListWidget):
    onNameChanged = pyqtSignal(str, str)
    def __init__(self, parent):
        super(EListWidget, self).__init__(parent)
        self.line_edit = None

    def mouseDoubleClickEvent(self, e):
        if self.currentItem() is not None:
            self.line_edit = PopupLineEdit(self)
            rect = self.visualItemRect(self.currentItem())
            pos = QPoint(rect.x(), rect.y())
            pos = self.mapToParent(pos)

            self.line_edit.move(self.mapToGlobal(pos))
            self.line_edit.resize(self.width(), self.line_edit.height())
            self.line_edit.show()
            self.line_edit.returnPressed.connect(self.on_lineedit_closed)
            self.line_edit.setFocus(Qt.OtherFocusReason)

        print("Hello")

    def on_lineedit_closed(self):
        self.line_edit.close()
        self.onNameChanged.emit(self.currentItem().text(), self.line_edit.text())
        self.line_edit = None



class PopupLineEdit(QLineEdit):
    def __init__(self, parent):
        super(PopupLineEdit, self).__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setWindowModality(Qt.NonModal)
        # self.setFocus(Qt.OtherFocusReason)

    def focusOutEvent(self, QFocusEvent):
        self.close()


