from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from visualizer.data.cache import *
from functools import partial

class PresentationWidget(QWidget):
    def __init__(self, parent, visualizer, path = ""):
        super(PresentationWidget, self).__init__(parent)
        self.visualizer = visualizer
        if path != "":
            path = os.path.abspath(path)
            uic.loadUi(path, self)
        self.visualizer.query_worker.signals.onQueryResult.connect(self.on_query_result)

    @pyqtSlot(object)
    def on_query_result(self, obj):
        pass


class VisualizerVisualization(QMainWindow):
    onToFavorites = pyqtSignal(object, str)

    def __init__(self, parent, visualizer, visualization = None, settings_widget = None, inhibit_favorites = False):
        super(VisualizerVisualization, self).__init__(parent)
        self.visualization = None
        self.hovered = False
        self.visualizer = visualizer

        self.settings_widget = settings_widget
        self.settings_window = QMainWindow(self, Qt.Tool)
        if self.settings_widget is not None:
            self.settings_window.setCentralWidget(self.settings_widget)

        self.toolbar = QToolBar("Visualization Toolbar")
        self.a_magnify = self.toolbar.addAction(QIcon("qt_ui/icons/icon_magnification.png"), "")
        self.a_settings = self.toolbar.addAction(QIcon("qt_ui/icons/icon_settings_plot.png"), "")

        if not inhibit_favorites:
            self.a_to_plot_list = self.toolbar.addAction(QIcon("qt_ui/icons/icon_favorites.png"), "")
            self.a_to_plot_list.triggered.connect(self.on_to_favorites)

        self.a_reset = self.toolbar.addAction(QIcon("qt_ui/icons/icon_reset.png"), "")

        self.a_magnify.triggered.connect(self.on_focus_visualization)
        self.a_settings.triggered.connect(self.on_settings_opened)
        self.a_reset.triggered.connect(self.on_reset)

        self.onToFavorites.connect(self.visualizer.vis_favorites.on_to_favorites)

        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)
        if visualization is not None:
            self.settings_window.setWindowTitle("Settings: " + visualization.__class__.__name__)
            self.set_visualization(visualization)
        self.current_classification_object = 1
        self.show()

    def get_current_classification_object(self):
        return self.current_classification_object

    def set_current_classification_object(self, idx):
        self.current_classification_object = idx

    def on_settings_opened(self):
        self.settings_window.show()

    def set_visualization(self, vis):
        self.setCentralWidget(vis)
        self.visualization = vis

    def on_to_favorites(self):
        menu = QMenu(self)
        for k in self.visualizer.vis_favorites.get_sheet_names():
            a = menu.addAction(k)
            a.triggered.connect(partial(self.to_favorites, k))
        menu.popup(self.mapToGlobal(QPoint(0,0)))

    def to_favorites(self, name):
        cache = VisualizationCache(self.visualization.__class__, self.visualization.get_raw_data())
        self.onToFavorites.emit(cache, name)

    def on_focus_visualization(self):
        dialog = FocusVisualizationWindow(self, self.visualization, self)
        dialog.showFullScreen()

    def on_reset(self):
        try:
            self.visualization.reset_view()
        except Exception as e:
            print(e)

class FocusVisualizationWindow(QMainWindow):
    def __init__(self, parent, visualization, old_parent:VisualizerVisualization):
        super(FocusVisualizationWindow, self).__init__(parent)
        self.visualization = visualization.__class__(self)
        self.visualization.apply_raw_data(visualization.get_raw_data())
        self.old_parent = old_parent
        self.setWindowFlags(Qt.Window)
        self.setCentralWidget(self.visualization)

        self.settings_widget = self.visualization.get_param_widget()
        self.settings_window = QMainWindow(self, Qt.Tool)
        if self.settings_widget is not None:
            self.settings_window.setCentralWidget(self.settings_widget)

        self.toolbar = QToolBar("Visualization Toolbar")
        self.a_settings = self.toolbar.addAction(QIcon("qt_ui/icons/icon_settings_plot.png"), "")
        self.a_exit = self.toolbar.addAction(QIcon("qt_ui/icons/icon_close.png"), "")
        self.a_settings.triggered.connect(self.on_settings_opened)
        self.a_exit.triggered.connect(self.close)
        self.addToolBar(Qt.LeftToolBarArea, self.toolbar)

    def on_settings_opened(self):
        self.settings_window.show()

    def keyPressEvent(self, a0: QKeyEvent):
        if a0.key() == Qt.Key_Escape:
            self.close()
        else:
            a0.ignore()

    def closeEvent(self, a0: QCloseEvent):
        self.settings_window.close()
        super(FocusVisualizationWindow, self).closeEvent(a0)