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
from extensions.plugins.fiwi_tools.fiwi_visualizer.filmcolors_db import Corpus
MODE_FOREGROUND = 0




class ListEntry(QListWidgetItem):
    def __init__(self, name, year, fm_id, parent=None):
        super(ListEntry, self).__init__(parent)
        self.setText(name)


class MovieList(QDockWidget):
    def __init__(self, parent):
        super(MovieList, self).__init__(parent)
        self.setWindowTitle("Corpus Manager")
        self.visualizer = parent
        self.listWidget = QTableWidget(self)

        self.inner_widget = QWidget()
        self.inner_widget.setLayout(QHBoxLayout(self))

        self.setWidget(self.inner_widget)

        self.left_widget = QWidget()
        self.left_widget.setLayout(QVBoxLayout())
        self.listWidget.setSelectionBehavior(self.listWidget.SelectRows)
        self.listWidget.setSortingEnabled(True)
        self.left_widget.layout().addWidget(self.listWidget)

        self.currentCorpusList = QTableWidget(self)
        self.currentCorpusList.setSelectionBehavior(self.listWidget.SelectRows)
        self.currentCorpusList.setSortingEnabled(True)

        self.right_widget = QWidget(self)
        self.right_widget.setLayout(QVBoxLayout())

        self.w_ctrls = QWidget()
        self.w_ctrls.setLayout(QHBoxLayout(self))
        self.btn_add = QPushButton("Add To Sub Corpus")
        self.btn_remove = QPushButton("Remove From Sub Corpus")
        self.w_ctrls.layout().addWidget(self.btn_add)
        self.w_ctrls.layout().addWidget(self.btn_remove)

        self.combo_box_CurrentSubCorpus = QComboBox(self)
        self.combo_box_CurrentSubCorpus.currentIndexChanged.connect(self.set_corpus)
        self.btn_new_sub_corpus = QPushButton("New Corpus")
        self.btn_new_sub_corpus.clicked.connect(self.create_corpus)
        self.btn_delete_sub_corpus = QPushButton("Delete Corpus")
        self.btn_delete_sub_corpus.clicked.connect(self.remove_corpus)
        self.w_corp_ctrl = QWidget(self)
        self.w_corp_ctrl.setLayout(QHBoxLayout(self))
        self.w_corp_ctrl.layout().addWidget(self.combo_box_CurrentSubCorpus)
        self.w_corp_ctrl.layout().addWidget(self.btn_new_sub_corpus)
        self.w_corp_ctrl.layout().addWidget(self.btn_delete_sub_corpus)
        self.line_edit_corpus_name = QLineEdit(self)
        self.line_edit_corpus_name.returnPressed.connect(self.set_corpus_name)


        self.right_widget.layout().addWidget(self.w_corp_ctrl)
        self.right_widget.layout().addWidget(self.line_edit_corpus_name)
        self.right_widget.layout().addWidget(self.w_ctrls)
        self.right_widget.layout().addWidget(self.currentCorpusList)

        self.inner_widget.layout().addWidget(self.left_widget)
        self.inner_widget.layout().addWidget(self.right_widget)

        # self.listWidget.itemClicked.connect(self.on_item_change)
        self.items = []

        self.btn_add.clicked.connect(self.add_to_corpus)
        self.btn_remove.clicked.connect(self.remove_from_corpus)


    def list_files(self, all_movies):
        self.listWidget.clear()
        self.items.clear()
        self.listWidget.setColumnCount(4)
        self.listWidget.setRowCount(0)
        self.listWidget.setHorizontalHeaderLabels(["DB-ID", "Name", "Year", "FileMaker ID"])
        for i, m in enumerate(all_movies):
            self.listWidget.insertRow(self.listWidget.rowCount())
            self.listWidget.setItem(i, 0, QTableWidgetItem(m.database_id))
            self.listWidget.setItem(i, 1, QTableWidgetItem(m.name))
            self.listWidget.setItem(i, 2, QTableWidgetItem(str(m.year)))
            self.listWidget.setItem(i, 3, QTableWidgetItem(m.fm_id))
            self.items.append(m)

    def create_corpus(self):
        corpus = Corpus("New Corpus")
        self.visualizer.corporas.append(corpus)
        self.update_combobox()

    def remove_corpus(self):
        self.visualizer.corporas.remove(self.visualizer.corporas[self.combo_box_CurrentSubCorpus.currentIndex()])
        self.update_combobox()

    def add_to_corpus(self):
        if self.visualizer.current_corpus() is None:
            return

        for idx in self.listWidget.selectedIndexes():
            self.visualizer.current_corpus().add_movie(self.items[idx.row()])

        self.visualizer.onCorporasChange.emit(self.visualizer.corporas)
        self.update_corpus_list()

    def remove_from_corpus(self):
        if self.visualizer.current_corpus() is None:
            return

        for idx in self.currentCorpusList.selectedIndexes():
            try:
                self.visualizer.current_corpus().remove_movie(self.visualizer.current_corpus().movies[idx.row()])
            except:
                pass
        self.visualizer.onCorporasChange.emit(self.visualizer.corporas)
        self.update_corpus_list()

    def update_corpus_list(self):
        self.currentCorpusList.clear()
        self.currentCorpusList.setColumnCount(4)
        self.currentCorpusList.setRowCount(0)
        self.currentCorpusList.setHorizontalHeaderLabels(["DB-ID", "Name", "Year", "FileMaker ID"])

        if self.visualizer.current_corpus() is None:
            return

        for i, m in enumerate(self.visualizer.current_corpus().movies):
            self.currentCorpusList.insertRow(self.currentCorpusList.rowCount())
            self.currentCorpusList.setItem(i, 0, QTableWidgetItem(m.database_id))
            self.currentCorpusList.setItem(i, 1, QTableWidgetItem(m.name))
            self.currentCorpusList.setItem(i, 2, QTableWidgetItem(str(m.year)))
            self.currentCorpusList.setItem(i, 3, QTableWidgetItem(m.fm_id))

    def set_corpus(self):
        self.visualizer.set_current_corpus(self.combo_box_CurrentSubCorpus.currentIndex())
        self.update_corpus_list()
        self.line_edit_corpus_name.setText(self.visualizer.current_corpus().name)


    def update_combobox(self):
        self.combo_box_CurrentSubCorpus.clear()
        for c in self.visualizer.corporas:
            self.combo_box_CurrentSubCorpus.addItem(c.name)


    def set_corpus_name(self):
        if self.visualizer.current_corpus() is not None:
            self.visualizer.current_corpus().name = self.line_edit_corpus_name.text()
            self.update_combobox()


