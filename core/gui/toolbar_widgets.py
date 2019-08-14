import os
import cv2
import numpy as np
import time

from functools import partial
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRectF, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtWidgets import *
from core.data.enums import *
from collections import namedtuple
from core.gui.perspectives import Perspective

from core.gui.ewidgetbase import EToolBar

from core.data.computation import create_icon
# from core.gui.main_window import MainWindow

class WidgetsToolbar(EToolBar):
    def __init__(self, main_window):
        super(WidgetsToolbar, self).__init__(main_window, "Windows Toolbar")
        self.setWindowTitle("Windows Toolbar")

        self.a_player = self.addAction(create_icon("qt_ui/icons/icon_player.png"), "Player")
        self.a_outliner = self.addAction(create_icon("qt_ui/icons/icon_outliner.png"), "Outliner")
        self.a_timeline = self.addAction(create_icon("qt_ui/icons/icon_timeline.png"), "Timeline")
        self.a_player_controls = self.addAction(create_icon("qt_ui/icons/icon_player_controls.png"), "Player Controls")

        self.addSeparator()
        self.a_screenshot_manager = self.addAction(create_icon("qt_ui/icons/icon_screenshot_manager.png"), "Screenshot Manager")
        self.a_colorimetry = self.addAction(create_icon("qt_ui/icons/icon_colorimetry.png"), "Colorimetry")
        self.a_analyses = self.addAction(create_icon("qt_ui/icons/icon_analyses.png"), "Analyses")
        self.a_classification = self.addAction(create_icon("qt_ui/icons/icon_classification.png"), "Classification")
        self.a_upload = self.addAction(create_icon("qt_ui/icons/icon_upload.png"), "Upload")

        self.addSeparator()
        self.a_setup = self.addAction(create_icon("qt_ui/icons/icon_settings_plot.png"), "Setup")
        self.a_vocabulary = self.addAction(create_icon("qt_ui/icons/icon_vocabulary.png"), "Vocabulary")
        self.a_query = self.addAction(create_icon("qt_ui/icons/icon_query.png"), "Query")

        self.addSeparator()
        self.a_cl_obj = self.addAction(create_icon("qt_ui/icons/icon_classification_object.png"), "Select Classification Object")

        self.a_outliner.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_O))
        self.a_timeline.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_T))
        self.a_player_controls.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_P))
        self.a_analyses.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_A))
        self.a_classification.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_C))
        self.a_query.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_Q))
        self.a_upload.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_U))

        self.a_vocabulary.triggered.connect(self.main_window.create_vocabulary_manager)
        self.a_setup.triggered.connect(partial(self.main_window.switch_perspective, Perspective.ExperimentSetup))
        self.a_outliner.triggered.connect(self.main_window.create_outliner)
        self.a_timeline.triggered.connect(self.main_window.create_timeline)
        self.a_player_controls.triggered.connect(self.main_window.create_widget_player_controls)
        self.a_analyses.triggered.connect(self.main_window.create_analysis_results_widget)
        self.a_classification.triggered.connect(self.main_window.create_vocabulary_matrix)
        self.a_query.triggered.connect(partial(self.main_window.switch_perspective, Perspective.Query))
        self.a_upload.triggered.connect(self.main_window.create_corpus_client_toolbar)
        self.a_screenshot_manager.triggered.connect(self.main_window.create_screenshot_manager_dock_widget)
        self.a_colorimetry.triggered.connect(self.main_window.create_colorimetry_live)
        self.a_player.triggered.connect(self.main_window.create_widget_video_player)

        self.a_cl_obj.triggered.connect(self.show_classification_selector)
        self.show()

    def show_classification_selector(self):
        if self.main_window.project is None:
            return

        pos = self.mapToGlobal(self.widgetForAction(self.a_cl_obj).pos())
        menu = QMenu(self)
        for exp in self.main_window.project.experiments:
            for clobj in exp.get_classification_objects_plain():
                a = menu.addAction(clobj.name)
                a.triggered.connect(partial(self.main_window.on_classification_object_changed, clobj))

        menu.show()
        if pos.x() > self.main_window.x() + self.main_window.width() / 2:
            pos -= QPoint(menu.width(), 0)
        if pos.y() > self.main_window.y() + self.main_window.height() / 2:
            pos -= QPoint(0, menu.height())
        menu.move(pos)