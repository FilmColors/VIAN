from core.gui.ewidgetbase import EDockWidget
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from core.data.interfaces import IProjectChangeNotify
from core.analysis.colorimetry.hilbert import create_hilbert_color_pattern, hilbert_mapping_3d, HilbertMode
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

        self.h_bgr = create_hilbert_color_pattern(8, multiplier=32, color_space=cv2.COLOR_Lab2RGB)
        self.h_indices = hilbert_mapping_3d(8, np.zeros(shape=(8,8,8)), HilbertMode.Indices_All)

        self.h_indices = np.array(self.h_indices)
        self.h_indices = np.array([self.h_indices[:, 0],self.h_indices[:, 1],self.h_indices[:, 2]])

        self.histogram = HistogramVis(self)
        self.histogram.plot(8**3 * [1.0], self.h_bgr)
        self.histogram.view.setYRange(min = 0.1, max = 1.0)
        self.histogram.view.setXRange(min = 0, max = 255)

        self.palette = PaletteVis(self)
        self.lt.addWidget(self.palette)
        self.vis_tab.addTab(self.histogram, "Histogram")

    def update_timestep(self, data):
        if data is not None:
            # hist_d = cv2.resize(data['hist'], dsize = (8,8,8), interpolation=cv2.INTER_CUBIC)
            hist_d = data['hist']

            for n in range(hist_d.ndim):
                hist_d = np.add.reduceat(hist_d, indices=range(0, hist_d.shape[n], 2), axis=n)
            hist_d = np.nan_to_num(hist_d)
            hist_d = hist_d[self.h_indices[0], self.h_indices[1], self.h_indices[2]]
            # hist_d = np.log(hist_d + 1)

            self.histogram.update_plot(hist_d)
            self.palette.plot(data['palette']['val'], data['palette']['col'])
