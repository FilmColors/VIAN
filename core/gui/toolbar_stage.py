
import os
import cv2
import numpy as np
import time

from functools import partial
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRectF, pyqtSlot
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import *
from core.data.enums import *
from collections import namedtuple

from core.data.computation import *
from core.gui.ewidgetbase import EDockWidget, EToolBar, ImagePreviewPopup


class StageSelectionToolbar(EToolBar):
    def __init__(self, main_window):
        super(StageSelectionToolbar, self).__init__(main_window, "Stage Selection Toolbar")
        self.setWindowTitle("Stage Selection Toolbar")

        self.action_player = self.addAction(create_icon("qt_ui/icons/icon_export_screenshot.png"), "")
        self.toggle_annotation = self.addAction(create_icon("qt_ui/icons/icon_toggle_annotations.png"), "")

        self.toggle_annotation.setToolTip("Toggle Annotations on Screenshots")
        self.action_export.setToolTip("Export Screenshots")

        self.action_export.triggered.connect(self.on_export)
        self.toggle_annotation.triggered.connect(self.on_toggle_annotations)

        self.show()