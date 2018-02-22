from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import os
import pickle
from collections import namedtuple
import numpy as np
from typing import List
from functools import partial
from glob import glob

from core.data.plugin import *
from core.visualization.image_plots import ImagePlotTime

from extensions.plugins.fiwi_tools.fiwi_visualizer.visualizations import *

MODE_FOREGROUND = 0


class ListEntry(QListWidgetItem):
    def __init__(self, name, path, parent=None):
        super(ListEntry, self).__init__(parent)
        self.setText(name)
        self.path = path



class MovieList(QDockWidget):
    def __init__(self, parent):
        super(MovieList, self).__init__(parent)
        self.visualizer = parent
        self.listWidget = QListWidget(self)
        self.setWidget(self.listWidget)

        self.listWidget.itemClicked.connect(self.on_item_change)
        self.items = []


    def list_files(self, path):
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
        self.visualizer.create_plot(item.path)
        # if self.visualizer.mode == MODE_FOREGROUND:
        widget = ColorDTWidget(self)
        self.visualizer.set_central(widget)
        with open(item.path, "rb") as f:
            data = pickle.load(f)
            widget.update_view(data)
