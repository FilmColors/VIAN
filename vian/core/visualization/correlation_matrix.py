import numpy as np
from collections import namedtuple
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from functools import partial

from vian.core.visualization.basic_vis import IVIANVisualization, MatrixPlot
from vian.core.visualization.bar_plot import BarPlot
from typing import *

CorrelationFeatureTuple = namedtuple("FeatureTuple", ["name", "voc_name", "class_obj", "id"])

class CorrelationVisualization(QWidget, IVIANVisualization):
    def __init__(self, parent, naming_fields = None):
        QWidget.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "correlation_plot"
        self.split = QSplitter()
        self.stack = QStackedWidget()

        self.barplot = CorrelationBarplot(self)
        self.matrix = CorrelationMatrix(self)

        self.stack.addWidget(self.matrix)
        self.stack.addWidget(self.barplot)
        self.matrix.onFeatureClicked.connect(self.on_feature_selected)

        self.back_button = QPushButton("Back", self.barplot)
        self.barplot.set_heads_up_widget(self.back_button)
        self.back_button.clicked.connect(partial(self.stack.setCurrentIndex, 0))
        self.back_button.move(10, 10)
        self.back_button.resize(100, 30)

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.split)
        self.controls = FeatureMatrixParamWidget(self)
        self.controls.onFeatureActivated.connect(self.on_filter_activated)
        self.split.addWidget(self.controls)
        self.split.addWidget(self.stack)
        self.controls.setMaximumWidth(300)
        # self.layout().addWidget(self.stack)

        self.features = []
        self.correlation_matrix = None

    def set_data(self, features:List[CorrelationFeatureTuple], correlation_matrix):
        self.features = features
        self.controls.on_features_changed(features)
        self.correlation_matrix = correlation_matrix
        self.matrix.set_data(features, correlation_matrix)
        self.barplot.set_data(features, correlation_matrix)
        self.matrix.frame_default()

    def get_param_widget(self):
        w = FeatureMatrixParamWidget(self)
        return w

    @pyqtSlot(object)
    def on_filter_activated(self, features):
        self.matrix.on_filter_changed(features)
        self.barplot.on_filter_changed(features)

    @pyqtSlot(object)
    def on_feature_selected(self, feature):
        self.barplot.set_current_feature(feature)
        self.barplot.draw()
        self.barplot.add_title("Keyword Frequencies for " + feature.name)
        self.stack.setCurrentIndex(1)
        self.barplot.frame_default()


class CorrelationBarplot(BarPlot):
    def __init__(self, parent, naming_fields=None):
        super(CorrelationBarplot, self).__init__(parent, naming_fields=naming_fields)
        self.naming_fields['plot_name'] = "correlation_bar_plot"
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))

        self.features = []
        self.matrix = None

        # All features to compare with
        self.active_features = []

        # The feature that is currently of interest
        self.current_feature = None

    def set_data(self, features:List[CorrelationFeatureTuple], matrix):
        self.active_features = features
        self.features = features
        self.matrix = matrix
        self.draw()

    def set_current_feature(self, current_feature:CorrelationFeatureTuple):
        self.current_feature = current_feature
        self.draw()

    @pyqtSlot(object)
    def on_filter_changed(self, features:List[CorrelationFeatureTuple]):
        self.active_features = features
        self.draw()

    def draw(self):
        self.clear_view()
        if self.current_feature is not None and self.matrix is not None:
            row = self.current_feature.id
            for f in self.active_features:
                b = self.add_bar(f.name, self.matrix[row][f.id])
        self.frame_default()


class CorrelationMatrix(MatrixPlot, IVIANVisualization):
    onFeatureClicked = pyqtSignal(object)

    def __init__(self, parent, title ="", naming_fields=None):
        super(CorrelationMatrix, self).__init__(parent, naming_fields=naming_fields)
        self.naming_fields['plot_name'] = "correlation_matrix_plot"
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.selection_rect = None
        self.active_features = []
        self.correlation_matrix = None

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-50, -50, 100, 100)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def set_data(self, features:List[CorrelationFeatureTuple], correlation_matrix):
        if correlation_matrix.shape[0] == 0:
            return
        self.max = np.amax(correlation_matrix)
        self.active_features = features
        self.correlation_matrix = correlation_matrix

        names = [f.name + f.voc_name + f.class_obj for f in self.active_features]
        if len(names) > 500:
            self.scene().addText("Too Many Keywords to plot, select a subset in the control panel.")
            return

        if len(names) > 100:
            names = None
        self.plot_data(correlation_matrix, names, features, draw_image=True)

    def on_enter_text(self, object):
        if self.selection_rect is not None:
            self.scene().removeItem(self.selection_rect)
        feature = object.meta
        # x = feature.id * self.dot_size
        x = self.active_features.index(feature) * self.dot_size
        width = self.matrix.shape[0] * self.dot_size
        self.selection_rect = self.scene().addRect(0, x, width, self.dot_size, QPen(), QBrush(QColor(230,100,100,100)))

    def on_leave_text(self, object):
        if self.selection_rect is not None:
            self.scene().removeItem(self.selection_rect)

    def on_filter_changed(self, features):
        if self.correlation_matrix is None or len(features) == 0:
            return

        self.active_features = []
        for i, f in enumerate(features):
            self.active_features.append(f)

        sub_mat = np.zeros(shape=(len(self.active_features), len(self.active_features)))
        for i, x in enumerate(self.active_features):
            for j, y in enumerate(self.active_features):
                sub_mat[i, j] = self.correlation_matrix[x.id, y.id]

        names = [f.name + f.voc_name + f.class_obj for f in self.active_features]
        if len(names) > 500:
            self.on_filter_changed(features[:500])
            return

        if len(names) > 100:
            names = None
        self.plot_data(sub_mat, names, self.active_features, draw_image=True)


    def on_text_clicked(self, object):
        feature = object.meta
        self.onFeatureClicked.emit(feature)


class FeatureMatrixParamWidget(QWidget):
    onFeatureActivated = pyqtSignal(object)
    onXScale = pyqtSignal(float)
    onImageScale = pyqtSignal(float)

    def __init__(self, parent):
        super(FeatureMatrixParamWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.param_list = QTreeWidget(self)
        self.layout().addWidget(self.param_list)
        self.sl_x_scale = QSlider(Qt.Horizontal, self)
        self.sl_x_scale.setRange(1, 100)
        self.sl_x_scale.setValue(10)
        self.hb_x_scale = QHBoxLayout(self)
        self.hb_x_scale.addWidget(QLabel("x-Scale", self))
        self.hb_x_scale.addWidget(self.sl_x_scale)
        self.sl_x_scale.valueChanged.connect(self.on_slider_x_scale)

        self.sl_img_scale = QSlider(Qt.Horizontal, self)
        self.sl_img_scale.setRange(1, 100)
        self.sl_img_scale.setValue(10)
        self.hb_img_scale = QHBoxLayout(self)
        self.hb_img_scale.addWidget(QLabel("Image-Scale", self))
        self.hb_img_scale.addWidget(self.sl_img_scale)
        self.sl_img_scale.valueChanged.connect(self.on_slider_img_scale)

        self.layout().addItem(self.hb_x_scale)
        self.layout().addItem(self.hb_img_scale)
        self.param_list.itemClicked.connect(self.on_clicked)
        self.features = []
        self.show()

    @pyqtSlot(object)
    def on_features_changed(self, features: List[CorrelationFeatureTuple]):
        self.param_list.clear()
        self.features.clear()
        curr_voc_name = None
        curr_voc_itm = None
        curr_class_name = None
        curr_class_itm = None

        for f in sorted(features, key=lambda x: (x.class_obj, x.voc_name, x.name)):
            if not f.class_obj == curr_class_name:
                curr_class_name = f.class_obj
                curr_class_itm = QTreeWidgetItem([curr_class_name])
                self.param_list.addTopLevelItem(curr_class_itm)
                curr_voc_name = None
            if not f.voc_name == curr_voc_name:
                curr_voc_name = f.voc_name
                curr_voc_itm = QTreeWidgetItem([f.voc_name])
                curr_class_itm.addChild(curr_voc_itm)

            itm = QTreeWidgetItem([f.name])
            itm.setCheckState(0, Qt.Unchecked)

            curr_voc_itm.addChild(itm)
            self.features.append((itm, f))

    def on_slider_x_scale(self):
        v = self.sl_x_scale.value() / 10
        self.onXScale.emit(v)

    def on_slider_img_scale(self):
        v = self.sl_img_scale.value() / 20
        self.onImageScale.emit(v)

    def on_clicked(self):
        result = []
        for f in self.features:
            if f[0].checkState(0) == Qt.Checked:
                result.append(f[1])
        self.onFeatureActivated.emit(result)