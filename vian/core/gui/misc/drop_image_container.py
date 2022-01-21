from functools import partial

from PyQt6.QtGui import QPixmap, QDropEvent, QDragEnterEvent
from PyQt6.QtWidgets import QWidget, QSizePolicy, QGridLayout, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal

class DropImageContainer(QWidget):
    onChanged = pyqtSignal(object)

    def __init__(self, parent, x_max=5):
        super(DropImageContainer, self).__init__(parent)
        self.x_max = x_max

        self.setAcceptDrops(True)
        self.images = []

        self.lt = QGridLayout(self)
        self.setLayout(self.lt)
        self.pos_x = 0
        self.pos_y = 0
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        self.placeholder = DropImagePlaceholder(self)
        self.lt.addWidget(self.placeholder, 0, 0)

    def dragEnterEvent(self, a0: QDragEnterEvent) -> None:
        if ".jpg" in a0.mimeData().text() or ".png" in a0.mimeData().text():
            a0.acceptProposedAction()

    def dropEvent(self, a0: QDropEvent) -> None:
        for p in a0.mimeData().text().split("\n"):
            if ".jpg" in p or ".png" in p:
                img = DropImage(self, p)
                self._drop_image(img)
                img.btn_delete.clicked.connect(partial(self._on_delete, img))
        self.onChanged.emit(self.get_images())

    def get_images(self):
        return [img.path for img in self.images]

    def _drop_image(self, img):
        self.lt.addWidget(img, self.pos_y, self.pos_x)
        if self.pos_x ==  self.x_max - 1:
            self.pos_x = 0
            self.pos_y += 1
        else:
            self.pos_x += 1

        if img not in self.images:
            self.images.append(img)
        self.lt.addWidget(self.placeholder, self.pos_y, self.pos_x)

    def _on_delete(self, img):
        self.images.remove(img)
        self.layout().removeWidget(img)
        img.deleteLater()
        self.pos_x = 0
        self.pos_y = 0
        for img in self.images:
            self._drop_image(img)
        self.onChanged.emit(self.get_images())

import os
class DropImage(QWidget):
    def __init__(self, parent, path, w = 50):
        super(DropImage, self).__init__(parent)
        path = path.replace("file:///", "/")
        self.pixmap = QPixmap(path)
        self.pixmap.scaledToWidth(w)
        self.path = path
        self.btn_delete = QPushButton("Remove", self)
        self.setLayout(QVBoxLayout())
        lbl = QLabel(self)
        lbl.setPixmap(self.pixmap)
        self.layout().addWidget(lbl)
        self.layout().addWidget(self.btn_delete)
        self.setMaximumWidth(self.pixmap.width())
        self.setMaximumHeight(self.pixmap.height())


class DropImagePlaceholder(QWidget):
    def __init__(self, parent):
        super(DropImagePlaceholder, self).__init__(parent)
        self.pixmap = QPixmap("qt_ui/icons/icon_drop_image.png")
        self.setLayout(QVBoxLayout())
        lbl = QLabel(self)
        lbl.setPixmap(self.pixmap)
        self.layout().addWidget(lbl)





