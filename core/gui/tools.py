
import os

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QPoint
from core.data.computation import pixmap_to_numpy
from core.gui.ewidgetbase import EDialogWidget, EGraphicsView
import cv2

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


class ExportImageDialog(EDialogWidget):
    def __init__(self, main_window, visualization):
        super(ExportImageDialog, self).__init__(visualization, main_window)
        path = os.path.abspath("qt_ui/DialogExportImage.ui")
        uic.loadUi(path, self)
        self.visualization = visualization
        self.preview = ExportPreviewWidget(self, self.visualization)
        self.widget_Preview.setLayout(QVBoxLayout(self))
        self.widget_Preview.layout().addWidget(self.preview)

        self.spinBox_BG_R.valueChanged.connect(self.on_update)
        self.spinBox_BG_G.valueChanged.connect(self.on_update)
        self.spinBox_BG_B.valueChanged.connect(self.on_update)
        self.spinBox_BG_A.valueChanged.connect(self.on_update)
        self.spinBox_Width.valueChanged.connect(self.on_update)
        self.spinBox_Height.valueChanged.connect(self.on_update)

        self.btn_Export.clicked.connect(self.on_export)
        self.btn_Cancel.clicked.connect(self.close)
        self.btn_ResetRegion.clicked.connect(self.preview.reset_region)
        self.on_update()

    def on_update(self):
        background = QColor(self.spinBox_BG_R.value(), self.spinBox_BG_G.value(), self.spinBox_BG_B.value(), self.spinBox_BG_A.value())
        size = QSize(self.spinBox_Width.value(), self.spinBox_Height.value())
        image = self.visualization.render_to_image(background, size)
        self.preview.set_image(image)
        return image

    def on_export(self):
        img = self.on_update()
        if self.main_window is not None:
            file_name = QFileDialog.getSaveFileName(self,
                                                    directory=self.main_window.project.export_dir,
                                                    filter="*.png *.jpg")[0]
        else:
            file_name = QFileDialog.getSaveFileName(self,
                                                    filter="*.png *.jpg")[0]

        try:
            region = self.preview.region
            size = QSize(self.spinBox_Width.value(), self.spinBox_Height.value())

            img = pixmap_to_numpy(QPixmap(img))

            if region is not None:
                img = img[
                      int(region.y()):int(region.y() + region.height()),
                      int(region.x()):int(region.x() + region.width())
                      ]

                img = cv2.resize(img, (size.width(), size.height()), interpolation=cv2.INTER_CUBIC)

            cv2.imwrite(file_name, img)
        except Exception as e:
            raise e
            pass


class ExportPreviewWidget(QGraphicsView):
    def __init__(self, parent, visualization):
        super(ExportPreviewWidget, self).__init__(parent)
        self.visualization = visualization
        self.gscene = QGraphicsScene()
        self.setScene(self.gscene)

        self.image = None
        self.image_item = None

        self.is_selecting = False
        self.p_start = QPoint()
        self.p_end = QPoint()
        self.region = None
        self.selector_frame = self.gscene.addRect(self.sceneRect(), QColor(255, 255, 255))

    def reset_region(self):
        self.region = None
        self.selector_frame.setRect(self.sceneRect())

    def set_image(self, image:QImage):
        self.image = image
        self.gscene.clear()
        pen = QPen()
        pen.setWidthF(10)
        pen.setColor(QColor(255,255,255))
        self.image_item = self.gscene.addPixmap(QPixmap(image))
        self.selector_frame = self.gscene.addRect(self.sceneRect(), pen)

    def frame_image(self):
        if self.image_item is not None:
            rect = self.image_item.sceneBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def resizeEvent(self, event: QResizeEvent):
        super(ExportPreviewWidget, self).resizeEvent(event)
        self.frame_image()

    def start_selection(self, pos):
        self.is_selecting = True
        self.p_start = pos

    def update_selection(self, pos):
        new_s = QPoint()
        new_e = QPoint()
        if pos.x() > self.p_start.x():
            new_s.setX(self.p_start.x())
            new_e.setX(pos.x())
        else:
            new_s.setX(pos.x())
            new_e.setX(self.p_start.x())

        if pos.y() > self.p_end.y():
            new_s.setY(self.p_start.y())
            new_e.setY(pos.y())
        else:
            new_s.setY(pos.y())
            new_e.setY(self.p_start.y())

        self.selector_frame.setRect(new_s.x(), new_s.y(), new_e.x() - new_s.x(), new_e.y() - new_s.y())


    def end_selection(self):
        self.is_selecting = False
        self.region = self.selector_frame.sceneBoundingRect()

    def mousePressEvent(self, event: QMouseEvent):
        self.start_selection(self.mapToScene(event.pos()))

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.is_selecting:
            self.update_selection(self.mapToScene(event.pos()))

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.end_selection()


    def update(self):
        super(ExportPreviewWidget, self).update()
        self.frame_image()




