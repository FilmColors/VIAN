from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from typing import List
from collections import namedtuple

from core.data.plugin import *

from extensions.plugins.fiwi_tools.fiwi_visualizer.filmcolors_db import UniqueKeyword
FilterTuple = namedtuple("FilterTuple", ["table_name", "keyword_name"])

#region Filters

class QueryDock(QDockWidget):
    def __init__(self, parent, visualizer):
        super(QueryDock, self).__init__(parent)
        self.visualizer = visualizer

        self.inner = QStackedWidget(self)
        self.setWidget(self.inner)

