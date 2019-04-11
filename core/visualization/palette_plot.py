"""
The Palette Widget can be used to display a Palette Asset
"""

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import pickle
import sys
import cv2

from core.analysis.colorimetry.hilbert import *
from core.visualization.basic_vis import IVIANVisualization, ExportImageDialog
from core.data.computation import *
from core.gui.ewidgetbase import EGraphicsView
from core.visualization.dot_plot import DotPlot

from random import randint
import numpy as np


class PaletteWidget(QWidget):
    def __init__(self, parent):
        super(PaletteWidget, self).__init__(parent)
        self.palette_tree = None

        self.setLayout(QVBoxLayout(self))
        self.view = PaletteView(self)
        self.slider = QSlider(Qt.Horizontal, self)
        self.cb_mode = QComboBox(self)
        self.cb_mode.addItems(['Layer', 'Full Tree'])
        self.lbl_mode_hint = QLabel("Layer Index:", self)
        self.lbl_depth = QLabel("0", self)
        self.lbl_depth.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.layout().addWidget(self.view)
        self.cb_show_grid = QCheckBox("Show Grid", self)
        self.hbox_slider = QHBoxLayout(self)
        self.cb_sorting = QComboBox(self)
        self.cb_sorting.addItems(['Cluster', 'Frequency', "Hilbert"])

        self.hbox_ctrl = QHBoxLayout(self)
        self.layout().addItem(self.hbox_ctrl)
        self.layout().addItem(self.hbox_slider)

        self.hbox_ctrl.addWidget(QLabel("Mode: ", self))
        self.hbox_ctrl.addWidget(self.cb_mode)
        self.hbox_ctrl.addItem(QSpacerItem(0,0,QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.hbox_ctrl.addWidget(self.cb_show_grid)
        self.hbox_ctrl.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.hbox_ctrl.addWidget(QLabel("Sorting: ", self))
        self.hbox_ctrl.addWidget(self.cb_sorting)

        self.slider.setValue(4)

        self.hbox_slider.addWidget(self.lbl_mode_hint)
        self.hbox_slider.addWidget(self.slider)
        self.hbox_slider.addWidget(self.lbl_depth)

        self.slider.valueChanged.connect(self.draw_palette)
        self.cb_mode.currentTextChanged.connect(self.on_settings_changed)
        self.cb_show_grid.stateChanged.connect(self.on_settings_changed)
        self.cb_sorting.currentTextChanged.connect(self.on_settings_changed)

    def on_settings_changed(self):
        self.view.sorting = self.cb_sorting.currentText()
        self.view.mode = self.cb_mode.currentText()
        self.view.show_grid = self.cb_show_grid.isChecked()
        if self.cb_mode.currentText() == "Layer":
            self.lbl_mode_hint.setText("Layer Index:")
        else:
            self.lbl_mode_hint.setText("Layer Depth:")
        self.draw_palette()

    def set_palette(self, tree):
        self.palette_tree = tree
        self.slider.setRange(0, np.unique(self.palette_tree[0]).shape[0] - 1)
        self.view.palette_layer = self.palette_tree

    def draw_palette(self):
        self.lbl_depth.setText(str(self.slider.value()))
        self.view.mode = self.cb_mode.currentText()
        self.view.depth = self.slider.value()
        self.view.draw_palette()
        self.view.update()

    def clear_view(self):
        self.view.palette_layer = None
        self.view.image = None
        self.view.update()


class PaletteView(QWidget, IVIANVisualization):
    def __init__(self, parent, naming_fields = None):
        QWidget.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "palette_plot"
        self.palette_layer = None
        self.hilbert_lookup = get_hilbert_lookup()
        self.mode = "Layer"
        self.depth = 0
        self.image = None
        self.show_grid = False
        self.sorting = "Cluster"
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def draw_palette(self, target = None):
        if self.palette_layer is None:
            return
        all_layers = self.palette_layer[0]
        all_cols = self.palette_layer[1]
        all_bins = self.palette_layer[2]

        if target is None:
            t_height = self.height()
        else:
            t_height = target.height()

        layers_unique = np.unique(all_layers)
        if self.mode == "Layer":
            height = t_height
            layers = [layers_unique[self.depth]]
        else:
            self.depth = np.clip(self.depth, 1, None)
            height = t_height / self.depth
            layers = layers_unique[:self.depth]

        self.image = QImage(self.size(), QImage.Format_RGBA8888)

        qp = QPainter()
        pen = QPen()
        pen.setWidthF(0.1)
        pen.setColor(QColor(0,0,0,255))
        if target is None:
            qp.begin(self.image)
            t_width = self.width()
        else:
            qp.begin(target)
            t_width = target.width()
        qp.setPen(pen)
        # qp.setRenderHint(QPainter.Antialiasing)
        y = 0
        for i in layers:
            indices = np.where(all_layers == i)
            cols_to_draw = all_cols[indices]
            bins_to_draw = all_bins[indices]

            bin_total = np.sum(bins_to_draw)
            width_factor = t_width / bin_total
            x = 0

            if self.sorting == "Frequency":
                new_sort = np.argsort(bins_to_draw)[::-1]
                cols_to_draw = cols_to_draw[new_sort]
                bins_to_draw = bins_to_draw[new_sort]

            elif self.sorting == "Hilbert":
                indices = []
                for c in cols_to_draw:
                    c = tpl_bgr_to_lab(np.array([c[2], c[1], c[0]], np.uint8), False)
                    indices.append(self.hilbert_lookup[c[0], c[1], c[2]])
                new_sort = np.argsort(indices)
                cols_to_draw = cols_to_draw[new_sort]
                bins_to_draw = bins_to_draw[new_sort]

            for q in range(cols_to_draw.shape[0]):
                try:
                    color = cols_to_draw[q]
                    size = bins_to_draw[q] * width_factor
                    qp.fillRect(x - 0.5, y - 0.5, size + 1.0, height + 1.0, QColor(int(color[2]), int(color[1]), int(color[0])))
                    if self.show_grid:
                        qp.drawRect(x, y, size, height)
                    x += size
                except Exception as e:
                    pass
            y += height
        qp.end()

    def paintEvent(self, a0: QPaintEvent):
        if self.image is None:
            return
        qp = QPainter()
        pen = QPen()
        qp.begin(self)
        qp.setPen(pen)
        qp.drawImage(self.rect(), self.image)
        qp.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))

    def render_to_image(self, background: QColor, size: QSize):
        image = super(PaletteView, self).render_to_image(background, size)
        self.draw_palette(image)
        return image


class PaletteLABWidget(QWidget):
    def __init__(self, parent):
        super(PaletteLABWidget, self).__init__(parent)
        self.palette_tree = None
        self.setLayout(QVBoxLayout(self))
        self.view = PaletteLABView(self)

        self.w_ctrls2 = QWidget(self)
        self.w_ctrls2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.w_ctrls2.setLayout(QVBoxLayout(self.w_ctrls2))

        self.cb_mode = QComboBox(self)
        self.cb_mode.addItems(['Layer', 'Full Tree'])
        self.lbl_mode_hint = QLabel("Layer Index:", self.w_ctrls2)
        self.cb_show_grid = QCheckBox("Show Grid", self)

        self.hbox_slider = QHBoxLayout(self.w_ctrls2)
        self.w_ctrls2.layout().addItem(self.hbox_slider)

        self.slider = QSlider(Qt.Horizontal, self.w_ctrls2)
        self.slider_size = QSlider(Qt.Horizontal, self.w_ctrls2)
        self.slider_size.setRange(1, 100)
        self.slider_jitter = QSlider(Qt.Horizontal, self.w_ctrls2)
        self.slider_jitter.setRange(0, 100)
        self.slider_scale = QSlider(Qt.Horizontal, self.w_ctrls2)
        self.slider_scale.setRange(1, 30)

        self.lbl_depth = QLabel("0", self.w_ctrls2)
        self.lbl_depth.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        self.cb_background = QComboBox(self)
        self.cb_background.addItems(['White', "Light-Gray", 'Dark-Gray', 'Black'])
        self.cb_background.setCurrentText("Dark-Gray")

        self.hbox_ctrl = QHBoxLayout(self)

        self.hbox_ctrl.addWidget(QLabel("Mode: ", self))
        self.hbox_ctrl.addWidget(self.cb_mode)
        self.hbox_ctrl.addItem(QSpacerItem(0,0,QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.hbox_ctrl.addWidget(self.cb_show_grid)
        self.hbox_ctrl.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.hbox_ctrl.addWidget(QLabel("Background: ", self))
        self.hbox_ctrl.addWidget(self.cb_background)
        self.btn_ctrls = QPushButton("Show Controls", self)
        self.hbox_ctrl.addWidget(self.btn_ctrls)
        self.btn_ctrls.clicked.connect(self.toggle_controls)

        self.hbox_slider.addWidget(self.lbl_mode_hint)
        self.hbox_slider.addWidget(self.slider)
        self.hbox_slider.addWidget(QLabel("n-Merges:", self.w_ctrls2))
        self.hbox_slider.addWidget(self.lbl_depth)

        self.hbox_scale = QHBoxLayout(self.w_ctrls2)
        self.hbox_dot_size = QHBoxLayout(self.w_ctrls2)
        self.hbox_jitter = QHBoxLayout(self.w_ctrls2)

        self.w_ctrls2.layout().addItem(self.hbox_scale)
        self.w_ctrls2.layout().addItem(self.hbox_dot_size)
        self.w_ctrls2.layout().addItem(self.hbox_jitter)

        self.hbox_scale.addWidget(QLabel("Scale:", self.w_ctrls2))
        self.hbox_dot_size.addWidget(QLabel("Dot Size:", self.w_ctrls2))
        self.hbox_jitter.addWidget(QLabel("Jitter:", self.w_ctrls2))

        self.hbox_scale.addWidget(self.slider_scale)
        self.hbox_dot_size.addWidget(self.slider_size)
        self.hbox_jitter.addWidget(self.slider_jitter)

        self.layout().addWidget(self.view)
        self.layout().addItem(self.hbox_ctrl)
        self.layout().addWidget(self.w_ctrls2)

        self.cb_show_grid.setChecked(True)
        self.slider.setValue(12)

        self.slider_jitter.setValue(3)
        self.slider_scale.setValue(2)
        self.slider_size.setValue(2)

        self.slider.valueChanged.connect(self.on_settings_changed)
        self.slider_jitter.valueChanged.connect(self.on_settings_changed)
        self.slider_size.valueChanged.connect(self.on_settings_changed)
        self.slider_scale.valueChanged.connect(self.on_settings_changed)
        self.cb_mode.currentTextChanged.connect(self.on_settings_changed)
        self.cb_show_grid.stateChanged.connect(self.on_settings_changed)
        self.cb_background.currentTextChanged.connect(self.on_settings_changed)

        self.w_ctrls2.setVisible(False)
        self.show()

    def toggle_controls(self):
        v = not self.slider_size.isVisible()
        self.w_ctrls2.setVisible(v)

    def on_settings_changed(self):
        self.view.background = self.cb_background.currentText()
        self.view.mode = self.cb_mode.currentText()
        self.view.show_grid = self.cb_show_grid.isChecked()
        self.view.jitter = self.slider_jitter.value()
        self.view.dot_size = self.slider_size.value()
        self.view.scale = self.slider_scale.value()
        if self.cb_mode.currentText() == "Layer":
            self.lbl_mode_hint.setText("Layer Index:")
        else:
            self.lbl_mode_hint.setText("Layer Depth:")
        self.view.draw_palette()
        self.view.update()

    def set_palette(self, tree):
        self.palette_tree = tree
        self.slider.setRange(0, np.unique(self.palette_tree[0]).shape[0] - 1)
        self.view.palette_layer = self.palette_tree

    def draw_palette(self):
        if self.palette_tree is None:
            return
        self.lbl_depth.setText(str(np.amax(self.palette_tree[0]) - np.unique(self.palette_tree[0])[self.slider.value()]))
        self.view.mode = self.cb_mode.currentText()
        self.view.depth = self.slider.value()
        self.on_settings_changed()

    def clear_view(self):
        self.view.palette_layer = None
        self.view.update()


class PaletteLABView(QWidget, IVIANVisualization):
    def __init__(self, parent, naming_fields = None):
        QWidget.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "palette_ab_plot"
        self.palette_layer = None
        self.view = parent
        self.depth = 0
        self.image = None
        self.dot_size = 10
        self.scale = 8
        self.show_grid = True
        self.background = "Light-Gray"
        self.jitter = 10
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def draw_palette(self, target = None):
        if self.palette_layer is None:
            return
        self.image = QImage(self.size(), QImage.Format_RGBA8888)
        qp = QPainter()
        pen = QPen()
        pen.setWidthF(0.5)

        if target is None:
            qp.begin(self.image)
            t_width = self.width()
            t_height = self.height()
        else:
            qp.begin(target)
            t_width = target.width()
            t_height = target.height()

        qp.setRenderHint(QPainter.Antialiasing)
        if target is None:
            if self.background == "White":
                qp.fillRect(self.rect(), QColor(self.background))
                pen.setColor(QColor(0,0,0,200))
                self.grid_color = QColor(0,0,0,255)
            elif self.background == "Light-Gray":
                qp.fillRect(self.rect(), QColor(130,130,130))
                pen.setColor(QColor(0,0,0,200))
            elif self.background == "Dark-Gray":
                qp.fillRect(self.rect(), QColor(37, 37, 37))
                pen.setColor(QColor(255, 255, 255, 200))
            else:
                qp.fillRect(self.rect(), QColor(0,0,0))
                pen.setColor(QColor(255, 255, 255, 200))

        qp.setPen(pen)
        pen.setColor(self.grid_color)

        if self.show_grid:
            qp.drawLine(0, t_height / 2, t_width, t_height / 2)
            qp.drawLine(t_width / 2, 0, t_width / 2, t_height)
            qp.drawEllipse(t_width / 2 - self.scale * 128, t_height / 2 - self.scale * 128, self.scale * 256, self.scale * 256)
            qp.drawEllipse(t_width / 2 - self.scale * 64, t_height / 2 - self.scale * 64, self.scale * 128, self.scale * 128)
            qp.drawEllipse(t_width / 2 - self.scale * 32, t_height / 2 - self.scale * 32, self.scale * 64, self.scale * 64)
            if self.scale > 5:
                qp.drawEllipse(t_width / 2 - self.scale * 16, t_height / 2 - self.scale * 16, self.scale * 32,
                               self.scale * 32)
            if self.scale > 6:
                qp.drawEllipse(t_width / 2 - self.scale * 8, t_height / 2 - self.scale * 8, self.scale * 16,
                               self.scale * 16)
            if self.scale > 7:
                qp.drawEllipse(t_width / 2 - self.scale * 4, t_height / 2 - self.scale * 4, self.scale * 8,
                               self.scale * 8)
            if self.scale > 8:
                qp.drawEllipse(t_width / 2 - self.scale * 2, t_height / 2 - self.scale * 2, self.scale * 4,
                               self.scale * 4)
        counter = 0

        layer_idx = np.unique(self.palette_layer[0])[self.depth]
        indices = np.where(self.palette_layer[0] == layer_idx)
        cols_to_draw = self.palette_layer[1][indices]
        bins_to_draw = self.palette_layer[2][indices]

        for q in range(cols_to_draw.shape[0]):
            color = cols_to_draw[q]
            radius = self.dot_size
            lab = tpl_bgr_to_lab(color)

            # increase the visible number of dots:
            if self.jitter > 1:
                ndot_factor = self.jitter / 2
            else:
                ndot_factor = 1
            for i in range(int(bins_to_draw[q] * ndot_factor)):
                counter += 1
                path = QPainterPath()
                if self.jitter > 0:
                    rx = np.random.randint(-self.jitter, self.jitter)
                    ry = np.random.randint(-self.jitter, self.jitter)
                else:
                    rx, ry = 0,0
                path.addEllipse((t_width / 2) + ((self.scale * (1.0 * lab[1]) - radius) + rx),
                                (t_height / 2) + ((self.scale * (-1.0 * lab[2]) - radius) + ry),
                                radius, radius)
                qp.fillPath(path, QColor(int(color[2]), int(color[1]), int(color[0])))
        qp.end()

    def paintEvent(self, a0: QPaintEvent):
        if self.image is None:
            return
        qp = QPainter()
        pen = QPen()
        qp.begin(self)
        qp.setPen(pen)
        qp.drawImage(self.rect(), self.image)
        qp.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))

    def wheelEvent(self, a0: QWheelEvent):
        if a0.angleDelta().y() > 0:
            self.scale += 1
            self.view.slider_scale.setValue(self.scale)
        elif a0.angleDelta().y() < 0:
            self.scale -= 1
            self.view.slider_scale.setValue(self.scale)
        else:
            a0.ignore()

    def render_to_image(self, background: QColor, size: QSize):
        image = super(PaletteLABView, self).render_to_image(background, size)
        self.draw_palette(image)
        return image


class PaletteTimeWidget(QWidget):
    def __init__(self, parent):
        super(PaletteTimeWidget, self).__init__(parent)
        self.palette_tree = None
        self.setLayout(QVBoxLayout(self))
        self.scroll_area = QScrollArea(self)
        self.layout().addWidget(self.scroll_area)
        self.view = PaletteTimeView(self)
        self.scroll_area.setWidget(self.view)
        self.scroll_area.setWidgetResizable(True)
        self.slider = QSlider(Qt.Horizontal, self)
        self.lbl_mode_hint = QLabel("Layer Index:", self)
        self.lbl_depth = QLabel("0", self)
        self.lbl_depth.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        # self.layout().addWidget(self.view)
        self.cb_show_grid = QCheckBox("Show Grid", self)
        self.hbox_slider = QHBoxLayout(self)
        self.cb_sorting = QComboBox(self)
        self.cb_sorting.addItems(['Cluster', 'Frequency'])

        self.hbox_ctrl = QHBoxLayout(self)
        self.layout().addItem(self.hbox_ctrl)
        self.layout().addItem(self.hbox_slider)

        self.hbox_ctrl.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.hbox_ctrl.addWidget(self.cb_show_grid)
        self.hbox_ctrl.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.hbox_ctrl.addWidget(QLabel("Sorting: ", self))
        self.hbox_ctrl.addWidget(self.cb_sorting)

        self.hbox_slider.addWidget(self.lbl_mode_hint)
        self.hbox_slider.addWidget(self.slider)
        self.hbox_slider.addWidget(self.lbl_depth)

        self.slider.valueChanged.connect(self.draw_palette)
        self.cb_show_grid.stateChanged.connect(self.on_settings_changed)
        self.cb_sorting.currentTextChanged.connect(self.on_settings_changed)

    def on_settings_changed(self):
        self.view.sorting = self.cb_sorting.currentText()
        self.view.show_grid = self.cb_show_grid.isChecked()
        self.draw_palette()

    def set_palette(self, tree, times):
        self.palette_tree = tree
        self.view.times = times
        self.slider.setRange(0, np.unique(self.palette_tree[0][0]).shape[0] - 1)
        self.view.palette = self.palette_tree

    def draw_palette(self):
        self.lbl_depth.setText(str(self.slider.value()))
        self.view.depth = self.slider.value()
        self.view.draw_palette()
        # self.view.update()


class PaletteTimeView(EGraphicsView, IVIANVisualization):
    def __init__(self, parent, naming_fields = None):
        EGraphicsView.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "palette_barcode_plot"
        self.times = None
        self.palette = None
        self.depth = 0
        self.image = None
        self.show_grid = False
        self.sorting = "Cluster"
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.resolution = 1

    def draw_palette(self, target=None):
        if self.palette is None or self.times is None:
            return
        self.scene().clear()
        self.scene().setSceneRect(QRectF(0.0,0.0,4000.0,500.0))
        qp = QPainter()
        pen = QPen()
        pen.setWidthF(0.1)
        pen.setColor(QColor(0, 0, 0, 255))
        if target is None:
            self.image = QImage(QSize(4000, 500), QImage.Format_RGBA8888)
            qp.begin(self.image)
            t_width = self.width()
            # self.resize(4000, 500)
        else:
            qp.begin(target)
            t_width = target.width()
        qp.setPen(pen)

        x = 0
        time_sum = np.amax(self.times)
        for p, t in enumerate(self.palette):
            if p % self.resolution != 0:
                continue

            if target is None:
                b_width = self.image.width() / (len(self.palette) / self.resolution)
            else:
                b_width = target.width() / (len(self.palette) / self.resolution)
            all_layers = t[0]
            all_cols = t[1]
            all_bins = t[2]

            if target is None:
                t_height = self.image.height()
            else:
                t_height = target.height()

            layers_unique = np.unique(all_layers)
            height = t_height
            if self.depth >= layers_unique.shape[0]:
                return
            layers = [layers_unique[self.depth]]

            # qp.setRenderHint(QPainter.Antialiasing)
            y = 0
            for i in layers:
                indices = np.where(all_layers == i)
                cols_to_draw = all_cols[indices]
                bins_to_draw = all_bins[indices]

                bin_total = np.sum(bins_to_draw)
                width_factor = t_height / bin_total
                if self.sorting == "Frequency":
                    new_sort = np.argsort(bins_to_draw)
                    cols_to_draw = cols_to_draw[new_sort]
                    bins_to_draw = bins_to_draw[new_sort]
                for q in range(cols_to_draw.shape[0]):
                    color = cols_to_draw[q]
                    size = bins_to_draw[q] * width_factor
                    qp.fillRect(x - 0.5, y - 0.5, b_width + 1.0, size + 1.0,
                                QColor(int(color[2]), int(color[1]), int(color[0])))
                    if self.show_grid:
                        qp.drawRect(x, y, b_width, size)
                    y += size
            x += b_width
        qp.end()
        itm = self.scene().addPixmap(QPixmap(self.image.size()).fromImage(self.image))
        self.fitInView(itm.boundingRect(), Qt.KeepAspectRatio)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))

    def render_to_image(self, background: QColor, size: QSize):
        image = super(PaletteTimeView, self).render_to_image(background, size)
        self.draw_palette(image)
        return image

    def get_scene(self):
        return self.scene()


class MultiPaletteLABWidget(QWidget, IVIANVisualization):
    def __init__(self, parent, naming_fields=None):
        QWidget.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "palette_ab_plot"
        self.dot_plot = DotPlot(self, naming_fields=naming_fields)
        self.dot_plot.dot_size = 10
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.dot_plot)
        self.palette_tree = None
        self.slider = None
        self.spbox_depth = None
        self.depth = 10

    def get_param_widget(self):
        w = QWidget()
        w.setLayout(QHBoxLayout())
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(1, 20)
        self.slider.setValue(10)
        self.slider.valueChanged.connect(self.on_depth_changed)
        self.spbox_depth = QSpinBox(self)
        self.spbox_depth.setValue(10)
        self.spbox_depth.setRange(1, 20)
        self.spbox_depth.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self.spbox_depth.setValue)

        w.layout().addWidget(QLabel("Depth:", w))
        w.layout().addWidget(self.slider)
        w.layout().addWidget(self.spbox_depth)

        return w

    def render_to_image(self, background: QColor, size: QSize):
        self.dot_plot.font_size = self.font_size
        self.dot_plot.grid_color = self.grid_color

        print(self.grid_color)

        self.draw_palette()
        return self.dot_plot.render_to_image(background, size)

    def on_depth_changed(self):
        if self.slider is not None:
            self.depth = self.slider.value()
        self.draw_palette()

    def set_palettes(self, palettes):
        try:
            self.palette_tree = np.vstack(tuple(palettes.copy()))
        except Exception as e:
            print("Exception in set_palettes()", palettes)
            return
        layers = self.palette_tree[:, 1]
        if self.slider is not None:
            self.slider.setRange(0, len(np.unique(layers)) - 1)
            self.spbox_depth.setRange(0, len(np.unique(layers)) - 1)

        if not (0 <= self.depth <= len(np.unique(layers)) - 1):
            self.depth = len(np.unique(layers)) - 1
        self.draw_palette()

    def draw_palette(self):
        jitter = 0.5
        if self.palette_tree is None:
            return
        self.dot_plot.clear_view()
        self.dot_plot.add_grid("AB")
        try:
            layer_idx = np.unique(self.palette_tree[:, 1])[self.depth]
        except:
            layer_idx = np.unique(np.amax(np.unique(self.palette_tree[:, 1])))

        indices = self.palette_tree[:, 1]
        indices = np.where(indices == layer_idx)
        bins = self.palette_tree[indices[0]]
        bins_max = np.amax(bins[:, 5])

        pal = self.palette_tree[indices]
        labs = cv2.cvtColor(np.array([pal[:, 2:5] / 255.0, pal[:, 2:5] / 255.0], dtype=np.float32), cv2.COLOR_BGR2LAB)[0]
        chroma = lab_to_lch(labs)
        chroma = np.amax(chroma[:, 1])
        chroma2 = (np.ceil(chroma / 20)) * 20

        self.dot_plot.set_range_scale(int((128 / chroma2) * 100))

        u, indices = np.unique(labs, axis=0, return_index=True)
        labs = labs[indices]
        pal = pal[indices]

        for i in range(labs.shape[0]):
            lab = labs[i]
            rgb = pal[i, 2:5]
            n_dots = np.clip(np.nan_to_num(pal[i, 5] / bins_max * 20), 1, 20)
            for q in range(int(n_dots)):
                rx = np.random.normal(0, jitter)
                ry = np.random.normal(0, jitter)
                self.dot_plot.add_point(x=lab[1] + rx, y=-lab[2] + ry, z=lab[0], col=QColor(int(rgb[2]), int(rgb[1]), int(rgb[0])))

    def get_scene(self):
        return self.dot_plot.scene()