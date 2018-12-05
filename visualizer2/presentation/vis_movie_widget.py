from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os
from random import sample

from core.visualization.image_plots import ImagePlotTime, ImagePlotCircular, ImagePlotPlane
from visualizer.presentation.presentation_widget import *
from core.visualization.graph_plots import VocabularyGraph
from core.visualization.feature_plot import *
from core.corpus.shared.sqlalchemy_entities import *
from visualizer.widgets.segment_visualization import *

class VisMovieLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisMovieLayout, self).__init__(parent, visualizer)#, "qt_ui/visualizer/VisMovieLayout.ui")

        self.setLayout(QVBoxLayout())
        self.vsplit = QSplitter(Qt.Vertical, self)
        self.layout().addWidget(self.vsplit)
        self.upper_widget = QSplitter(self)
        self.lower_widget = QSplitter(self)
        self.lower_right = QSplitter(Qt.Vertical, self.lower_widget)
        self.lower_left = QSplitter(Qt.Vertical, self.lower_widget)
        self.lower_widget.addWidget(self.lower_left)
        self.lower_widget.addWidget(self.lower_right)

        self.vsplit.addWidget(self.upper_widget)
        self.vsplit.addWidget(self.lower_widget)

        self.plot_color_dt = ImagePlotTime(self)
        self.plot_network = VocabularyGraph(self)
        self.plot_features = GenericFeaturePlot(self)
        self.plot_segments = SegmentVisualization(self, self.visualizer)
        self.plot_la_space = ImagePlotPlane(self)
        self.plot_ab_space = ImagePlotCircular(self)
        self.vis_plot_la_space = VisualizerVisualization(self, self.visualizer, self.plot_la_space,
                                                         self.plot_la_space.get_param_widget())
        self.vis_plot_ab_space = VisualizerVisualization(self, self.visualizer, self.plot_ab_space,
                                                         self.plot_ab_space.get_param_widget())
        self.lower_widget.addWidget(self.vis_plot_la_space)
        self.lower_widget.addWidget(self.vis_plot_ab_space)

        self.vis_plot_color_dt = VisualizerVisualization(None, self.visualizer, self.plot_color_dt, self.plot_color_dt.get_param_widget())
        self.vis_plot_network = VisualizerVisualization(None, self.visualizer, self.plot_network, self.plot_network.get_param_widget())
        self.vis_plot_features = VisualizerVisualization(None, self.visualizer, self.plot_features, self.plot_features.get_param_widget())

        self.classification_object_filter_cbs = [QComboBox(), QComboBox()]
        self.classification_object_filter_indices = dict()
        self.plot_color_dt.set_heads_up_widget(self.classification_object_filter_cbs[0])
        self.classification_object_filter_cbs[0].currentTextChanged.connect(self.on_classification_object_changed)

        self.upper_widget.addWidget(self.vis_plot_color_dt)
        self.upper_widget.addWidget(self.plot_segments)
        self.lower_right.addWidget(self.vis_plot_network)
        self.lower_left.addWidget(self.vis_plot_features)

        self.plot_color_dt.onImageClicked.connect(self.on_images_clicked)
        self.plot_la_space.onImageClicked.connect(self.on_images_clicked)
        self.plot_ab_space.onImageClicked.connect(self.on_images_clicked)
        self.plot_segments.onSegmentSelected.connect(self.on_segments_selected)
        self.plot_segments.onSegmentHovered.connect(self.on_segments_selected)
        self.plot_segments.onSegmentLeave.connect(self.on_reset_hover)

        self.screenshots = dict() # TUPLE (DBScreenshot, Image, Used)
        self.color_features = dict()
        self.current_cl_obj = "Global"
        self.shot_counter = 0
        self.already_processed = []

    def set_project(self, dbproject:DBProject):
        counter = 0
        for scr in dbproject.screenshots: #type:DBScreenshot
            for a in scr.analyses: #type:DBScreenshotAnalysis
                if a.analysis_class_name == "ColorFeatures":
                    if scr.id not in self.color_features:
                        self.color_features[scr.id] = dict()
                    self.color_features[scr.id][a.classification_object.id] = a
            self.screenshots[scr.id] = scr
        self.on_classification_object_changed(self.current_cl_obj)

    @pyqtSlot(object)
    def on_screenshot_loaded(self, scr):
        try:
            self.screenshots[scr['screenshot_id']][1] = scr['image']
            if scr['screenshot_id'] in self.color_features and scr['screenshot_id'] in self.screenshots:
                l = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][0]
                tx = self.screenshots[scr['screenshot_id']][0].time_ms
                ty = self.color_features[scr['screenshot_id']].analysis_data['saturation_p']
                x = -self.color_features[scr['screenshot_id']].analysis_data['color_lab'][1] + 128
                y = self.color_features[scr['screenshot_id']].analysis_data['color_lab'][2] - 128
                if self.screenshots[scr['screenshot_id']][2] == True:
                    self.plot_color_dt.add_image(tx, ty, self.screenshots[scr['screenshot_id']][1], False, mime_data=self.screenshots[scr['screenshot_id']][0])
                    self.plot_segments.add_item_to_segment(scr['screenshot_id'], self.screenshots[scr['screenshot_id']][1])
                    self.plot_ab_space.add_image(x, y, self.screenshots[scr['screenshot_id']][1], False, mime_data=self.screenshots[scr['screenshot_id']][0], z = l)
                    self.plot_la_space.add_image(x, l, self.screenshots[scr['screenshot_id']][1], False, mime_data=self.screenshots[scr['screenshot_id']][0], z = y)
                    self.plot_features.add_image(tx, 0, self.screenshots[scr['screenshot_id']][1], False, mime_data=self.screenshots[scr['screenshot_id']][0])

                if self.shot_counter == 10:
                    self.plot_color_dt.frame_default()
                    self.plot_ab_space.frame_default()
                    self.plot_la_space.frame_default()
                    self.shot_counter = 0
                self.shot_counter += 1
        except Exception as e:
            print(e)

    def on_classification_object_changed(self, name):
        self.plot_color_dt.clear_view()
        self.plot_la_space.clear_view()
        self.plot_ab_space.clear_view()
        self.plot_ab_space.add_grid()
        self.plot_la_space.add_grid()

        for k in self.screenshots:
            scr = self.screenshots[k]
            analysis = self.color_features[scr.id][1] #type:DBScreenshotAnalysis
            data = self.visualizer.query_worker.corpus.hdf5_manager.features()[analysis.hdf5_index]
            print(self.visualizer.query_worker.root + "/shots/" + scr.file_path)
            img = cv2.imread(self.visualizer.query_worker.root + scr.file_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
            # x = self.screenshots[k][0].time_ms
            # y = self.color_features[k].analysis_data['saturation_p']
            l = data[3]
            tx = scr.time_ms
            ty = data[7]
            x = data[4]
            y = data[5]

            self.plot_color_dt.add_image(tx, ty, img, False, mime_data=scr)
            self.plot_ab_space.add_image(x, y, img, False, mime_data=scr, z=l)
            self.plot_la_space.add_image(x, l, img, False, mime_data=scr, z=y)

        self.plot_color_dt.frame_default()
        self.plot_ab_space.frame_default()
        self.plot_la_space.frame_default()

    def clear(self):
        self.plot_color_dt.clear_view()
        self.plot_features.clear_view()
        self.plot_segments.clear_view()
        self.plot_la_space.clear_view()
        self.plot_ab_space.clear_view()
        self.plot_ab_space.add_grid()
        self.plot_la_space.add_grid()

    def compute_node_matrix(self, key_mapping, keywords):
        labels = []

        # Generate a list of labes from the received keyword result of the Query
        for k in keywords.keys():
            k = keywords[k]
            labels.append(k['word'].name + ":" + k['voc'].name + ":" + k['cl_obj'].name)

        # Iterate over all Segments, and create a segment wise correlation matrix
        segment_sorted = dict()
        for k in key_mapping:
            if k.target_id not in segment_sorted:
                segment_sorted[k.target_id] = []
            segment_sorted[k.target_id].append(k)

        node_matrix = np.zeros(shape=(len(keywords), len(keywords)), dtype=np.float32)
        for k in segment_sorted.keys():
            k = segment_sorted[k]
            all_keyws_in_segment = [kwd.keyword_id for kwd in k]
            for x in all_keyws_in_segment:
                for y in all_keyws_in_segment:
                    node_matrix[x][y] += 1

        self.plot_network.create_graph(node_matrix, labels)

    @pyqtSlot(object, object)
    def on_segments_selected(self, obj:DBSegment, scrs:List[DBScreenshot]):
        indices = []
        for idx, img in enumerate(self.plot_color_dt.images):
            if img.mime_data in scrs:
                indices.append(idx)
        self.plot_color_dt.set_highlighted(indices)
        self.plot_ab_space.set_highlighted(indices)
        self.plot_la_space.set_highlighted(indices)


    @pyqtSlot(object)
    def on_images_clicked(self, mime_data):
        self.visualizer.on_screenshot_inspector(mime_data)

    @pyqtSlot(object, object)
    def on_reset_hover(self, a, b):
        self.vis_plot_ab_space.on_reset()
        self.vis_plot_color_dt.on_reset()
        self.vis_plot_la_space.on_reset()


