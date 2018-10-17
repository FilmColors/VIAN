from core.gui.ewidgetbase import EDockWidget
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from core.data.interfaces import IProjectChangeNotify
from core.analysis.colorimetry.hilbert import create_hilbert_color_pattern, hilbert_mapping_3d, HilbertMode
from core.visualization.palette_plot import PaletteWidget, PaletteLABWidget, PaletteTimeWidget
import cv2
import numpy as np

from core.visualization.basic_vis import *

class ColorimetryLiveWidget(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(ColorimetryLiveWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Colorimetry")
        self.lt = QVBoxLayout(self)
        self.central = QWidget()
        self.central.setLayout(self.lt)

        self.inner.setCentralWidget(self.central)

        self.vis_tab = QTabWidget(self)
        self.lt.addWidget(self.vis_tab)

        # self.h_bgr = create_hilbert_color_pattern(8, multiplier=32, color_space=cv2.COLOR_Lab2RGB)
        # self.h_indices = hilbert_mapping_3d(8, np.zeros(shape=(8,8,8)), HilbertMode.Indices_All)
        #
        # self.h_indices = np.array(self.h_indices)
        # self.h_indices = np.array([self.h_indices[:, 0],self.h_indices[:, 1],self.h_indices[:, 2]])

        # self.histogram = HistogramVis(self)
        # self.histogram.plot(8**3 * [1.0], self.h_bgr)
        # self.histogram.view.setYRange(min = 0.1, max = 1.0)
        # self.histogram.view.setXRange(min = 0, max = 255)

        # self.palette = PaletteVis(self)
        self.palette = PaletteWidget(self)
        self.lab_palette = PaletteLABWidget(self)
        self.time_palette = PaletteTimeWidget(self)
        # self.lt.addWidget(self.palette)
        self.vis_tab.addTab(self.palette, "Tree-Palette")
        self.vis_tab.addTab(self.lab_palette, "LAB-Palette")
        self.vis_tab.addTab(self.time_palette, "Time Palette")
        self.vis_tab.currentChanged.connect(self.on_tab_changed)
        # self.vis_tab.addTab(self.histogram, "Histogram")

    def update_timestep(self, data):
        if data is not None:
            try:
                self.palette.set_palette(data['palette'])
                self.lab_palette.set_palette(data['palette'])
                if self.vis_tab.currentIndex() == 0:
                    self.palette.draw_palette()
                elif self.vis_tab.currentIndex() == 1:
                    self.lab_palette.draw_palette()
            except Exception as e:
                print("Exception in ColormetryWidget.update_timestep()", str(e))

    def on_tab_changed(self):
        if self.vis_tab.currentIndex() == 0:
            self.palette.draw_palette()
        elif self.vis_tab.currentIndex() == 1:
            self.lab_palette.draw_palette()

    def plot_time_palette(self, data):
        try:
            self.time_palette.set_palette(data[0], data[1])
            self.time_palette.draw_palette()
        except:
            print("Exception in ColorimetryLiveWidget::plot_time_palette()")
            pass

    def resizeEvent(self, *args, **kwargs):
        super(ColorimetryLiveWidget, self).resizeEvent(*args, **kwargs)
        self.on_tab_changed()

    def on_selected(self, sender, selected):
        pass

    def on_closed(self):
        self.palette.clear_view()
        self.lab_palette.clear_view()

    def on_changed(self, project, item):
        pass

    def on_loaded(self, project):
        pass