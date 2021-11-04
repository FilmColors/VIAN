import os
import cv2
import numpy as np
import time
from typing import TYPE_CHECKING

from functools import partial
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRectF, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtWidgets import *
from vian.core.data.enums import *
from collections import namedtuple
from vian.core.gui.perspectives import Perspective

from vian.core.gui.ewidgetbase import EToolBar
from vian.core.data.computation import create_icon, is_vian_light
if TYPE_CHECKING:
    from vian.core.gui.main_window import MainWindow


class WidgetsToolbar(EToolBar):
    def __init__(self, main_window):
        super(WidgetsToolbar, self).__init__(main_window, "Windows Toolbar")
        self.setWindowTitle("Windows Toolbar")

        self.a_player = self.addAction(create_icon("qt_ui/icons/icon_player.png"), "Player")
        self.a_outliner = self.addAction(create_icon("qt_ui/icons/icon_outliner.png"), "Outliner")
        self.a_timeline = self.addAction(create_icon("qt_ui/icons/icon_timeline.png"), "Timeline")
        self.a_player_controls = self.addAction(create_icon("qt_ui/icons/icon_player_controls.png"), "Player Controls")
        self.a_inspector = self.addAction(create_icon("qt_ui/icons/icon_inspector.png"), "Inspector")


        self.addSeparator()
        self.a_screenshot_manager = self.addAction(create_icon("qt_ui/icons/icon_screenshot_manager.png"), "Screenshot Manager")


        self.a_colorimetry = self.addAction(create_icon("qt_ui/icons/icon_colorimetry.png"), "Colorimetry")
        self.a_analyses = self.addAction(create_icon("qt_ui/icons/icon_analyses.png"), "Analyses")
        self.a_classification = self.addAction(create_icon("qt_ui/icons/icon_classification.png"), "Classification")
        self.a_upload = self.addAction(create_icon("qt_ui/icons/icon_upload.png"), "Upload")

        self.addSeparator()
        self.a_setup = self.addAction(create_icon("qt_ui/icons/icon_settings_plot.png"), "Setup")
        self.a_vocabulary = self.addAction(create_icon("qt_ui/icons/icon_vocabulary.png"), "Vocabulary")
        self.a_corpus = self.addAction(create_icon("qt_ui/icons/icon_corpus.png"), "Corpus")
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
        self.a_inspector.setShortcut(QKeySequence(Qt.Key_Alt + Qt.Key_I))

        self.a_vocabulary.triggered.connect(self.main_window.create_vocabulary_manager)
        self.a_setup.triggered.connect(self.main_window.create_experiment_editor)
        self.a_outliner.triggered.connect(self.main_window.create_outliner)
        self.a_timeline.triggered.connect(self.main_window.create_timeline)
        self.a_player_controls.triggered.connect(self.main_window.create_widget_player_controls)
        self.a_analyses.triggered.connect(self.main_window.create_analysis_results_widget2)
        self.a_classification.triggered.connect(self.main_window.create_vocabulary_matrix)
        self.a_query.triggered.connect(partial(self.main_window.create_query_widget))
        # self.a_upload.triggered.connect(self.main_window.create_corpus_client_toolbar)
        self.a_screenshot_manager.triggered.connect(self.main_window.create_screenshot_manager_dock_widget)
        self.a_colorimetry.triggered.connect(self.main_window.create_colorimetry_live)
        self.a_player.triggered.connect(self.main_window.create_widget_video_player)
        self.a_corpus.triggered.connect(self.main_window.create_corpus_widget)
        self.a_inspector.triggered.connect(self.main_window.create_inspector)

        self.a_cl_obj.triggered.connect(self.show_classification_selector)

        self.hook_visibility(self.main_window.player_dock_widget, self.a_player)
        self.hook_visibility(self.main_window.outliner, self.a_outliner)
        self.hook_visibility(self.main_window.timeline, self.a_timeline)
        self.hook_visibility(self.main_window.player_controls, self.a_player_controls)
        self.hook_visibility(self.main_window.screenshots_manager_dock, self.a_screenshot_manager)
        self.hook_visibility(self.main_window.colorimetry_live, self.a_colorimetry)
        self.hook_visibility(self.main_window.web_view, self.a_analyses)
        self.hook_visibility(self.main_window.vocabulary_matrix, self.a_classification)
        # self.hook_visibility(self.main_window.corpus_client_toolbar, self.a_upload)
        self.hook_visibility(self.main_window.experiment_dock, self.a_setup)
        self.hook_visibility(self.main_window.vocabulary_manager, self.a_vocabulary)
        self.hook_visibility(self.main_window.corpus_widget, self.a_corpus)
        self.hook_visibility(self.main_window.query_widget, self.a_query)
        self.hook_visibility(self.main_window.inspector, self.a_inspector)


        if is_vian_light():
            self.a_colorimetry.setVisible(False)
            self.a_analyses.setVisible(False)
            self.a_classification.setVisible(False)
            self.a_query.setVisible(False)
            self.a_corpus.setVisible(False)
            self.a_cl_obj.setVisible(False)

        # self.main_window = main_window
        self.main_window.vocabulary_manager.visibilityChanged.connect(partial(self.on_visibility_changed, self.main_window.vocabulary_manager, self.a_vocabulary))
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

    def hook_visibility(self, widget, action):
        widget.visibilityChanged.connect(partial(self.on_visibility_changed, widget, action))

    def on_visibility_changed(self, widget:QWidget, action:QAction):
        if widget.isVisible():
            self.widgetForAction(action).setStyleSheet("QWidget { background-color: QLinearGradient(x1:0, y1:0, x2:0, y2:1, stop:1 #212121, stop:0.4 #3f7eaf, stop:0.2 #3f7eaf, stop:0.1 #3f7eaf); }")
        else:
            self.widgetForAction(action).setStyleSheet("QWidget { background-color: #303030; }")