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
    def __init__(self, parent):
        super(QueryDock, self).__init__(parent)
        self.setWindowTitle("Query")
        self.visualizer = parent
        self.inner = QWidget(self)
        self.inner.setLayout(QVBoxLayout(self.inner))

        self.controls = QWidget()
        self.controls.setLayout(QVBoxLayout())
        self.inner.layout().addWidget(self.controls)

        self.cb_Corporas = QComboBox(self)
        self.controls.layout().addWidget(self.cb_Corporas)
        self.cb_Corporas.currentIndexChanged.connect(self.visualizer.set_current_corpus)

        self.filter_controls = QWidget(self)
        self.filter_controls.setLayout(QHBoxLayout())
        self.btn_reset = QPushButton("Reset Filters")
        self.btn_query = QPushButton("Query")
        self.btn_query.clicked.connect(self.visualizer.on_start_query)

        self.fm_id_controls = QWidget(self)
        self.fm_id_controls.setLayout(QHBoxLayout(self))
        self.fm_id_controls.layout().addWidget(QLabel("FileMaker ID:"))
        self.lineEdit_fm_id = QLineEdit(self)
        self.lineEdit_fm_id.setPlaceholderText("z.B. 2_1_1")
        self.fm_id_controls.layout().addWidget(self.lineEdit_fm_id)

        self.year_controls = QWidget(self)
        self.year_controls.setLayout(QHBoxLayout())
        self.sB_year_start = QSpinBox(self.year_controls)
        self.sB_year_start.setRange(1850, 2018)
        self.sB_year_start.setValue(1900)
        self.sB_year_end = QSpinBox(self.year_controls)
        self.sB_year_end.setRange(1850, 2018)
        self.sB_year_end.setValue(2018)

        self.sB_year_start.valueChanged.connect(self.on_year_changed)
        self.sB_year_end.valueChanged.connect(self.on_year_changed)

        self.year_controls.layout().addWidget(self.sB_year_start)
        self.year_controls.layout().addWidget(self.sB_year_end)

        self.filter_controls.layout().addWidget(self.btn_reset)
        self.filter_controls.layout().addWidget(self.btn_query)

        self.n_images = QWidget(self)
        self.n_images.setLayout(QHBoxLayout(self))
        self.n_images.layout().addWidget(QLabel("n-Images:"))
        self.lbl_n_images = QLabel("50",self)
        self.sl_n_images = QSlider(Qt.Horizontal, self)
        self.sl_n_images.setRange(1, 2000)
        self.sl_n_images.setValue(50)
        self.sl_n_images.valueChanged.connect(self.on_n_images_changed)
        self.n_images.layout().addWidget(self.sl_n_images)
        self.n_images.layout().addWidget(self.lbl_n_images)

        self.controls.layout().addWidget(self.filter_controls)
        self.controls.layout().addWidget(self.fm_id_controls)
        self.controls.layout().addWidget(self.year_controls)
        self.controls.layout().addWidget(self.n_images)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(QWidget(self.scroll_area))
        self.scroll_area.widget().setLayout(QVBoxLayout(self.scroll_area))
        self.scroll_area.setWidgetResizable(True)
        self.inner.layout().addWidget(self.scroll_area)
        self.setWidget(self.inner)

        self.filters = []
        self.categories = []

        self.years = list(range(1900, 2018))

        self.current_filters = []

    def update_corpora_list(self, corporas):
        self.cb_Corporas.clear()
        for c in corporas:
            self.cb_Corporas.addItem(c.name)
        self.cb_Corporas.addItem("FilmColors Complete")

    def create_filter_menu(self, filters:List[UniqueKeyword]):
        for f in self.filters:
            f.close()
        self.filters = []

        category_names = []
        for f in filters:
            table_name,  keyword_name = f.to_query()
            itm = FilterItem(None, table_name, keyword_name)
            self.filters.append(itm)
            if table_name not in category_names:
                self.categories.append(FilterCategory(self, table_name, self))
                category_names.append(table_name)
            self.categories[category_names.index(table_name)].add_item(itm)

        for c in self.categories:
            self.scroll_area.widget().layout().addWidget(c)
            c.on_expand()

    @pyqtSlot(bool, str, str)
    def on_filter_changed(self, state, table_name, word_name):
        if state == False:
            for f in self.current_filters:
                if f[0] == table_name and f[1] == word_name:
                    self.current_filters.remove([table_name, word_name])
        else:
            self.current_filters.append([table_name, word_name])

        print(self.current_filters)

    def on_year_changed(self):
        self.years = list(range(self.sB_year_start.value(), self.sB_year_end.value(), 1))
        print(self.years)

    def on_n_images_changed(self):
        v = self.sl_n_images.value()
        self.lbl_n_images.setText(str(v))
        self.visualizer.n_stills_max = v


class FilterCategory(QFrame):
    def __init__(self, parent, name, query_dock):
        super(FilterCategory, self).__init__(parent)
        self.query_dock = query_dock
        self.setLayout(QVBoxLayout(self))
        self.btn_expand = QPushButton(name)
        self.layout().addWidget(self.btn_expand)

        self.is_expanded = True

        self.w_container = QWidget(self)
        self.w_container.setLayout(QVBoxLayout())
        self.layout().addWidget(self.w_container)

        self.keyword_items = []

        self.btn_expand.clicked.connect(self.on_expand)

    def add_item(self, item):
        self.w_container.layout().addWidget(item)
        item.onFilterStateChanged.connect(self.query_dock.on_filter_changed)
        self.keyword_items.append(item)

    def on_expand(self):
        self.is_expanded = not self.is_expanded

        if not self.is_expanded:
            for k in self.keyword_items:
                k.hide()
        else:
            for k in self.keyword_items:
                k.show()


class FilterItem(QCheckBox):
    onFilterStateChanged = pyqtSignal(bool, str, str)

    def __init__(self, parent, table_name, word_name):
        super(FilterItem, self).__init__(parent)
        self.table_name = table_name
        self.word_name = word_name
        self.setText(word_name)
        self.stateChanged.connect(self.on_state_changed)

    def on_state_changed(self, bool):
        self.onFilterStateChanged.emit(self.checkState(), self.table_name, self.word_name)

#endregion