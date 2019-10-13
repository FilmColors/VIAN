import os
import cv2
import numpy as np
import time

from functools import partial
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt, QPoint, QRectF, pyqtSlot, QRect
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import *
from core.data.enums import *
from collections import namedtuple

from core.data.computation import *
from core.container.project import VIANProject
from core.container.screenshot import Screenshot
from core.data.exporters import ScreenshotsExporter
from core.data.interfaces import IProjectChangeNotify
from core.gui.Dialogs.screenshot_exporter_dialog import DialogScreenshotExporter
from core.gui.ewidgetbase import EDockWidget, EToolBar, ImagePreviewPopup
from core.visualization.image_plots import ImagePlotCircular, VIANPixmapGraphicsItem, ImagePlotTime, ImagePlotPlane
from core.analysis.color_feature_extractor import ColorFeatureAnalysis
from core.gui.ewidgetbase import ExpandableWidget, ESimpleDockWidget

SCALING_MODE_NONE = 0
SCALING_MODE_WIDTH = 1
SCALING_MODE_HEIGHT = 2
SCALING_MODE_BOTH = 3

from threading import Lock

#TODO we should move the ProjectChanged Loaded and Closed Dispatcher into the ScreenshotManagerDockWidget
class ScreenshotsToolbar(EToolBar):
    def __init__(self, main_window, screenshot_manager):
        super(ScreenshotsToolbar, self).__init__(main_window, "Screenshots Toolbar")
        self.setWindowTitle("Screenshots")

        self.manager = screenshot_manager
        self.action_export = self.addAction(create_icon("qt_ui/icons/icon_export_screenshot.png"), "")
        self.toggle_annotation = self.addAction(create_icon("qt_ui/icons/icon_toggle_annotations.png"), "")

        self.toggle_annotation.setToolTip("Toggle Annotations on Screenshots")
        self.action_export.setToolTip("Export Screenshots")

        self.action_export.triggered.connect(self.on_export)
        self.toggle_annotation.triggered.connect(self.on_toggle_annotations)

        self.show()

    def on_export(self):
        self.main_window.on_export_screenshots()

    def on_toggle_annotations(self):
        self.manager.toggle_annotations()


class SMSegment(object):
    def __init__(self, name, segm_id, segm_start):
        self.segm_name = name
        self.segm_id = segm_id
        self.segm_start = segm_start
        self.segm_images = []
        self.scr_captions = []
        self.scr_caption_offset = QPoint(0,0)


class ScreenshotsManagerDockWidget(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(ScreenshotsManagerDockWidget, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Screenshot")
        self.m_display = self.inner.menuBar().addMenu("Display")
        self.a_static = self.m_display.addAction("Static")
        self.a_static.setCheckable(True)
        self.a_static.setChecked(True)
        self.a_scale_width =self.m_display.addAction("Reorder by Width")
        self.a_scale_width.setCheckable(True)
        self.a_scale_width.setChecked(False)

        self.lbl_n = None
        self.bar = None
        self.lbl_slider = None

        self.curr_visualization = "Row-Column"

        self.a_static.triggered.connect(self.on_static)
        self.a_scale_width.triggered.connect(self.on_scale_to_width)
        self.m_display.addSeparator()
        self.a_follow_time = self.m_display.addAction(" Follow Time")
        self.a_follow_time.setCheckable(True)
        self.a_follow_time.setChecked(True)
        self.a_follow_time.triggered.connect(self.on_follow_time)
        self.m_display.addSeparator()
        self.a_toggle_name = self.m_display.addAction(" Show Segment Names")
        self.a_toggle_name.setCheckable(True)
        self.a_toggle_name.setChecked(False)
        self.a_toggle_name.triggered.connect(self.on_toggle_name)

        self.a_show_only_current = self.m_display.addAction(" Only Show Current Segment")
        self.a_show_only_current.setCheckable(True)
        self.a_show_only_current.setChecked(False)
        self.a_show_only_current.triggered.connect(self.on_toggle_show_current)

        self.m_plots = self.inner.menuBar().addMenu("Visualizations")
        self.a_scr_plot = self.m_plots.addAction("Screenshot Manager")
        self.a_ab_plot = self.m_plots.addAction("AB-Plot")
        self.a_lc_plot = self.m_plots.addAction("LC-Plot")
        self.a_dt_plot = self.m_plots.addAction("Color-dT")

        self.inner.resize(400, self.height())
        self.tab = None
        self.ab_view = None
        self.lc_view = None
        self.color_dt = None
        self.slider_image_size = None
        self.lbl_slider_size = None
        self.screenshot_manager = None

        self.color_dt_mode = "Saturation"
        self.ab_view_mean_cache = dict()

        # self.inner.addToolBar(ScreenshotsToolbar(main_window, self.main_window.screenshots_manager))

    def on_static(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_NONE
        self.screenshot_manager.arrange_images()
        self.a_scale_width.setChecked(False)

        if self.bar is not None:
            self.bar.setEnabled(True)

    def on_toggle_name(self):
        state = self.a_toggle_name.isChecked()
        self.screenshot_manager.show_segment_name = state
        self.screenshot_manager.update_manager()

    def on_scale_to_width(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_WIDTH
        self.screenshot_manager.arrange_images()
        self.a_static.setChecked(False)

        if self.bar is not None:
            self.bar.setEnabled(False)

    def on_scale_to_height(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_HEIGHT

    def on_scale_to_both(self):
        self.screenshot_manager.scaling_mode = SCALING_MODE_BOTH

    def on_follow_time(self):
        self.screenshot_manager.follow_time = self.a_follow_time.isChecked()

    def create_bottom_bar(self):
        bar = QStatusBar(self)
        l = QHBoxLayout(bar)

        self.slider_n_per_row = QSlider(Qt.Horizontal, self)
        self.slider_n_per_row.setRange(1, 20)
        self.slider_n_per_row.setValue(10)
        self.slider_n_per_row.setStyleSheet("QSlider{padding: 2px; margin: 2px; background: transparent}")

        self.slider_n_per_row.valueChanged.connect(self.on_n_per_row_changed)
        self.lbl_slider = QLabel("N-Columns:")
        self.lbl_slider.setStyleSheet("QLabel{padding: 2px; margin: 2px; background: transparent}")
        bar.addPermanentWidget(self.lbl_slider)
        bar.addPermanentWidget(self.slider_n_per_row)
        self.lbl_n = QLabel("\t" + str(self.slider_n_per_row.value()))
        bar.addPermanentWidget(self.lbl_n)

        self.slider_image_size = QSlider(Qt.Horizontal, self)
        self.slider_image_size.setRange(1, 200)
        self.slider_image_size.setValue(10)
        self.slider_image_size.setStyleSheet("QSlider{padding: 2px; margin: 2px; background: transparent}")

        self.slider_image_size.valueChanged.connect(self.on_image_size_changed)
        self.lbl_slider_size = QLabel("Image-Size::")
        self.lbl_slider_size.setStyleSheet("QLabel{padding: 2px; margin: 2px; background: transparent}")
        bar.addPermanentWidget(self.lbl_slider_size)
        bar.addPermanentWidget(self.slider_image_size)
        self.slider_image_size.setVisible(False)
        self.lbl_slider_size.setVisible(False)
        self.inner.setStatusBar(bar)
        self.bar_row_column = bar

    def set_manager(self, screenshot_manager):
        # self.tab = QTabWidget(self.inner)
        # self.tab.addTab(screenshot_manager, "Screenshot Manager")
        self.manager_dock = ESimpleDockWidget(self.inner, screenshot_manager, "Screenshots")
        self.inner.addDockWidget(Qt.TopDockWidgetArea, self.manager_dock, Qt.Horizontal)
        # t = QWidget()
        # t.setMinimumHeight(1)
        # t.setMinimumWidth(1)
        # self.inner.setCentralWidget(t)

        self.ab_view = ImagePlotCircular(self)
        self.ab_ctrls = self.ab_view.get_param_widget()
        w = QWidget(self.tab)
        w.setLayout(QVBoxLayout())
        w.layout().addWidget(self.ab_view)
        w.layout().addWidget(ExpandableWidget(w, "Plot Controls", self.ab_ctrls, popup=True))
        # self.tab.addTab(w, "AB-Plane")
        self.la_dock = ESimpleDockWidget(self.inner, w, "LA-View")
        self.inner.addDockWidget(Qt.TopDockWidgetArea, self.la_dock, Qt.Horizontal)

        self.color_dt = ImagePlotTime(self)
        self.color_dt_ctrls = self.color_dt.get_param_widget()
        # hl4 = QHBoxLayout(self.color_dt_ctrls)
        # hl4.addWidget(QLabel("Channel:", self.color_dt_ctrls))
        # self.color_dt_ctrls.layout().addItem(hl4)
        # cbox_channel = QComboBox(self.color_dt_ctrls)
        # cbox_channel.addItems(["Saturation", "Hue", "Chroma", "Luminance", "A", "B"])
        # cbox_channel.currentTextChanged.connect(self.color_dt_mode_changed)
        # hl4.addWidget(cbox_channel)

        self.lc_view = ImagePlotPlane(self, range_y=[0, 255])
        self.color_lc_view = self.lc_view.get_param_widget()
        w3 = QWidget()
        w3.setLayout(QVBoxLayout())
        w3.layout().addWidget(self.lc_view)
        w3.layout().addWidget(ExpandableWidget(w3, "Plot Controls", self.color_lc_view, popup=True))
        self.lc_dock = ESimpleDockWidget(self.inner, w3, "LC-View")
        self.inner.addDockWidget(Qt.TopDockWidgetArea, self.lc_dock, Qt.Horizontal)
        # self.tab.addTab(w3, "LC-Plane")

        w2 = QWidget()
        w2.setLayout(QVBoxLayout())
        w2.layout().addWidget(self.color_dt)
        w2.layout().addWidget(ExpandableWidget(w2, "Plot Controls", self.color_dt_ctrls, popup=True))
        self.dt_dock = ESimpleDockWidget(self.inner, w2, "Color-dT")
        self.inner.addDockWidget(Qt.BottomDockWidgetArea, self.dt_dock, Qt.Horizontal)
        # self.tab.addTab(w2, "Color-dt")

        self.setWidget(self.tab)

        self.inner.tabifyDockWidget(self.manager_dock, self.la_dock)
        self.inner.tabifyDockWidget(self.la_dock, self.lc_dock)
        self.manager_dock.raise_()
        self.dt_dock.hide()
        self.screenshot_manager = screenshot_manager
        self.create_bottom_bar()

        self.a_scr_plot.triggered.connect(self.manager_dock.show)
        self.a_ab_plot.triggered.connect(self.la_dock.show)
        self.a_lc_plot.triggered.connect(self.lc_dock.show)
        self.a_dt_plot.triggered.connect(self.dt_dock.show)

        self.main_window.currentClassificationObjectChanged.connect(self.screenshot_manager.on_classification_object_changed)

    def on_toggle_show_current(self):
        state = self.a_show_only_current.isChecked()
        self.screenshot_manager.only_show_current_segment = state
        self.screenshot_manager.frame_segment(self.screenshot_manager.current_segment_index)

    def on_n_per_row_changed(self, value):
        if self.curr_visualization == "Row-Column":
            self.screenshot_manager.n_per_row = value + 1
            self.lbl_n.setText("\t" + str(value))
            self.screenshot_manager.arrange_images()
            self.screenshot_manager.frame_segment(self.screenshot_manager.current_segment_index)

        elif self.curr_visualization == "AB-Plane":
            self.ab_view.set_range_scale(self.slider_n_per_row.value() / 0.01)

        elif self.curr_visualization == "Color-dT":
            self.color_dt.set_x_scale(self.slider_n_per_row.value() / 0.01)

    def on_image_size_changed(self):
        self.ab_view.set_image_scale(self.slider_image_size.value())
        self.color_dt.set_image_scale(self.slider_image_size.value())

    def color_dt_mode_changed(self, v):
        self.color_dt_mode = v
        for scr in self.main_window.project.screenshots:
            self.update_screenshot(scr)

    def remove_screenshot(self, scr):
        self.color_dt.remove_image_by_uid(scr.unique_id)
        self.ab_view.remove_image_by_uid(scr.unique_id)
        self.lc_view.remove_image_by_uid(scr.unique_id)

    def on_loaded(self, project:VIANProject):
        project.onScreenshotGroupAdded.connect(self.connect_scr_group)
        for grp in project.screenshot_groups:
            self.connect_scr_group(grp)
            for scr in grp.screenshots:
                self.add_screenshot(scr)
        project.onScreenshotsHighlighted.connect(self.on_screenshots_highlighted)

    def on_closed(self):
        self.color_dt.clear_view()
        self.ab_view.clear_view()
        self.ab_view.add_grid()
        self.lc_view.clear_view()
        self.lc_view.add_grid()

    @pyqtSlot(object)
    def on_screenshots_highlighted(self, screenshots):
        if len(screenshots) == 0:
            self.color_dt.set_highlighted([], True)
            self.ab_view.set_highlighted([], True)
            self.lc_view.set_highlighted([], True)
        else:
            uids = [scr.unique_id for scr in screenshots]
            self.color_dt.set_highlighted_by_uid(uids)
            self.ab_view.set_highlighted_by_uid(uids)
            self.lc_view.set_highlighted_by_uid(uids)

    def connect_scr_group(self, grp):
        grp.onScreenshotAdded.connect(self.add_screenshot)
        grp.onScreenshotRemoved.connect(self.remove_screenshot)

    @pyqtSlot(object)
    def add_screenshot(self, scr:Screenshot):
        scr.onImageSet.connect(self.update_screenshot)
        scr.onAnalysisAdded.connect(self.on_analysis_added)
        self.update_screenshot(scr)

    def on_analysis_added(self, a):
        self.update_screenshot(a.target_container)

    @pyqtSlot(object, object, object)
    def update_screenshot(self, scr, ndarray=None, pixmap=None):
        if self.main_window.project is None:
            return
        clobj = self.main_window.project.active_classification_object
        if clobj is None:
            try:
                a = scr.get_connected_analysis(ColorFeatureAnalysis, as_clobj_dict=True)["default"][0].get_adata()
            except Exception as e:
                # Analysis is missing or not yet computed
                a = None
        else:
            try:
                a = scr.get_connected_analysis(ColorFeatureAnalysis, as_clobj_dict=True)[clobj][0].get_adata()
            except Exception as e:
                a = None
        if a is None:
            return
        x = scr.movie_timestamp
        sat = a['saturation_l']
        lab = a['color_lab']
        lch = lab_to_lch(lab)

        if self.color_dt_mode == "Saturation":
            y = sat * 100
        elif self.color_dt_mode == "Luminance":
            y = lab[0] * 100
        elif self.color_dt_mode == "Chroma":
            y = lch[1] * 100
        elif self.color_dt_mode == "A":
            y = lab[1] / 255 * 100
        elif self.color_dt_mode == "B":
            y = lab[2] / 255 * 100
        elif self.color_dt_mode == "Hue":
            y = lch[2] / (2 * np.pi) * 100
        else:
            y = sat

        if pixmap is None:
            ndarray = scr.get_img_movie(ignore_cl_obj=False)
            if ndarray.shape[2] == 3:
                pixmap = numpy_to_pixmap(ndarray)
            else:
                 pixmap = numpy_to_pixmap(ndarray, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True)

        try:
            exists = self.color_dt.update_item(scr.unique_id, [x, y], pixmap)
            if not exists:
                self.color_dt.add_image(x,
                                        y,
                                        ndarray,
                                        uid=scr.unique_id,
                                        convert=False,
                                        channels=dict(chroma=lch[1],
                                                      luminance=lch[0],
                                                      hue=((lch[2] + np.pi) / (2 * np.pi) * 100),
                                                      saturation=y))
            exists = self.ab_view.update_item(scr.unique_id, [128 - lab[1], 128 - lab[2]], pixmap)
            if not exists:
                self.ab_view.add_image(128 - lab[1],
                                       128 - lab[2],
                                       ndarray,
                                       to_float=True,
                                       convert=False,
                                       uid=scr.unique_id)
            exists = self.lc_view.update_item(scr.unique_id, [lab[1], lab[0], lab[2]], pixmap)
            if not exists:
                self.lc_view.add_image(lab[1],
                                       lab[0],
                                       ndarray,
                                       convert=False,
                                       uid=scr.unique_id,
                                       z=lab[2])
        except Exception as e:
            log_error(e)


class ScreenshotsManagerWidget(QGraphicsView, IProjectChangeNotify):
    """
    Implements IProjectChangeNotify
    """
    def __init__(self,main_window, parent = None, ab_view = None, color_dt_view = None):
        super(ScreenshotsManagerWidget, self).__init__(parent)

        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        self.setRenderHints(QtGui.QPainter.Antialiasing|QtGui.QPainter.SmoothPixmapTransform)

        self.is_hovered = False
        self.ctrl_is_pressed = False
        self.shift_is_pressed = False
        self.follow_time = True
        self.show_segment_name = False
        self.only_show_current_segment = False

        self.font = QFont("Consolas")
        self.font_size = 68
        self.font_size_segments = 120
        self.font.setPointSize(self.font_size)
        self.color = QColor(225,225,225)

        self.loading_icon = None
        self.loading_text= None

        self.setDragMode(self.RubberBandDrag)
        self.setRubberBandSelectionMode(Qt.IntersectsItemShape)
        self.rubberband_rect = QtCore.QRect(0, 0, 0, 0)
        self.curr_scale = 1.0
        self.curr_image_scale = 1.0

        self.scaling_mode = SCALING_MODE_NONE

        self.main_window = main_window
        self.main_window.onSegmentStep.connect(self.frame_segment)

        self.scene = ScreenshotsManagerScene(self)
        self.setScene(self.scene)

        self.project = None
        self.images_plain = []
        self.images_segmentation = []
        self.captions = []
        self.scr_captions = []
        self.selected = []
        self.selection_frames = []

        self.write_lock = Lock()

        self.selected = []

        self.current_segment_index = 0
        self.current_segment_frame = None

        self.x_offset = 100
        self.y_offset = 200
        self.border_width = 1500
        self.border_height = 1000
        self.segment_distance = 100
        self.img_height = 0
        self.img_width = 0

        self.n_per_row = 10

        self.n_images = 0

        # self.setBaseSize(500,500)
        self.rubberBandChanged.connect(self.rubber_band_selection)

        self.qimage_cache = dict()

    def set_loading(self, state):
        if state:
            self.clear_manager()
            lbl = QLabel()
            movie = QtGui.QMovie(os.path.abspath("qt_ui/icons/loading512.gif"))
            lbl.setMovie(movie)
            lbl.setAttribute(Qt.WA_NoSystemBackground)
            movie.start()

            font = QFont("Consolas", 36)
            self.loading_icon = self.scene.addWidget(lbl)
            self.loading_text = self.scene.addText("Loading Screenshots... please wait.", font)
            self.loading_text.setDefaultTextColor(QColor(255,255,255))
            self.loading_icon.setPos(256, 256)
            self.loading_text.setPos(100, 786)
            self.scene.removeItem(self.current_segment_frame)

            rect = QRectF(0.0, 0.0, 1280, 1024)
            self.fitInView(rect, QtCore.Qt.KeepAspectRatio)
        else:
            if self.loading_icon is not None:
                self.scene.removeItem(self.loading_icon)
                self.scene.removeItem(self.loading_text)
            self.update_manager()
            self.center_images()

    def toggle_annotations(self):
        if len(self.selected) == 0:
            return

        state = not self.selected[0].screenshot_obj.annotation_is_visible
        for s in self.selected:
            # Only change those which aren't already
            if s.screenshot_obj.annotation_is_visible != state:
                if state and s.screenshot_obj.img_blend is not None:
                    s.setPixmap(numpy_to_pixmap(s.screenshot_obj.img_blend))
                    s.screenshot_obj.annotation_is_visible = state
                else:
                    s.setPixmap(numpy_to_pixmap(s.screenshot_obj.get_img_movie()))
                    s.screenshot_obj.annotation_is_visible = False
        pass

    def update_manager(self):
        """
        Recreating the Data Structures
        :return: 
        """
        if self.project is None:
            return
        last_items = dict()
        for img in self.images_plain:
            last_items[img.screenshot_obj.unique_id] = img
        self.clear_manager()

        current_segment_id = 0
        current_sm_object = None
        new_qimage_cache = dict()
        for s in self.project.screenshots:

            # If this Screenshot belongs to a new Segment, append the last SMObject to the list
            if s.scene_id != current_segment_id:
                if current_sm_object is not None:
                    self.images_segmentation.append(current_sm_object)

                current_segment_id = s.scene_id
                segment = self.project.get_segment_of_main_segmentation(current_segment_id - 1)
                if segment is not None:
                    current_sm_object = SMSegment(segment.get_name(), segment.ID, segment.get_start())

            if s.unique_id in last_items:
                item_image = last_items[s.unique_id]
            else:
                # Should we use the Annotated Screenshot?
                if s.annotation_is_visible and s.img_blend is not None:
                    image = s.img_blend
                else:
                    image = s.get_img_movie()

                if image is None:
                    continue
                # Convert to Pixmap
                # Cache the converted QPixamps if these are not the initial place holders
                if image.shape[0] > 100:
                    # Check if the Image is already in the cache
                    # if str(s.unique_id) in self.qimage_cache:
                    #     qpixmap = self.qimage_cache[str(s.unique_id)]
                    # else:
                    try:
                        if image.shape[2] == 4:
                            qpixmap = numpy_to_pixmap(image, cvt=cv2.COLOR_BGRA2RGBA, with_alpha=True)
                        else:
                            qpixmap = numpy_to_pixmap(image)

                        self.qimage_cache[str(s.unique_id)] = qpixmap
                    except Exception as e:
                        log_error(e)
                        continue
                    # new_qimage_cache[str(s.unique_id)] = qpixmap
                else:
                    qpixmap = numpy_to_pixmap(image)

                item_image = ScreenshotManagerPixmapItems(qpixmap, self, s)
            self.scene.addItem(item_image)

            self.images_plain.append(item_image)
            if current_sm_object is not None:
                current_sm_object.segm_images.append(item_image)

                scr_lbl = self.scene.addText(str(s.shot_id_segm), self.font)
                scr_lbl.setPos(item_image.pos() + QPoint(10, item_image.qpixmap.height()))
                scr_lbl.setDefaultTextColor(self.color)
                # scr_lbl.setFlag(QGraphicsItem.ItemIgnoresTransformations)
                current_sm_object.scr_captions.append(scr_lbl)
                current_sm_object.scr_caption_offset = QPoint(10, item_image.qpixmap.height())
                self.scr_captions.append(scr_lbl)

        if current_sm_object is not None:
            self.images_segmentation.append(current_sm_object)

        self.qimage_cache = new_qimage_cache
        self.clear_selection_frames()
        self.arrange_images()

        if self.project.get_main_segmentation() is None \
                or len(self.project.get_main_segmentation().segments) == 0:
            self.center_images()

    def clear_manager(self):
        self.clear_scr_captions()

        for img in self.images_plain:
            self.scene.removeItem(img)
        self.images_plain = []
        self.clear_captions()

        self.clear_selection_frames()
        if self.current_segment_frame is not None:
            self.scene.removeItem(self.current_segment_frame)
            self.current_segment_frame = None

        if self.loading_icon is not None:
            self.scene.removeItem(self.loading_icon)
        if self.loading_text is not None:
            self.scene.removeItem(self.loading_text)
        self.images_segmentation = []

    def arrange_images(self):
        self.clear_captions()

        y = self.border_height
        if len(self.images_plain) > 0:
            img_width = self.images_plain[0].pixmap().width()
            img_height = self.images_plain[0].pixmap().height()
            x_offset = int(img_width / 7)
            y_offset = int(img_height / 7)
            y_offset = x_offset
            caption_width = int(img_width / 1.5)

            self.scene.setSceneRect(self.sceneRect().x(), self.sceneRect().y(), self.n_per_row * (img_width + x_offset), self.sceneRect().width())
        else:
            return

        if self.scaling_mode == SCALING_MODE_WIDTH:
            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            viewport_width = viewport_size.x()
            image_scale = round(img_width / (viewport_size.x()), 4)
            self.n_per_row = np.clip(int(np.floor((viewport_width + 0.5 * img_width) / (img_width + x_offset))), 1, None)

        if len(self.images_segmentation) > 0:
            for segm in self.images_segmentation:
                self.add_line(y)

                self.add_caption(100, y + 100, segm.segm_id)
                if self.show_segment_name:
                    self.add_caption(100, y + 250, segm.segm_name)

                x_counter = 0
                x = caption_width - (x_offset + img_width)
                for i, img in enumerate(segm.segm_images):
                    if x_counter == self.n_per_row - 1:
                        x = caption_width
                        x_counter = 1
                        y += (y_offset + img_height)
                    else:
                        x_counter += 1
                        x += (x_offset + img_width)

                    img.setPos(x, y + int(img_height/5))
                    img.selection_rect = QtCore.QRect(x, y + int(img_height/5), img_width, img_height)
                    segm.scr_captions[i].setPos(img.pos() + segm.scr_caption_offset)


                y += (2 * img_height)
        else:
            x_counter = 0
            x = caption_width - (x_offset + img_width)
            for i, img in enumerate(self.images_plain):
                if x_counter == self.n_per_row - 1:
                    x = caption_width
                    x_counter = 1
                    y += (y_offset + img_height)
                else:
                    x_counter += 1
                    x += (x_offset + img_width)

                img.setPos(x, y + int(img_height / 5))
                img.selection_rect = QtCore.QRect(x, y + int(img_height / 5), img_width, img_height)

        self.scene.setSceneRect(self.sceneRect().x(), self.sceneRect().y(), self.n_per_row * (img_width + x_offset) - 0.5 * img_width, y)

        # Drawing the New Selection Frames
        self.draw_selection_frames()

        self.img_height = img_height
        self.img_width = img_width

    def add_line(self, y):
        p1 = QtCore.QPointF(0, y)
        p2 = QtCore.QPointF(self.scene.sceneRect().width(), y)

        pen = QtGui.QPen()
        pen.setColor(QtGui.QColor(200, 200, 200))
        pen.setWidth(5)
        line = self.scene.addLine(QtCore.QLineF(p1, p2), pen)
        self.captions.append(line)
        return line

    def add_caption(self, x, y, text):
        caption = self.scene.addText(str(text), self.font)
        caption.setDefaultTextColor(self.color)
        caption.setPos(QtCore.QPointF(x, y))
        # caption.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.captions.append(caption)
        return caption

    def clear_selection_frames(self):
        for s in self.selection_frames:
            self.scene.removeItem(s)
        self.selection_frames = []

    def clear_captions(self):
        with self.write_lock:
            for cap in self.captions:
                self.scene.removeItem(cap)
            self.captions = []

    def clear_scr_captions(self):
        with self.write_lock:
            for cap in self.scr_captions:
                self.scene.removeItem(cap)

            self.scr_captions = []

    def select_image(self, images, dispatch = True):
        self.selected = images

        # Drawing the New Selection Frames
        self.draw_selection_frames()

        if dispatch:
            sel = []
            for i in self.selected:
                sel.append(i.screenshot_obj)
            self.project.set_selected(self, sel)

    def draw_selection_frames(self):
        self.clear_selection_frames()
        if len(self.selected) > 0:
            for i in self.selected:
                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(255, 160, 74))
                pen.setWidth(25)
                item = QtWidgets.QGraphicsRectItem(QtCore.QRectF(i.selection_rect))
                item.setPen(pen)
                # rect = QtCore.QRectF(i.selection_rect)
                self.selection_frames.append(item)
                self.scene.addItem(item)

    def center_images(self):
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def frame_image(self, image):
        rect = image.sceneBoundingRect()
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.curr_scale = self.sceneRect().width() / rect.width()

    def frame_screenshot(self, scr_item):
        for s in self.images_plain:
            if isinstance(s, ScreenshotManagerPixmapItems) and s.screenshot_obj == scr_item:
                rect = s.sceneBoundingRect()
                self.fitInView(rect, Qt.KeepAspectRatio)
                self.curr_scale = self.sceneRect().width() / rect.width()
                break

    def frame_segment(self, segment_index, center = True):
        self.current_segment_index = segment_index
        self.arrange_images()

        if self.follow_time:
            x = self.scene.sceneRect().width()
            y = self.scene.sceneRect().height()
            width = 0
            height = 0

            if self.only_show_current_segment:
                for i, img_segm in enumerate(self.images_segmentation):
                    if img_segm.segm_id - 1 != self.current_segment_index:
                        for img in img_segm.segm_images:
                            img.hide()
                        for cap in img_segm.scr_captions:
                            cap.hide()
                    else:
                        for img in img_segm.segm_images:
                            img.show()
                        for cap in img_segm.scr_captions:
                            cap.show()

            # # Segments that are empty are not represented in self.images_segmentation
            # if segment_index >= len(self.images_segmentation):
            #     return

            index = -1
            for i, s in enumerate(self.images_segmentation):
                try:
                    if s.segm_id == segment_index + 1:
                        index = i
                except:
                    return

            if index == -1:
                return

            # Determining the Bounding Box
            for img in self.images_segmentation[index].segm_images:
                if img.scenePos().x() < x:
                    x = img.scenePos().x()
                if img.scenePos().y() < y:
                    y = img.scenePos().y()
                if img.scenePos().y() + img.pixmap().width() > width:
                    width = img.scenePos().x() + img.pixmap().width()
                if img.scenePos().y() + img.pixmap().height() > height:
                    height = img.scenePos().y() + img.pixmap().height()


            if self.current_segment_frame is not None:
                self.scene.removeItem(self.current_segment_frame)



            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(251, 95, 2, 60))
            pen.setWidth(20)
            self.current_segment_frame = self.scene.addRect(0, y-int(self.img_height/5) - 10, self.sceneRect().width() + 100, height - y + int(self.img_height / 7) + self.img_height - 100, pen)

            if center:
                self.current_segment_frame.boundingRect()

                self.fitInView(self.current_segment_frame, Qt.KeepAspectRatio)
        else:
            if self.current_segment_frame is not None:
                self.scene.removeItem(self.current_segment_frame)
                self.current_segment_frame = None

    def on_loaded(self, project):
        self.clear_manager()
        self.setEnabled(True)
        self.project = project
        self.update_manager()

    def on_changed(self, project, item):
        if item is not None and item.get_type() not in [SEGMENT, SEGMENTATION, SCREENSHOT, SCREENSHOT_GROUP]:
            return
        # self.project = project

        self.update_manager()
        self.on_selected(None, project.get_selected())

        # if self.follow_time:
        #     self.frame_segment(self.current_segment_index)
        # else:
        #     self.center_images()

    @QtCore.pyqtSlot(object)
    def on_classification_object_changed(self):
        self.draw_visualizations(clear = True)

    def on_closed(self):
        self.clear_manager()
        self.setEnabled(False)

    def on_selected(self, sender, selected):
        if selected is None:
            selected = []
        if not sender is self:
            sel = []
            for i in self.images_plain:
                    for s in selected:
                        if isinstance(s, Screenshot):
                            if i.screenshot_obj is s:
                                sel.append(i)
            self.select_image(sel, dispatch=False)

    def rubber_band_selection(self, QRect, Union, QPointF=None, QPoint=None):
        self.rubberband_rect = self.mapToScene(QRect).boundingRect()

    def export_screenshots(self, path, visibility=None, image_type=None, quality=None, naming=None, smooth=False):
        screenshots = []

        # If there are selected Screenshots, only export those,
        # Else export all
        if len(self.selected) == 0:
            for item in self.images_plain:
                screenshots.append(item.screenshot_obj)
            self.main_window.print_message("No Screenshots selected, exporting all Screenshots", "red")
        else:
            for item in self.selected:
                screenshots.append(item.screenshot_obj)

        try:
            if not os.path.isdir(path):
                os.mkdir(path)

            exporter = ScreenshotsExporter(self.main_window.settings, self.main_window.project, naming)
            exporter.export(screenshots, path, visibility, image_type, quality, smooth)
        except OSError as e:
            QMessageBox.warning(self.main_window, "Failed to Create Directory", "Please choose a valid path\n\n" + path)
            self.main_window.print_message("Failed to Create Directory: " + path, "Red")

    def wheelEvent(self, event):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
            self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())
            if self.main_window.is_darwin:
                h_factor = 1.1
                l_factor = 0.9
            else:
                h_factor = 1.1
                l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))
            self.curr_scale = round(self.img_width / (viewport_size.x()), 4)

            if event.angleDelta().y() > 0.0 and self.curr_scale < 10:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.01:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            if self.scaling_mode == SCALING_MODE_WIDTH:
                self.arrange_images()
                self.frame_segment(self.current_segment_index, center = False)
            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(ScreenshotsManagerWidget, self).wheelEvent(event)
            # self.verticalScrollBar().setValue(self.verticalScrollBar().value() - (500 * (float(event.angleDelta().y()) / 360)))

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.UpArrowCursor))
            self.ctrl_is_pressed = True

        elif event.key() == QtCore.Qt.Key_A and self.ctrl_is_pressed:
            self.select_image(self.images_plain)

        elif event.key() == QtCore.Qt.Key_F:
            self.center_images()

        elif event.key() == QtCore.Qt.Key_Shift:
            self.shift_is_pressed = True
        else:
            event.ignore()

    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.viewport().setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
            self.ctrl_is_pressed = False
        elif event.key() == QtCore.Qt.Key_Shift:
            self.shift_is_pressed = False
        else:
            event.ignore()

    def mouseReleaseEvent(self, QMouseEvent):
        selected = []
        if self.rubberband_rect.width() > 20 and self.rubberband_rect.height() > 20:
            for i in self.images_plain:
                i_rect = QtCore.QRectF(i.pos().x(), i.pos().y(),i.boundingRect().width(), i.boundingRect().height())
                if self.rubberband_rect.intersects(QtCore.QRectF(i_rect)):
                    selected.append(i)
            self.select_image(selected)

            self.rubberband_rect = QtCore.QRectF(0.0, 0.0, 0.0, 0.0)
            super(ScreenshotsManagerWidget, self).mouseReleaseEvent(QMouseEvent)

    def mouseDoubleClickEvent(self, *args, **kwargs):
        if len(self.selected) > 0:
            popup = ImagePreviewPopup(self, self.selected[0].pixmap())
            self.main_window.player.set_media_time(self.selected[0].screenshot_obj.movie_timestamp)
            # self.frame_image(self.selected[0])
        else:
            self.center_images()


class ScreenshotsManagerScene(QGraphicsScene):
    def __init__(self, graphicsViewer):
        super(ScreenshotsManagerScene, self).__init__()
        self.graphicsViewer = graphicsViewer


class ScreenshotManagerPixmapItems(QGraphicsPixmapItem):
    def __init__(self, qpixmap, manager, obj:Screenshot, selection_rect = QtCore.QRect(0,0,0,0)):
        super(ScreenshotManagerPixmapItems, self).__init__(qpixmap)
        self.manager = manager
        self.screenshot_obj = obj
        self.screenshot_obj.onImageSet.connect(self.set_pixmap)
        self.selection_rect = selection_rect
        self.qpixmap = qpixmap

    def boundingRect(self) -> QtCore.QRectF:
        if self.qpixmap is None:
            return QRectF()
        return QRectF(self.qpixmap.rect())

    # @pyqtSlot(object, object, object)
    def set_pixmap(self, scr, ndarray, pixmap):
        self.setPixmap(pixmap)
        self.qpixmap = pixmap

    def mousePressEvent(self, *args, **kwargs):
        self.setSelected(True)
        if self.manager.shift_is_pressed:
            selected = self.manager.selected
            if self in selected:
                selected.remove(self)
            else:
                selected.append(self)
        else:
            selected = [self]

        self.manager.select_image(selected)
        # self.manager.main_window.screenshots_editor.set_current_screenshot(self.screenshot_obj)

