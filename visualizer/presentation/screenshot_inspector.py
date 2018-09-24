from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from random import sample
from core.gui.ewidgetbase import EGraphicsView
from core.data.computation import numpy_to_pixmap
from core.corpus.shared.entities import *
from core.visualization.palette_plot import *
class ScreenshotInspectorPopup(QMainWindow):
    def __init__(self, visualizer, screenshot_info:DBScreenshot, img, mask, clobj_indices):
        super(ScreenshotInspectorPopup, self).__init__(visualizer)
        self.visualizer = visualizer
        self.visualizer.query_worker.signals.onQueryResult.connect(self.on_query_result)
        self.setWindowFlags(Qt.Popup|Qt.FramelessWindowHint)

        self.visualizer.on_query(query_type="screenshot_info", shot_id=screenshot_info.screenshot_id)

        self.screenshot_info = screenshot_info
        self.img = img
        self.mask = mask
        self.clobj_indices = clobj_indices

        self.data_by_clobj = dict()
        self.central = QWidget(self)
        self.setCentralWidget(self.central)

        self.central.setLayout(QVBoxLayout())
        self.vsplit = QSplitter(Qt.Vertical, self)
        self.central.layout().addWidget(self.vsplit)
        self.upper_widget = QSplitter(self)
        # self.lower_widget = QSplitter(self)
        # self.lower_right = QSplitter(Qt.Vertical, self.lower_widget)
        # self.lower_left = QSplitter(Qt.Vertical, self.lower_widget)
        # self.lower_widget.addWidget(self.lower_left)
        # self.lower_widget.addWidget(self.lower_right)

        self.vsplit.addWidget(self.upper_widget)
        # self.vsplit.addWidget(self.lower_widget)

        self.screenshot_view = EGraphicsView(self)
        self.screenshot_view.set_image(numpy_to_pixmap(self.img))
        self.upper_widget.addWidget(self.screenshot_view)

        self.plot_palette = PaletteWidget(self)
        self.upper_widget.addWidget(self.plot_palette)

        # Heads Up widget to set the Classification Object
        self.heads_up_widget = QComboBox(self)
        for k in self.clobj_indices.keys():
            self.heads_up_widget.addItem(k)
        # We set the default Classification Object to be Global, this can be removed during th eAnalysis process
        # in VIAN, an should be defined somewhere but for now we just try to set it to Global. # todo
        try:
            self.heads_up_widget.setCurrentText("Global")
        except:
            pass
        self.screenshot_view.set_heads_up_widget(self.heads_up_widget)
        self.heads_up_widget.currentTextChanged.connect(self.on_clobj_changed)

        rect = QApplication.desktop().screenGeometry()
        rect.adjust(100,100,-100,-100)
        self.move(rect.x(), rect.y())
        self.resize(rect.width(), rect.height())

    def keyPressEvent(self, a0: QKeyEvent):
        if a0.key() == Qt.Key_Escape:
            self.close()
        else:
            a0.ignore()

    @pyqtSlot(object)
    def on_query_result(self, result):
        try:
            for k in result['data_by_classification_object'].keys():
                self.data_by_clobj[k] = dict(img_path = self.visualizer.db_root + result['data_by_classification_object'][k]['file_path'],
                                            palette = ColorPaletteAnalysis().from_json(result['data_by_classification_object'][k]['data'])['tree'])
            self.on_clobj_changed("Global")
        except Exception as e:
            print(e)

    def on_clobj_changed(self, clobj_name):
        try:
            clobj_id = self.clobj_indices[clobj_name]
            self.plot_palette.set_palette(self.data_by_clobj[clobj_id]['palette'])
            self.plot_palette.draw_palette()
            self.screenshot_view.set_image(numpy_to_pixmap(cv2.imread(self.data_by_clobj[clobj_id]['img_path'])))
        except Exception as e:
            print(e)
