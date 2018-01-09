from PyQt5.Qt import QApplication
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QScreen, QColor, QPainter, QPen, QResizeEvent
from PyQt5.QtWidgets import *

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

class EDockWidget(QDockWidget):
    def __init__(self, main_window, limit_size = True):
        super(EDockWidget, self).__init__()
        self.main_window = main_window
        self.setAttribute(Qt.WA_MacOpaqueSizeGrip, True)
        self.limit_size = limit_size

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

            if self.project():
                self.main_window.update_player_size()
                self.main_window.update_overlay()

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

    def project(self):
        try:
            return self.main_window.project
        except TypeError:
            print(self.__class__.__name__, ".main_window attributed of ", self, \
                " doesn't seem to be from derived from class MainWindow")


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


class EVisualizationDialog(EDialogWidget):
    def __init__(self, parent, visualization_widget):
        super(EVisualizationDialog, self).__init__(parent)
        self.vis_widget = visualization_widget
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(self.vis_widget)
        self.show()

    def closeEvent(self, QCloseEvent):
        self.parent().layout().addWidget(self.vis_widget)
        super(EVisualizationDialog, self).closeEvent(QCloseEvent)


class EAnalyseVisualization(QWidget):
    def __init__(self, parent, analyze):
        super(EAnalyseVisualization, self).__init__(parent)
        self.setLayout(QVBoxLayout(self))
        self.lbl = QLabel("<b>Visualization:", self)
        self.btn_expand = QPushButton("Expand", self)
        self.layout().addWidget(self.lbl)
        self.layout().addWidget(self.btn_expand)
        self.btn_expand.clicked.connect(self.on_expand)
        self.analyze = analyze
        self.figure = None

        self.show()

    def plot(self):
        print("plot() not implemented in:", self)

    def on_expand(self):
        if self.figure is not None:
            dialog = EVisualizationDialog(self, self.figure)


class EMatplotLibVis(EAnalyseVisualization):
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


# class MatplotlibFigure(FigureCanvas):
#     """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
#
#     def __init__(self, parent=None, analysis=None, width=5, height=4, dpi=300):
#         self.background = (50.0/255, 50.0/255, 50.0/255)
#         fig = Figure(figsize=(width, height), dpi=dpi, facecolor=self.background)
#         self.analysis = analysis
#         self.axes = fig.add_subplot(111)
#         self.axes.set_facecolor(self.background)
#
#         self.plot()
#
#         FigureCanvas.__init__(self, fig)
#         self.setParent(parent)
#
#         FigureCanvas.setSizePolicy(self,
#                                    QSizePolicy.Expanding,
#                                    QSizePolicy.Expanding)
#         FigureCanvas.updateGeometry(self)
#
#     def plot(self):
#         print("plot not  implemented in", self)


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
        self.setStyleSheet("QToolBar{background-color: gray;}")
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

        qp.fillRect(self.rect(), QColor(50, 50, 50))

        if self.show_indicator_frame:

            qp.drawRect(self.rect())

        qp.end()



    def show_indicator(self, visibility):
        self.show_indicator_frame = visibility
        self.update()

