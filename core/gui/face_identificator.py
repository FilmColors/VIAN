from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from PyQt5 import uic
import os
import cv2
import numpy as np
from random import shuffle

from core.gui.ewidgetbase import EDockWidget, EMultiGraphicsView, EditableListWidget, VIANMovableGraphicsItem
from core.data.computation import numpy_to_pixmap


# If Keras is not available this will throw an error.
try:
    from core.analysis.deep_learning.face_identification import FaceRecognitionModel, sub_image
    from keras.utils.np_utils import to_categorical
except:
    class FaceReconitionModel(): pass
    def to_categorical(): return []
class IdentificationWorkerSignals(QObject):
    onFacesFound = pyqtSignal(object, object, object)
    onClusteringDone = pyqtSignal()
    onRecognitionDone = pyqtSignal()
    onProgress = pyqtSignal(float)
    onTrainingDone = pyqtSignal()

class IdentificationWorker(QObject):
    def __init__(self):
        super(IdentificationWorker, self).__init__()
        self.signals = IdentificationWorkerSignals()
        self.model = FaceRecognitionModel()
        self.n_epochs = 100

    @pyqtSlot(str, dict)
    def find_faces(self, movie_path, settings):
        start = 0
        resolution = settings['resolution']

        result_features = []
        cap = cv2.VideoCapture(movie_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        images = []

        for i in range(int(cap.get(cv2.CAP_PROP_FRAME_COUNT) - start)):
            ret, frame = cap.read()
            if i % resolution == 0:
                self.signals.onProgress.emit(round(i / length, 2))
                res = self.model.get_vector(frame, preview=False)
                if res is None:
                    continue
                for r in res:
                    result_features.append([i, r])
                    images.append(sub_image(frame, r[0]))

        euclidian = np.zeros(shape=(len(result_features), 68))
        for idx, r in enumerate(result_features): euclidian[idx] = r[1][2][0]
        result = dict()
        for idx, n_cluster in enumerate(range(settings['min_clusters'], settings['max_clusters'])):
            self.signals.onProgress.emit(round(idx / np.clip(settings['max_clusters'] - settings['min_clusters'], 1, None), 2))
            if n_cluster > euclidian.shape[0]:
                break
            result[n_cluster] = self.model.cluster_faces(euclidian, n_cluster)
            print(len(result[n_cluster]), len(images))

        self.signals.onFacesFound.emit(result, images, result_features)

    def train_model(self, dataset, settings):
        self.model.init_model(dataset['n_classes'],settings['dropout'])
        self.model.weights_path = settings['path']
        self.n_epochs = settings['epochs']
        data = zip(dataset['labels'], dataset['vectors'])
        # for i in range(5):
        # shuffle(data)
        n_test = int(np.floor(len(dataset['labels']) / 3 * 2))
        n_train = len(dataset['labels']) - n_test

        tx = np.zeros(shape=(n_train, 68, 1))
        ty = np.zeros(shape=(n_train, dataset['n_classes']))
        ex = np.zeros(shape=(n_test, 68, 1))
        ey = np.zeros(shape=(n_test, dataset['n_classes']))

        for idx, (lbl, vec) in enumerate(data):
            print(idx, lbl, vec[1][2])
            c = np.array(to_categorical(lbl, dataset['n_classes']))
            if idx < n_train:
                tx[idx] = np.reshape(vec[1][2], newshape=(68, 1))
                ty[idx] = c
            else:
                ex[idx - n_train] = np.reshape(vec[1][2], newshape=(68, 1))
                ey[idx - n_train] = c
        self.model.train_model(tx, ty, ex, ey, callback=self.on_keras_callback)
        self.signals.onTrainingDone.emit()

    def on_keras_callback(self, obj):
        self.signals.onProgress.emit(obj / np.clip(self.n_epochs, 1, None))

    def cluster_faces(self):
        pass

class FaceIdentificatorDock(EDockWidget):
    def __init__(self, parent):
        super(FaceIdentificatorDock, self).__init__(parent, limit_size=False)
        self.setWindowTitle("Facial Identification")
        self.identificator = FaceIdentificatorWidget(self, self.main_window)
        self.inner.setCentralWidget(self.identificator)


class FaceIdentificatorWidget(QWidget):
    onCollectFaces = pyqtSignal(str, dict)
    onTrainModel = pyqtSignal(object, dict)

    def __init__(self, parent, main_window):
        super(FaceIdentificatorWidget, self).__init__(parent)

        self.main_window = main_window
        self.worker = IdentificationWorker()
        self.worker_thread = QThread(self)
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.start()

        self.final_dataset = None

        self.onCollectFaces.connect(self.worker.find_faces, Qt.QueuedConnection)
        self.worker.signals.onProgress.connect(self.on_progress, Qt.QueuedConnection)
        self.worker.signals.onFacesFound.connect(self.on_collect_faces_finished, Qt.QueuedConnection)
        self.onTrainModel.connect(self.worker.train_model)

        self.current_stage = 0

        self.setLayout(QVBoxLayout(self))
        self.tab_widget = QTabWidget(self)
        self.layout().addWidget(self.tab_widget)
        self.progress_bar = QProgressBar(self)
        self.layout().addWidget(self.progress_bar)

        self.collection_window = FaceIdentificationSettingsWidget(self)
        self.tab_widget.addTab(self.collection_window, "Collecting Faces")
        self.collection_window.btn_Collect.clicked.connect(self.collect_faces)

        self.train_window = QWidget(self)
        self.train_window.setLayout(QVBoxLayout())
        self.cluster_view = FaceClusteringView(self)
        self.train_window.layout().addWidget(self.cluster_view)
        self.cluster_selector = QSlider(Qt.Horizontal, self)
        self.cluster_selector.valueChanged.connect(self.cluster_view.set_current_cluster)

        self.train_window.layout().addWidget(self.cluster_selector)
        self.cluster_hbox = QHBoxLayout( self.train_window)
        self.train_window.layout().addItem(self.cluster_hbox)
        self.cluster_hbox.addSpacerItem(QSpacerItem(1,1, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.btn_create_dataset = QPushButton("Create Dataset",  self.train_window)
        self.cluster_hbox.addWidget(self.btn_create_dataset)

        self.btn_create_dataset.clicked.connect(self.on_create_dataset)

        self.tab_widget.addTab(self.train_window, "Training Data")

        self.fine_adjusting_window = TrainWidget(self)
        self.tab_widget.addTab(self.fine_adjusting_window, "Fine Adjusting")
        self.fine_adjusting_window.settings.btn_Train.clicked.connect(self.on_start_training)

        self.tab_widget.setTabEnabled(1, False)
        self.tab_widget.setTabEnabled(2, False)


    def collect_faces(self):
        settings = self.collection_window.get_settings()
        self.onCollectFaces.emit(self.main_window.project.movie_descriptor.movie_path, settings)

    @pyqtSlot(object, object, object)
    def on_collect_faces_finished(self, result, images, result_features):
        self.set_stage(1)
        self.progress_bar.setValue(0)
        self.cluster_selector.setRange(np.amin(list(result.keys())), np.amax(list(result.keys())))
        self.cluster_view.add_clustering(result, images, result_features)
        # self.cluster_selector.shot()

    def on_create_dataset(self):
        self.set_stage(2)
        self.final_dataset = self.cluster_view.get_final_dataset()

    def set_stage(self, v):
        self.current_stage = v
        self.tab_widget.setTabEnabled(v, True)
        self.tab_widget.setCurrentIndex(v)
        # if v >= 1:
        #     self.ta

    def on_finetune(self):
        self.cluster_selector.hide()

    def on_start_training(self):
        if self.final_dataset is not None:
            s = self.fine_adjusting_window.settings.get_settings()
            s['path'] = self.main_window.project.data_dir + s['path']
            self.onTrainModel.emit(self.final_dataset, s)


    @pyqtSlot(float)
    def on_progress(self, f):
        self.progress_bar.setValue(f * 100)


class FaceIdentificationSettingsWidget(QWidget):
    def __init__(self, parent):
        super(FaceIdentificationSettingsWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/FaceIdentificationSettings.ui")
        uic.loadUi(path, self)

    def get_settings(self):
        return dict(
            resolution=self.spinBox_Resolution.value(),
            min_clusters = self.spinBox_MinClusters.value(),
            max_clusters = self.spinBox_MaxClusters.value()
        )


class FaceClusteringView(QGraphicsView):
    def __init__(self, parent):
        super(FaceClusteringView, self).__init__(parent)
        self.cluster_idx = 0
        self.setScene(QGraphicsScene(self))
        self.images = None
        self.clusters = None
        self.result_features = None
        self.labels = None
        self.list_offset = 0
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.rubberBandChanged.connect(self.on_rubberband_selection)
        self.curr_scale = 1.0
        self.ctrl_is_pressed = True
        self.curr_cluster_idx = 0
        self.item_height = 100
        self.item_margin = 20

        self.selected = []
        self.items = []

        self.fiex_clustering = []

    def add_clustering(self, clustering, images, result_features):
        """
        
        :param clustering: a dict of list each containing the labels of the image indices dict(k=n_clusters, val= [labels])
        :param images: 
        :return: 
        """
        clusters = []
        labels = []

        for k in sorted(clustering.keys()):
            c = dict()
            for idx, sample_idx in enumerate(clustering[k]):
                if sample_idx not in c:
                    c[sample_idx] = []
                c[sample_idx].append(idx)
            clusters.append(c)

        self.list_offset = np.amin(list(clustering.keys()))
        # Clusters: a list of dict [dict(k=label, val= [image_indices])]

        self.images = images
        self.result_features = result_features
        self.clusters = clusters
        self.set_current_cluster(self.list_offset)

    def on_fineadjust(self):
        return self.clusters[self.curr_cluster_idx]

    def set_current_cluster(self, idx = None):
        if self.clusters is None:
            return

        self.scene().clear()
        self.items = []
        if idx is not None:
            idx -= self.list_offset
            self.curr_cluster_idx = idx
        else:
            idx = self.curr_cluster_idx

        y = 0
        for lbl in self.clusters[idx]:
            h_max = 0
            x = 0
            for img_idx in self.clusters[idx][lbl]:
                img = self.images[img_idx]
                fx =  self.item_height / img.shape[1]
                img = cv2.resize(img, None, fx = fx, fy = fx, interpolation=cv2.INTER_CUBIC)
                itm = VIANMovableGraphicsItem(numpy_to_pixmap(img), mime_data=dict(data_idx=img_idx))
                itm.signals.hasBeenMoved.connect(self.update_arrangement)
                self.scene().addItem(itm)
                itm.setFlag(QGraphicsItem.ItemIsMovable, True)
                if img.shape[0] > h_max:
                    h_max = img.shape[0]
                itm.setPos(x, y + self.item_margin)

                x += img.shape[1] + self.item_margin
                self.items.append(itm)
            self.scene().addLine(0, y, x + 100, y)
            y += h_max + (2 * self.item_margin)

        self.scene().addLine(0, y, x + 100, y)
        text = self.scene().addText("Drag Image here to add new Character...", QFont("Helvetica", pointSize=30))
        text.setPos(20, y + self.item_margin)

    def get_final_dataset(self):
        vectors = []
        labels = []
        for lbl in self.clusters[self.curr_cluster_idx]:
            for img_idx in self.clusters[self.curr_cluster_idx][lbl]:
                labels.append(lbl)
                vectors.append(self.result_features[img_idx])
        return dict(vectors=vectors, labels=labels, n_classes=len(self.clusters[self.curr_cluster_idx].keys()))

    @pyqtSlot(object)
    def update_arrangement(self, args):
        new_clustering = dict()
        for itm in self.items:
            cluster = int(np.floor(itm.pos().y() / (self.item_height + (2 * self.item_margin))))
            if cluster not in new_clustering:
                new_clustering[cluster] = []
            new_clustering[cluster].append(itm.mime_data['data_idx'])
        self.clusters[self.curr_cluster_idx] = new_clustering
        self.set_current_cluster()


    def on_rubberband_selection(self, QRect, Union, QPointF=None, QPoint=None):
        p = QPainterPath()
        p.addRect(QRectF(self.mapToScene(QRect).boundingRect()))
        self.scene().setSelectionArea(p, self.viewportTransform())

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            pass
        else:
            super(FaceClusteringView, self).mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.viewport().setCursor(QCursor(Qt.UpArrowCursor))
            self.ctrl_is_pressed = True
            event.ignore()

        elif event.key() == Qt.Key_F:
            self.setSceneRect(QRectF())
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
            self.curr_scale = 1.0
        else:
            event.ignore()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if len(self.pixmaps) > 0 and self.auto_frame:
            rect = self.scene().itemsBoundingRect()
            self.fitInView(rect, Qt.KeepAspectRatio)
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.viewport().setCursor(QCursor(Qt.ArrowCursor))
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100000:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.00001:
                self.scale(l_factor, l_factor)
                self.curr_scale *= l_factor

            cursor_pos = self.mapToScene(event.pos()) - old_pos
            # self.onScaleEvent.emit(self.curr_scale)

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(FaceClusteringView, self).wheelEvent(event)


class FaceIdentificationDeepLearningSettingsWidget(QWidget):
    def __init__(self, parent):
        super(FaceIdentificationDeepLearningSettingsWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/FaceIdentificationDeepLearningSettings.ui")
        uic.loadUi(path, self)

        self.lineEdit_Name.setText("facerec_weights")

    def get_settings(self):
        return dict(
            epochs=self.spinBox_Epochs.value(),
            batch_size=self.spinBox_BatchSize.value(),
            dropout=self.doubleSpinBox_DropOut.value(),
            path = self.lineEdit_Name.text() + ".hdf5"
        )


class TrainWidget(QWidget):
    def __init__(self, parent):
        super(TrainWidget, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.settings = FaceIdentificationDeepLearningSettingsWidget(self)
        self.layout().addWidget(self.settings)

#
# class FineAdjustingWindow(QWidget):
#     def __init__(self, parent):
#         super(FineAdjustingWindow, self).__init__(parent)
#         self.labels = []
#         self.features = []
#         self.images = []
#         self.indices = dict()
#         self.setLayout(QHBoxLayout(self))
#         self.splitter = QSplitter(Qt.Horizontal, self)
#         self.layout().addWidget(self.splitter)
#
#         self.side_widget = QWidget()
#         self.list_side = QVBoxLayout()
#         self.side_widget.setLayout(self.list_side)
#         self.list = EditableListWidget(self)
#
#         self.splitter.addWidget(self.list)
#         self.view = EMultiGraphicsView(self)
#         self.splitter.addWidget(self.view)
#
#     def set_clustering(self, clustering, features, images):
#         for k in clustering.keys():
#             self.labels.append(k)
#             self.list.add_item(k, k)
#         self.indices = clustering
#         self.features = features
#         self.images = images






