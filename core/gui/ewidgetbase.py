from PyQt5.Qt import QApplication
from PyQt5.QtCore import *
from PyQt5.QtGui import QScreen, QColor, QPainter, QPen, QResizeEvent, QWheelEvent, QKeyEvent, QCursor, QMouseEvent, QPixmap
from PyQt5.QtWidgets import *

from core.data.computation import pixmap_to_numpy, numpy_to_pixmap
import cv2
from PyQt5 import uic
import os
import sys
if sys.platform == "darwin":
    from PyQt5.QtWebEngineWidgets import QWebEngineView as QWebView
else:
    from PyQt5.QtWebKitWidgets import QWebView

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

class EDockWidget(QDockWidget):
    def __init__(self, main_window, limit_size = True, width = None, height = None):
        super(EDockWidget, self).__init__()
        self.main_window = main_window
        self.setAttribute(Qt.WA_MacOpaqueSizeGrip, True)
        self.limit_size = limit_size
        self.setLayout(QVBoxLayout(self))
        self.default_width = width
        self.default_height = height

        #NEWCODE
        self.inner = QMainWindow(None)
        self.init = True
        self.setWidget(self.inner)

        if QScreen.physicalDotsPerInch(QApplication.screens()[0]) > 300:
            self.max_width = 800
        else:
            self.max_width = 400

        # Currently VLC breaks the DockWidgets under OSX, we disable it therefore
        if self.main_window.is_darwin:
            self.setFeatures(QDockWidget.NoDockWidgetFeatures|QDockWidget.DockWidgetClosable)

    def resizeEvent(self, *args, **kwargs):
        # Keeping the size of the Dockwidgets

        if self.limit_size:
            if self.maximumWidth() != self.max_width:
                self.areas = self.main_window.dockWidgetArea(self)
                if self.areas == Qt.LeftDockWidgetArea or self.areas == Qt.RightDockWidgetArea:
                    self.setMaximumWidth(self.max_width)

        super(EDockWidget, self).resizeEvent( *args, **kwargs)

            # if self.project():
            #     self.main_window.update_player_size()
            #     self.main_window.update_overlay()

    def resize_dock(self, w=-1, h=-1):
        if w == -1:
            w = self.widget().width()
        if h == -1:
            h = self.widget().height()

        self.widget().resize(w, h)
        self.main_window.resizeDocks([self], [w], Qt.Horizontal)
        self.main_window.resizeDocks([self], [h], Qt.Vertical)

    def setWidget(self, QWidget):
        # NEWCODE
        if self.init:
            super(EDockWidget, self).setWidget(QWidget)
            self.init = False
        else:
            self.inner.setCentralWidget(QWidget)

    def dockLocationChanged(self, Qt_DockWidgetArea):
        super(EDockWidget, self).dockLocationChanged(Qt_DockWidgetArea)
        self.areas = Qt_DockWidgetArea

    def close(self):
        self.hide()

    def show(self):
        super(EDockWidget, self).show()

    def project(self):
        try:
            return self.main_window.project
        except TypeError:
            print(self.__class__.__name__, ".main_window attributed of ", self, \
                " doesn't seem to be from derived from class MainWindow")

    def set_ui_enabled(self, state):
        self.setDisabled(not state)


class EDialogWidget(QDialog):
    def __init__(self,  parent = None,  main_window = None, help_path = None):
        super(EDialogWidget, self).__init__(parent)
        self.setAttribute(Qt.WA_MacOpaqueSizeGrip, True)
        self.help_path = help_path

        # self.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.Dialog)
        self.setWindowFlags(Qt.Dialog)
        self.main_window = main_window

        if main_window is not None:
            self.overlay_was_visible = main_window.drawing_overlay.isVisible()
            self.main_window.set_overlay_visibility(False)

    def closeEvent(self, QCloseEvent):
        if self.main_window is not None:
            # self.main_window.set_darwin_player_visibility(True)
            if self.overlay_was_visible:
                self.main_window.set_overlay_visibility(True)
        super(EDialogWidget, self).closeEvent(QCloseEvent)

    def on_help(self):
        if self.help_path is not None:
            webbrowser.open("file://" + os.path.abspath(self.help_path))


class EGraphicsView(QGraphicsView):
    def __init__(self, parent, auto_frame = True, main_window = None, has_context_menu=True):
        super(EGraphicsView, self).__init__(parent)
        self.gscene = QGraphicsScene()
        self.setScene(self.gscene)
        self.pixmap = None
        self.auto_frame = auto_frame
        self.ctrl_is_pressed = False
        self.curr_scale = 1.0
        self.main_window = main_window
        self.has_context_menu = has_context_menu

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
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
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

            if event.angleDelta().y() > 0.0 and self.curr_scale < 10:
                self.scale(h_factor, h_factor)
                # self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.01:
                # self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(EGraphicsView, self).wheelEvent(event)


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


class EHtmlDisplay(QWidget):
    def __init__(self, parent, html, plot_width = 600):
        super(EHtmlDisplay, self).__init__(parent)

        self.view = QWebView(self)
        self.plot_width = plot_width
        self.view.setHtml(html)
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(self.view)
        self.view.setZoomFactor(1.0)

    def resizeEvent(self, a0: QResizeEvent):
        super(EHtmlDisplay, self).resizeEvent(a0)
        self.view.setZoomFactor(self.width()/self.plot_width - 0.1)


class EToolBar(QToolBar):
    def __init__(self, main_window, title = "Toolbar Title"):
        super(EToolBar, self).__init__(main_window)
        self.main_window = main_window
        self.setWindowTitle(title)

        self.show_indicator_frame = False
        self.indicator_color = QColor(255,160,47)

        if QScreen.physicalDotsPerInch(QApplication.screens()[0]) > 300:
            self.setIconSize(QSize(128,128))
        else:
            self.setIconSize(QSize(64, 64))

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
# class EMatplotLibVis(EAnalyseVisualization):
#     def __init__(self, parent, analyze):
#         super(EMatplotLibVis, self).__init__(parent, analyze)
#
#         # a figure instance to plot on
#         # self.figure = MatplotlibFigure(self, self.analyze)
#
#         # this is the Canvas Widget that displays the `figure`
#         # it takes the `figure` instance as a parameter to __init__
#
#         # this is the Navigation widget
#         # it takes the Canvas widget and a parent
#
#         self.layout().addWidget(self.figure)
#
#     def plot(self):
#         self.figure.plot()
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

