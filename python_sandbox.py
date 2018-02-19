import csv
import cv2
import numpy as np
from glob import glob

from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout


paths = glob("/Users/gaudenz/Documents/VIAN/MacSintel/shots/*")
movie_path = "/Users/gaudenz/sintel-1280-surround.mp4"

imgs = []
for scr_p in paths:
    imgs.append(cv2.imread(scr_p))

# cap = cv2.VideoCapture(movie_path)
# width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
# height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
#
# for img in imgs:
#     img = cv2.resize(img, (width, height), interpolation=cv2.INTER_CUBIC)
#
# segm_length = 200
# scr_positions = np.zeros(len(imgs), dtype=np.uint16)
# scr_match = np.zeros(len(imgs))
#
# ret = True
# frame_idx = 0
# while (ret):
#     segm = np.zeros(shape=(height, width, 3), dtype=np.float32)
#     for i in range(segm_length):
#         ret, frame = cap.read()
#
#     for i, img in enumerate(imgs):
#         match = np.argmin(np.sum((segm - frame[..., np.newaxis]) ** 2, axis=[1, 2, 3]))
#         if scr_match[i] < match:
#             scr_match[i] = match
#
#
#
#

# -*- coding: utf-8 -*-
"""
This example demonstrates many of the 2D plotting capabilities
in pyqtgraph. All of the plots may be panned/scaled by dragging with 
the left/right mouse buttons. Right click on any plot to show a context menu.
"""


from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg


#QtGui.QApplication.setGraphicsSystem('raster')
app = QtGui.QApplication([])
#mw = QtGui.QMainWindow()
#mw.resize(800,800)

class PyqtGraphImageView(QWidget):
    def __init__(self, parent):
        super(PyqtGraphImageView, self).__init__(parent)
        self.setLayout(QHBoxLayout(self))
        self.show()

    def plot(self, x, y, imgs):
        plot = pg.PlotWidget(title="Basic plotting examples")
        plot.resize(1000, 600)
        plot.setWindowTitle('pyqtgraph example: Plotting')

        # Enable antialiasing for prettier plots
        pg.setConfigOptions(antialias=True)

        # p1 = win.addPlot(title="Basic array plotting", y=np.random.normal(size=100))


        for i, img in enumerate(imgs):
            itm = pg.ImageItem(np.rot90(img, k=3))
            plot.addItem(itm, pg.PlotDataItem(xValues=[10], yValues=[50]))
            itm.setRect(QtCore.QRectF(x[i], y[i], img.shape[1] * 0.1, img.shape[0] * 0.1))

        self.layout().addWidget(plot)


mw = QMainWindow()
plot_w = PyqtGraphImageView(mw)

plot_w.plot(range(len(imgs)), range(len(imgs)), imgs)

mw.setCentralWidget(plot_w)
mw.show()
## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
