from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from visualizer2.data.cache import *
from visualizer2.presentation.presentation_widget import VisualizerVisualization


class VisualizationDock(QDockWidget):
    def __init__(self, parent, visualization_cache:VisualizationCache):
        super(VisualizationDock, self).__init__(parent)
        self.visualization = visualization_cache.vis_class(self)
        self.vis_frame = VisualizerVisualization(None, parent.visualizer, self.visualization, self.visualization.get_param_widget(), True)
        self.setWidget(self.vis_frame)
        self.visualization.apply_raw_data(visualization_cache.raw_data)


class VisFavToolbar(QToolBar):
    def __init__(self, parent, fav_window):
        super(VisFavToolbar, self).__init__(parent)
        self.fav_window = fav_window
        self.a_new = self.addAction("New Sheet")
        self.a_new.triggered.connect(self.on_new)

    def on_new(self):
        r = QInputDialog.getText(self, "New Sheet", "Insert the Name of the new Sheet:")
        if r[1]:
            self.fav_window.new_sheet(r[0])


class VisFavoritesWindow(QMainWindow):
    def __init__(self, parent, visualizer):
        super(VisFavoritesWindow, self).__init__(parent)
        self.setWindowTitle("All Stored Plots")
        self.central = QTabWidget(self)
        self.setCentralWidget(self.central)
        self.toolbar = VisFavToolbar(self, self)
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)
        self.visualizer = visualizer
        self.sheets = dict()
        self.new_sheet("Default")
        self.resize(800, 500)

    def new_sheet(self, name = "New Sheet"):
        sheet = VisFavorites(self, self.visualizer)
        self.sheets[name] = sheet
        self.central.addTab(sheet, name)

    def get_sheet_names(self):
        return self.sheets.keys()

    @pyqtSlot(object, str)
    def on_to_favorites(self, vis_cache, name):
        self.sheets[name].on_to_favorites(vis_cache)


class VisFavorites(QMainWindow):
    def __init__(self, parent, visualizer):
        super(VisFavorites, self).__init__(parent)
        self.setWindowTitle("Favorites")
        self.visualizer = visualizer
        self.visualization_docks = []
        self.c = QWidget()
        self.c.setFixedWidth(1)
        self.setCentralWidget(self.c)

    @pyqtSlot(object)
    def on_to_favorites(self, vis_cache):
        dock = VisualizationDock(self, vis_cache)
        self.visualization_docks.append(dock)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        dock.show()
