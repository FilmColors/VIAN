import networkx as nx
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import os
import pickle

import numpy as np

from functools import partial
from glob import glob

from core.data.plugin import *
from core.visualization.image_plots import ImagePlotTime
#region -- Definitions --
VOC_PATH = "C:\\Users\\Gaudenz Halter\\Desktop\\Glossar_DB_exp_11022018_2.CSV"
DATABASE_FILE_EXT = "*.vian_db"


MODE_FOREGROUND = 0

class FiwiVisualizerExtension(GAPlugin):
    def __init__(self, main_window):
        super(FiwiVisualizerExtension, self).__init__(main_window)
        self.plugin_name = "FIWI Database Visualizer"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = FiwiVisualizer(parent)
        wnd.show()


class FiwiVisualizer(QMainWindow):
    def __init__(self, parent):
        super(FiwiVisualizer, self).__init__(parent)
        path = os.path.abspath("extensions/plugins/fiwi_tools/fiwi_visualizer/qt_ui/WindowFiwiDatabase.ui")
        uic.loadUi(path, self)
        self.actionOpen_Database.triggered.connect(self.on_load_database)

        self.database_file = None
        self.showFullScreen()

        self.current_widget = None


        self.items = []
        self.listWidget.itemClicked.connect(self.on_item_change)
        self.mode = None
        self.files = []

    def set_central(self, widget):
        if self.current_widget is not None:
            self.current_widget.hide()

            self.central.layout().removeWidget(self.current_widget)
        self.current_widget = widget
        self.central.layout().addWidget(self.current_widget)


    def on_load_database(self):
        try:
            file = QFileDialog.getOpenFileName(filter=DATABASE_FILE_EXT)[0]
            with open(file, "r") as f:
                if "foreground" in f.readline():
                    self.mode = MODE_FOREGROUND
                else:
                    self.mode = None
                if self.mode is not None:
                    self.list_files(os.path.split(file)[0])

        except Exception as e:
            print(e)
            QMessageBox.warning(self,"Could Not Open File", "Sorry, there has gone something wrong with the file opening")

    def list_files(self, path):
        print(path)

        self.listWidget.clear()
        self.items.clear()
        files = glob(path + "/*.pickle")
        for f in files:
            name = os.path.split(f)[1]
            itm = ListEntry(name, f, self.listWidget)
            self.listWidget.addItem(itm)
            self.items.append(itm)

        if self.listWidget.count() > 0:
            self.on_item_change(self.items[0])


    def on_item_change(self, item):
        self.create_plot(item.path)
        if self.mode == MODE_FOREGROUND:
            widget = ColorDTWidget(self)
            self.set_central(widget)
            with open(item.path, "rb") as f:
                data = pickle.load(f)
                widget.update_view(data)


    def create_plot(self, item):
        pass

    def keyPressEvent(self, a0: QKeyEvent):
        if a0.key() == Qt.Key_Escape:
            self.showNormal()


class ListEntry(QListWidgetItem):
    def __init__(self, name, path, parent=None):
        super(ListEntry, self).__init__(parent)
        self.setText(name)
        self.path = path


class ColorDTWidget(QWidget):
    def __init__(self, parent):
        super(ColorDTWidget, self).__init__(parent)
        self.fg_view = ImagePlotTime(self)
        self.bg_view = ImagePlotTime(self)
        self.gl_view = ImagePlotTime(self)
        self.setLayout(QVBoxLayout(self))

        self.tab = QTabWidget(self)
        self.tab.addTab(self.fg_view, "Foreground")
        self.tab.addTab(self.bg_view, "Background")
        self.tab.addTab(self.gl_view, "Global")

        self.layout().addWidget(self.tab)

    def update_view(self, data):

        indices = range(0, len(data['sat_glob']) * 1000, 1000)

        self.plot(self.gl_view, np.array(indices), np.array(data['sat_glob']), data['img_glob'])
        self.plot(self.fg_view, np.array(indices), np.array(data['sat_fg']), data['img_fg'])
        self.plot(self.bg_view, np.array(indices), np.array(data['sat_bg']), data['img_bg'])


    def plot(self,view, time, channel, imgs, is_liminance=True):
        view.clear_view()
        view.x_scale = 0.02
        view.y_scale = 1
        # indices = np.arange(0, channel.shape[0], self.nth_frame)
        # time = np.array(time)[indices]
        # channel = np.array(channel)[indices]
        # imgs = np.array(imgs)[indices]
        # if is_liminance:
        #     channel = np.multiply(np.divide(channel.astype(np.float32), 255), 100)

        for i, img in enumerate(imgs):
            view.add_image(time[i], channel[i] * 100, img, convert=False)

        view.update_grid()
        view.sort_images()
