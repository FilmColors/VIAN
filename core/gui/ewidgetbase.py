from PyQt5.Qt import QApplication
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import webbrowser

from core.data.log import log_error
from core.data.computation import pixmap_to_numpy, numpy_to_pixmap
from core.container.project import VIANProject
import cv2
from functools import partial
from PyQt5 import uic
import os
from core.gui.misc.utils import dialog_with_margin

import sys
# if sys.platform == "darwin":
#     from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
# else:
#     from PyQt5.QtWebKitWidgets import QWebView

# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure
import webbrowser

def line_separator(Orientation):
    frame = QFrame()
    frame.setStyleSheet("QFrame{border: 1px solid black;}")
    frame.setFrameStyle(QFrame.Box)
    if Orientation == Qt.Horizontal:
        frame.setFixedHeight(1)
    else:
        frame.setFixedWidth(1)

    return frame

import typing

class ExpandableWidget(QWidget):
    onClicked = pyqtSignal()
    def __init__(self, parent, expand_title = "Expand", inner = None, expanded = False, popup = False):
        super(ExpandableWidget, self).__init__(parent)
        self.popup = popup
        self.expand_title = expand_title
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.setLayout(QVBoxLayout())
        self.btn_expand = QPushButton(expand_title, self)
        self.layout().addWidget(self.btn_expand)
        if inner is not None:
            self.layout().addWidget(inner)
            self.inner = inner
            self.inner.hide()
        else:
            self.inner = None
        self.btn_expand.clicked.connect(self.toggle_expanded)
        if expanded:
            self.toggle_expanded()

    def set_inner(self, inner):
        if self.inner is not None:
            self.layout().removeWidget(self.inner)
        self.inner = inner

        self.layout().addWidget(inner)

    def toggle_expanded(self):
        state = None
        if self.inner is None:
            self.onClicked.emit()
            return
        if self.popup:
            pop = ExpandablePopup(self, self)
            pop.move(self.mapToGlobal(QPoint(10,10)))
        if state is None:
            self.inner.setVisible(not self.inner.isVisible())
        else:
            self.inner.setVisible(state)
        self.onClicked.emit()


class ExpandablePopup(QMainWindow):
    def __init__(self, parent, expandable):
        super(ExpandablePopup, self).__init__(parent)
        self.expandable = expandable
        self.setCentralWidget(expandable.inner)
        self.setWindowTitle(self.expandable.expand_title)
        self.resize(600,50)
        self.show()

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.expandable.layout().addWidget(self.expandable.inner)
        self.expandable.inner.setVisible(False)
        super(ExpandablePopup, self).closeEvent(a0)


class EProgressPopup(QDialog):
    def __init__(self, parent):
        super(EProgressPopup, self).__init__(parent)
        path = os.path.abspath("qt_ui/ProgressPopup.ui")
        uic.loadUi(path, self)
        self.setWindowModality(Qt.ApplicationModal)

    @pyqtSlot(float, str)
    def on_progress(self, value, info):
        self.labelInfo.setText(info)
        self.progressBar.setValue(value * 100)


class ESimpleDockWidget(QDockWidget):
    def __init__(self, parent, inner, name = ""):
        super(ESimpleDockWidget, self).__init__(parent)
        self.setWidget(inner)
        self.setWindowTitle(name)


class EDockWidget(QDockWidget):
    def __init__(self, main_window, limit_size = True, width = None, height = None):
        super(EDockWidget, self).__init__()
        self.main_window = main_window
        self.setAttribute(Qt.WA_MacOpaqueSizeGrip, True)
        # self.setAttribute(Qt.WA_AlwaysStackOnTop, False)
        self.limit_size = limit_size
        self.setLayout(QVBoxLayout(self))
        self.default_width = width
        self.default_height = height

        #NEWCODE
        self.inner = QMainWindow(None)

        if limit_size:
            # if width is None:
            #     width = 400
            # self.inner.setMaximumWidth(width)
            self.inner.size
            self.inner.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding)

        self.init = True
        self.setWidget(self.inner)

        if QScreen.physicalDotsPerInch(QApplication.screens()[0]) > 300:
            self.max_width = 800
        else:
            self.max_width = 400

        self.main_window.dock_widgets.append(self)
    
    def minimumSizeHint(self):
        if self.limit_size:
            return QSize(200,200)
        else:
            return super(EDockWidget, self).minimumSizeHint()
    
    def resize_dock(self, w=-1, h=-1):
        return

        if w == -1:
            w = self.widget().width()
        if h == -1:
            h = self.widget().height()

        self.widget().resize(w, h)
        self.main_window.resizeDocks([self], [w], Qt.Horizontal)
        self.main_window.resizeDocks([self], [h], Qt.Vertical)

    def setWidget(self, QWidget):
        if self.init:
            super(EDockWidget, self).setWidget(QWidget)
            self.init = False
        else:
            self.inner.setCentralWidget(QWidget)

    # def dockLocationChanged(self, Qt_DockWidgetArea):
    #     super(EDockWidget, self).dockLocationChanged(Qt_DockWidgetArea)
    #     self.areas = Qt_DockWidgetArea

    def close(self):
        self.hide()

    def show(self):
        super(EDockWidget, self).show()

    def project(self) -> VIANProject:
        try:
            return self.main_window.project
        except TypeError:
            log_error(self.__class__.__name__, ".main_window attributed of ", self, \
                " doesn't seem to be from derived from class MainWindow")

    def set_ui_enabled(self, state):
        self.setDisabled(not state)

    def get_settings(self):
        return dict()

    def apply_settings(self, settings):
        pass


class EDialogWidget(QDialog):
    def __init__(self,  parent = None,  main_window = None, help_path = None):
        super(EDialogWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_MacOpaqueSizeGrip, True)
        self.help_path = help_path

        # self.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.Dialog)
        self.setWindowFlags(Qt.Dialog)
        self.main_window = main_window

        if main_window is not None:
            if self not in self.main_window.open_dialogs:
                self.main_window.open_dialogs.append(self)
            self.main_window.check_overlay_visibility()

    def closeEvent(self, QCloseEvent):
        if self.main_window is not None:
            if self in self.main_window.open_dialogs:
                self.main_window.open_dialogs.remove(self)
            self.main_window.check_overlay_visibility()
        super(EDialogWidget, self).closeEvent(QCloseEvent)

    def on_help(self):
        if self.help_path is not None:
            webbrowser.open(self.help_path)


class EGraphicsView(QGraphicsView):
    onScaleEvent = pyqtSignal(float)

    def __init__(self, parent, auto_frame = True, main_window = None, has_context_menu=True):
        super(EGraphicsView, self).__init__(parent)
        self.gscene = QGraphicsScene()
        self.setScene(self.gscene)
        self.pixmap = None
        self.heads_up_widget = None

        self.auto_frame = auto_frame
        self.ctrl_is_pressed = False
        self.curr_scale = 1.0
        self.main_window = main_window
        self.has_context_menu = has_context_menu
        self.keep_aspect_ratio = True

    def set_image(self, pixmap, clear = True):
        if clear:
            self.gscene.clear()
        self.pixmap = self.gscene.addPixmap(pixmap)

    def resizeEvent(self, event: QResizeEvent):
        super(EGraphicsView, self).resizeEvent(event)
        if self.pixmap is not None and self.auto_frame:
            rect = self.pixmap.sceneBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            if self.has_context_menu:
                self.create_context_menu(event.pos())
        else:
            super(EGraphicsView, self).mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.viewport().setCursor(QCursor(Qt.UpArrowCursor))
            self.ctrl_is_pressed = True
            event.ignore()

        elif event.key() == Qt.Key_F:
            self.setSceneRect(QRectF())
            if self.keep_aspect_ratio:
                self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            else:
                self.fitInView(self.sceneRect())
            self.curr_scale = 1.0
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.pixmap is not None and self.auto_frame:
            rect = self.pixmap.sceneBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.viewport().setCursor(QCursor(Qt.ArrowCursor))
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            # viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            # self.curr_scale = round(self.pixmap.pixmap().width() / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100000:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.00001:
                self.scale(l_factor, l_factor)
                self.curr_scale *= l_factor

            cursor_pos = self.mapToScene(event.pos()) - old_pos
            self.onScaleEvent.emit(self.curr_scale)

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(EGraphicsView, self).wheelEvent(event)

    def create_context_menu(self, pos):
        menu = QMenu(self.main_window)
        a_export = menu.addAction("Export Image")
        a_export.triggered.connect(self.on_export_image)
        menu.popup(self.mapToGlobal(pos))

    def on_export_image(self):
        if self.pixmap is not None:
            img = pixmap_to_numpy(self.pixmap.pixmap())
            file_name = QFileDialog.getSaveFileName(self.main_window,
                                                    directory = self.main_window.project.export_dir,
                                                    filter ="*.png *.jpg")[0]
            cv2.imwrite(file_name, img)

    def set_heads_up_widget(self, widget:QWidget):
        self.heads_up_widget = widget
        widget.setParent(self)
        widget.move(5,5)
        widget.resize(150, 20)
        widget.show()


class EMultiGraphicsView(QGraphicsView):
    onScaleEvent = pyqtSignal(float)

    def __init__(self, parent, auto_frame = True, main_window = None, has_context_menu=True):
        super(EMultiGraphicsView, self).__init__(parent)
        self.gscene = QGraphicsScene()
        self.setScene(self.gscene)
        self.auto_frame = auto_frame
        self.ctrl_is_pressed = False
        self.curr_scale = 1.0
        self.main_window = main_window
        self.has_context_menu = has_context_menu
        self.pixmaps = []
        self.curr_x = 0
        self.margin = 50
        self.id_map = dict()

    def add_image(self, pixmap, clear = False, frame = True, item_id = None):
        if clear:
            self.gscene.clear()
        itm = self.gscene.addPixmap(pixmap)
        itm.setPos(self.curr_x, 0)
        self.curr_x += (pixmap.width() + self.margin)
        self.pixmaps.append(itm)

        if item_id is not None:
            self.id_map[item_id] = itm

        if frame:
            rect = self.scene().itemsBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def replace_image(self, item_id, pixmap):
        if item_id in self.id_map:
            self.id_map[item_id].setPixmap(pixmap)
            self.update_layout()

    def update_layout(self):
        self.curr_x = 0
        for idx, (k, itm) in enumerate(self.id_map.items()):
            itm.setPos(self.curr_x, 0)
            self.curr_x += (itm.pixmap().width() + self.margin)

    def resizeEvent(self, event: QResizeEvent):
        super(EMultiGraphicsView, self).resizeEvent(event)
        if len(self.pixmaps) > 0 and self.auto_frame:
            rect = self.scene().itemsBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            if self.has_context_menu:
                self.create_context_menu(event.pos())
        else:
            super(EMultiGraphicsView, self).mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.viewport().setCursor(QCursor(Qt.UpArrowCursor))
            self.ctrl_is_pressed = True
            event.ignore()

        elif event.key() == Qt.Key_F:
            self.setSceneRect(QRectF())
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            self.curr_scale = 1.0
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if len(self.pixmaps) > 0 and self.auto_frame:
            rect = self.scene().itemsBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.viewport().setCursor(QCursor(Qt.ArrowCursor))
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            # viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            # self.curr_scale = round(self.pixmap.pixmap().width() / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100000:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.00001:
                self.scale(l_factor, l_factor)
                self.curr_scale *= l_factor

            cursor_pos = self.mapToScene(event.pos()) - old_pos
            self.onScaleEvent.emit(self.curr_scale)

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(EMultiGraphicsView, self).wheelEvent(event)

    def create_context_menu(self, pos):
        menu = QMenu(self.main_window)
        a_export = menu.addAction("Export Image")
        a_export.triggered.connect(self.on_export_image)
        menu.popup(self.mapToGlobal(pos))

    def on_export_image(self):
        img = pixmap_to_numpy(self.pixmap.pixmap())
        file_name = QFileDialog.getSaveFileName(self.main_window,
                                                directory = self.main_window.project.export_dir,
                                                filter ="*.png *.jpg")[0]
        cv2.imwrite(file_name, img)


# class EHtmlDisplay(QWidget):
#     def __init__(self, parent, html, plot_width = 600):
#         super(EHtmlDisplay, self).__init__(parent)
#
#         self.view = QWebView(self)
#         self.plot_width = plot_width
#         self.view.setHtml(html)
#         self.setLayout(QHBoxLayout(self))
#         self.layout().addWidget(self.view)
#         self.view.setZoomFactor(1.0)
#
#     def resizeEvent(self, a0: QResizeEvent):
#         super(EHtmlDisplay, self).resizeEvent(a0)
#         self.view.setZoomFactor(self.width()/self.plot_width - 0.1)


class EToolBar(QToolBar):
    def __init__(self, main_window, title = "Toolbar Title"):
        super(EToolBar, self).__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle(title)

        self.show_indicator_frame = False
        self.indicator_color = QColor(255,160,47)

        self.setIconSize(QSize(40, 40))
        # if QScreen.physicalDotsPerInch(QApplication.screens()[0]) > 300:
        #     self.setIconSize(QSize(128,128))
        # else:
        #     self.setIconSize(QSize(64, 64))

    def paintEvent(self, QPaintEvent):
        super(EToolBar, self).paintEvent(QPaintEvent)
        qp = QPainter()
        pen = QPen()

        qp.begin(self)

        qp.setRenderHint(QPainter.Antialiasing)
        qp.setRenderHint(QPainter.TextAntialiasing)

        pen.setColor(self.indicator_color)
        pen.setWidth(5)

        qp.setPen(pen)

        # qp.fillRect(self.rect(), QColor(50, 50, 50))

        if self.show_indicator_frame:
            qp.drawRect(self.rect())

        qp.end()

    def show_indicator(self, visibility):
        self.show_indicator_frame = visibility
        self.update()


class ImagePreviewPopup(QMainWindow):
    def __init__(self, parent, pixmap):
        super(ImagePreviewPopup, self).__init__(parent)
        self.view = EGraphicsView(self)
        self.setCentralWidget(self.view)
        self.view.set_image(pixmap)
        self.setWindowFlags(Qt.Popup|Qt.FramelessWindowHint)
        self.show()
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())


class TextEditPopup(QMainWindow):
    onFinished = pyqtSignal(str)


    def __init__(self, parent, on_finished, pos = None, size = QSize(500,150), text = ""):
        super(TextEditPopup, self).__init__(parent)
        self.view = QPlainTextEdit(self)
        self.view.setPlainText(text)
        self.setCentralWidget(self.view)
        self.setWindowFlags(Qt.Popup|Qt.FramelessWindowHint)
        self.onFinished.connect(on_finished)

        self.show()

        if pos is None:
            self.move(QApplication.desktop().screen().rect().center() - self.rect().center())
        else:
            self.move(pos)


        self.resize(size)
        self.view.setFocus()

    def closeEvent(self, a0: QCloseEvent):
        self.onFinished.emit(self.view.toPlainText())
        super(TextEditPopup, self).closeEvent(a0)

    def keyPressEvent(self, a0: QKeyEvent):
        if a0.key() == Qt.Key_Enter:
            self.close()


class EditableListWidgetItem(QListWidgetItem):
    def __init__(self, parent, name, meta):
        super(EditableListWidgetItem, self).__init__(parent)
        self.setText(name)
        self.name = name
        self.meta = meta


class EditableListWidget(QWidget):
    onSelectionChanged = pyqtSignal(object)
    onItemAdded = pyqtSignal(str, object)
    onItemDeleted = pyqtSignal(str, object)

    def __init__(self, parent):
        super(EditableListWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.list = QListWidget(self)

        self.edit_layout = QHBoxLayout()
        self.btn_Add = QPushButton("+", self)
        self.btn_Remove = QPushButton("-", self)
        self.lineEdit_Name = QLineEdit(self)
        self.edit_layout.addWidget(self.btn_Remove)
        self.edit_layout.addWidget(self.lineEdit_Name)
        self.edit_layout.addWidget(self.btn_Add)
        self.layout().addWidget(self.list)
        self.layout().addItem(self.edit_layout)

        self.items = []
        self.item_index = dict()

        self.list.itemSelectionChanged.connect(self.on_selected)
        self.btn_Add.clicked.connect(self.on_add)
        self.btn_Remove.clicked.connect(self.on_remove)

    def mousePressEvent(self, a0: QMouseEvent) -> None:
        if a0.button() == Qt.RightButton:

            def remove_all(itms):
                for r in itms:
                    self.remove_item(r)

            menu = QMenu(self)
            a_export = menu.addAction("Remove")
            a_export.triggered.connect(partial(remove_all,  [s.name for s in self.list.selectedItems()]))
            menu.popup(self.mapToGlobal(a0.pos()))

    def add_item(self, name, meta) -> EditableListWidgetItem:
        n = name
        c = 0
        while n in self.item_index:
            n = name + "_" + str(c).zfill(2)
            c += 1
        name = n
        itm = EditableListWidgetItem(self.list, name, meta)
        self.list.addItem(itm)
        self.items.append(itm)
        self.item_index[name] = itm
        return itm

    def remove_item(self, name):
        if name in self.item_index:
            itm = self.item_index[name]
            if itm in self.items:
                self.items.remove(itm)
            self.list.takeItem(self.list.indexFromItem(itm).row())
            self.onItemDeleted.emit(itm.name, itm)

    def on_selected(self):
        selected = [s for s in self.list.selectedItems()]
        self.onSelectionChanged.emit(selected)

    def on_add(self):
        name = self.lineEdit_Name.text()
        if name != "":
            itm = self.add_item(name, None)
            self.onItemAdded.emit(name, itm)
        self.lineEdit_Name.setText("")

    def on_remove(self):
        for idx, itm in zip(self.list.selectedIndexes(), self.list.selectedItems()):
            self.list.takeItem(idx.row())
            self.items.remove(itm)
            self.onItemDeleted.emit(itm.name, itm)


class VIANMoveableGraphicsItemSignals(QObject):
    hasBeenMoved = pyqtSignal(object, object)


class VIANMovableGraphicsItem(QGraphicsPixmapItem):
    def __init__(self, pixmap: QPixmap, hover_text=None, mime_data=None):
        super(VIANMovableGraphicsItem, self).__init__(pixmap)
        if hover_text != None:
            self.setToolTip(hover_text)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.abs_pos = None
        self.signals = VIANMoveableGraphicsItemSignals()
        self.pos_scale = 1.0
        self.mime_data = mime_data
        self.pixmap = pixmap
        self.curr_alpha = 1.0
        self.curr_pos = self.pos()

    def mousePressEvent(self, event: 'QGraphicsSceneMouseEvent'):
        self.curr_pos = self.pos()

    def mouseReleaseEvent(self, event: 'QGraphicsSceneMouseEvent'):
        super(VIANMovableGraphicsItem, self).mouseReleaseEvent(event)
        self.signals.hasBeenMoved.emit(self, self.pos() - self.curr_pos)

    def paint(self, painter: QPainter, option: 'QStyleOptionGraphicsItem', widget: QWidget):
        super(VIANMovableGraphicsItem, self).paint(painter, option, widget)
        if self.isSelected():
            painter.setPen(QPen(QColor(255,0,0,200)))
            painter.drawRect(QRectF(0,0, self.sceneBoundingRect().width(), self.sceneBoundingRect().height()))


class FileBrowseBar(QWidget):
    def __init__(self, parent, mode = "file", default = "", filter = "", name = "file:"):
        super(FileBrowseBar, self).__init__(parent)
        self.mode = mode
        self.filter = filter
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(QLabel(name, self))
        self.line_edit = QLineEdit(self)
        self.line_edit.setText(default)
        self.btn_browse = QPushButton("Browse", self)
        self.layout().addWidget(self.line_edit)
        self.layout().addWidget(self.btn_browse)
        self.btn_browse.clicked.connect(self.on_browse)

    def on_browse(self):
        if self.mode == "file":
            file = QFileDialog.getSaveFileName(filter=self.filter)[0]
            if os.path.isfile(file):
                self.line_edit.setText(file)
        else:
            ddir = QFileDialog.getExistingDirectory()
            if os.path.isdir(ddir):
                self.line_edit.setText(ddir)

    def get_path(self):
        return self.line_edit.text()


class MultiItemTextInput(QWidget):
    onChanged = pyqtSignal()

    def __init__(self, parent, title, autocompleter = None):
        super(MultiItemTextInput, self).__init__(parent)
        self.setLayout(QHBoxLayout(self))
        lbl = QLabel(title, self)
        lbl.setFixedWidth(150)
        self.layout().addWidget(lbl)
        self.input = QLineEdit(self)
        self.added_list = QWidget(self)
        self.added_list.setLayout(QHBoxLayout(self.added_list))
        self.btn_add = QPushButton("+", self)
        self.btn_add.setMaximumWidth(20)

        self.layout().addWidget(self.input)
        self.layout().addWidget(self.btn_add)
        self.layout().addWidget(QLabel("Added:", self))

        self.layout().addWidget(self.added_list)
        self.added_list.setContentsMargins(0,0,0,0)
        self.added_list.layout().setContentsMargins(0,0,0,0)
        self.input.setFixedWidth(200)
        self.input.returnPressed.connect(self.on_add_item)
        self.btn_add.clicked.connect(self.on_add_item)

        self.items = []
        if autocompleter is not None:
            self.input.setCompleter(autocompleter)

    def setCompleter(self, completer):
        self.input.setCompleter(completer)

    def on_add_item(self):
        name = self.input.text()
        self.input.setText("")

        item = MultiItemTextInputItem(self, name)
        self.added_list.layout().addWidget(item)
        self.items.append(item)
        item.onRemove.connect(self.on_remove)
        self.onChanged.emit()

    def on_remove(self, item):
        if item in self.items:
            self.items.remove(item)
            item.deleteLater()
        self.onChanged.emit()

    def set_items(self, lst):
        for name in lst:
            item = MultiItemTextInputItem(self, name)
            self.added_list.layout().addWidget(item)
            self.items.append(item)
            item.onRemove.connect(self.on_remove)

    def get_items(self):
        return [n.name for n in self.items]

    def clear(self):
        self.input.setText("")
        for itm in self.items:
            itm.deleteLater()
        self.items = []


class MultiItemTextInputItem(QWidget):
    onRemove = pyqtSignal(object)

    def __init__(self, parent, name):
        super(MultiItemTextInputItem, self).__init__(parent)
        path = os.path.abspath("qt_ui/multiitemedititem.ui")
        uic.loadUi(path, self)
        self.lblName.setText(name)
        self.name = name
        self.btn_remove.clicked.connect(partial(self.onRemove.emit, self))



#region POPUPS
class CreateSegmentationPopup(QMainWindow):
    def __init__(self, parent, project, name = "New Segmentation", callback = None):
        super(CreateSegmentationPopup, self).__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.line_name = QLineEdit(self)
        self.line_name.setText(name)
        self.project = project
        self.callback = callback

        self.btn_ok = QPushButton("Create Segmentation", self)
        self.btn_ok.clicked.connect(self.on_ok)
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(QHBoxLayout(self))
        self.centralWidget().layout().addWidget(self.line_name)
        self.centralWidget().layout().addWidget(self.btn_ok)
        self.setMinimumWidth(300)
        self.show()
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())

    def on_ok(self):
        segm = self.project.create_segmentation(self.line_name.text())
        if self.callback is not None:
            self.callback(segm)
        self.close()


class CreateAnnotationLayerPopup(QMainWindow):
    def __init__(self, parent, project, name="New AnnotationLayer", callback = None):
        super(CreateAnnotationLayerPopup, self).__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.line_name = QLineEdit(self)
        self.line_name.setText(name)
        self.project = project
        self.callback = callback

        self.btn_ok = QPushButton("Create Annotation Layer", self)
        self.btn_ok.clicked.connect(self.on_ok)
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(QHBoxLayout(self))
        self.centralWidget().layout().addWidget(self.line_name)
        self.centralWidget().layout().addWidget(self.btn_ok)
        self.setMinimumWidth(300)
        self.show()
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())

    def on_ok(self):
        layer = self.project.create_annotation_layer(self.line_name.text(), 0, 1000)
        if self.callback is not None:
            self.callback(layer)
        self.close()


class CreateScreenshotGroupPopup(QMainWindow):
    def __init__(self, parent, project, name="New ScreenshotGroup", callback=None):
        super(CreateScreenshotGroupPopup, self).__init__(parent)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.line_name = QLineEdit(self)
        self.line_name.setText(name)
        self.project = project
        self.callback = callback

        self.btn_ok = QPushButton("Create Screenshot Group", self)
        self.btn_ok.clicked.connect(self.on_ok)
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(QHBoxLayout(self))
        self.centralWidget().layout().addWidget(self.line_name)
        self.centralWidget().layout().addWidget(self.btn_ok)
        self.setMinimumWidth(300)
        self.show()
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())

    def on_ok(self):
        grp = self.project.add_screenshot_group(self.line_name.text())
        if self.callback is not None:
            self.callback(grp)
        self.close()

#endregion

#region -- OLD CODE --
# class EVisualizationDialog(EDialogWidget):
#     def __init__(self, parent, visualization_widget):
#         super(EVisualizationDialog, self).__init__(parent)
#         self.vis_widget = visualization_widget
#         self.setLayout(QVBoxLayout(self))
#         self.layout().addWidget(self.vis_widget)
#         self.show()
#
#     def closeEvent(self, QCloseEvent):
#         self.parent().layout().addWidget(self.vis_widget)
#         super(EVisualizationDialog, self).closeEvent(QCloseEvent)


# class EAnalyseVisualization(QWidget):
#     def __init__(self, parent, analyze):
#         super(EAnalyseVisualization, self).__init__(parent)
#         self.setLayout(QVBoxLayout(self))
#         self.lbl = QLabel("<b>Visualization:", self)
#         self.btn_expand = QPushButton("Expand", self)
#         self.layout().addWidget(self.lbl)
#         self.layout().addWidget(self.btn_expand)
#         self.btn_expand.clicked.connect(self.on_expand)
#         self.analyze = analyze
#         self.figure = None
#
#         self.show()
#
#     def plot(self):
#         print("plot() not implemented in:", self)
#
#     def on_expand(self):
#         if self.figure is not None:
#             dialog = EVisualizationDialog(self, self.figure)

#
class EMatplotLibVis(QWidget):
    def __init__(self, parent, analyze):
        super(EMatplotLibVis, self).__init__(parent, analyze)

        # a figure instance to plot on
        # self.figure = MatplotlibFigure(self, self.analyze)

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__

        # this is the Navigation widget
        # it takes the Canvas widget and a parent

        self.layout().addWidget(self.figure)

    def plot(self):
        self.figure.plot()
#
# class GraphicsViewDockWidget(EDockWidget):
#     def __init__(self, main_window, pixmap = None):
#         super(GraphicsViewDockWidget, self).__init__(main_window, False)
#         self.view = EGraphicsView(self, auto_frame=False)
#
#         self.setWidget(self.view)
#         if pixmap is not None:
#             self.set_pixmap(pixmap)
#
#     def set_pixmap(self, pixmap):
#         self.view.set_image(pixmap)

#endregion

