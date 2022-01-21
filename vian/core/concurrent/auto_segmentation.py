from sklearn.cluster import AgglomerativeClustering
import numpy as np

from vian.core.gui.ewidgetbase import *
from PyQt6.QtCore import QRect, Qt
from vian.core.data.interfaces import IConcurrentJob
from vian.core.data.enums import *
from vian.core.container.project import VIANProject
from vian.core.analysis.misc import preprocess_frame
from vian.core.data.computation import frame2ms, floatify_img, ms_to_frames

from vian.core.gui.misc.utils import dialog_with_margin

AUTO_SEGM_EVEN = 0
AUTO_SEGM_CHIST = 1


def cluster_histograms_adjacently(x, n_clusters = 2):
    connectivity = np.zeros(shape=(x.shape[0], x.shape[0]), dtype=np.uint8)
    for i in range(1, x.shape[0] - 1, 1):
        connectivity[i][i - 1] = 1
        connectivity[i][i] = 1
        connectivity[i][i + 1] = 1

    model = AgglomerativeClustering(linkage="ward",
                                    connectivity=connectivity,
                                    n_clusters=n_clusters, compute_full_tree=True)
    model.fit(x)
    return model.labels_


def auto_segmentation(project:VIANProject, mode, main_window, n_segment = -1, segm_width = 10000, nth_frame = 4, n_cluster_lb =1, n_cluster_hb = 100, resolution=30):
    duration = project.movie_descriptor.duration
    if mode == AUTO_SEGM_EVEN:
        if n_segment < 0:
            n_segment = int(duration / segm_width)
        else:
            segm_width = int(duration / n_segment)

        segmentation = project.create_segmentation("Auto Segmentation", False)
        for i in range(n_segment):
            segmentation.create_segment2(i * segm_width,
                                         i * segm_width + segm_width,
                                         mode=SegmentCreationMode.INTERVAL,
                                         inhibit_overlap=False,
                                         dispatch=False)

        project.dispatch_changed()

    elif mode == AUTO_SEGM_CHIST:
        ready, colormetry = project.get_colormetry()

        if ready:
            histograms = colormetry.get_histogram()
            frame_pos = colormetry.get_frame_pos()
            resolution = colormetry.resolution
        else:
            histograms = None
            frame_pos  = None
            resolution = resolution

        job = AutoSegmentingJobHistogram(
            [project.movie_descriptor.get_movie_path(),
             resolution,
             project.movie_descriptor.fps,
             histograms,
             frame_pos,
             nth_frame,
             [n_cluster_lb, n_cluster_hb]
             ,resolution],
            max_width=main_window.settings.PROCESSING_WIDTH)
        main_window.run_job_concurrent(job)


class DialogAutoSegmentation(EDialogWidget):
    def __init__(self, parent, project):
        super(DialogAutoSegmentation, self).__init__(parent, parent, "https://www.vian.app/static/manual/step_by_step/segmentation/auto_segmentation.html")
        path = os.path.abspath("qt_ui/DialogAutoSegmentation.ui")
        uic.loadUi(path, self)

        self.project = project
        self.comboBox_Mode.currentIndexChanged.connect(self.on_mode_changed)

        self.not_finished_text = "The Colormetry has not finished yet,\n" \
                                 "please wait until it is finished and try again.\n\n" \
                                 "The progress is indicated by the green line on the Timeline."
        self.not_run_text = "The Colormetry has not been started yet.\n" \
                            "please run the Colormetry First,\n " \
                            "since the results will be used for the Auto Segmentation"

        self.lbl_not_ready = QLabel("The Colormetry has not finished yet,\n"
                                    "please wait until it is finished and try again.\n\n"
                                    "The progress is inAtrousConvolution2Ddicated by the green line on the Timeline.")
        self.lbl_not_ready.setStyleSheet("QLabel{foreground: red;}")

        self.btn_Run.clicked.connect(self.on_ok)
        self.btn_Help.clicked.connect(self.on_help)
        self.btn_Cancel.clicked.connect(self.close)

        dialog_with_margin(parent, self, "sm")

    def on_mode_changed(self, idx):
        self.stackedWidget.setCurrentIndex(idx)
        return

    @pyqtSlot()
    def on_ok(self):
        if self.comboBox_Distribution.currentIndex() == 1:
            n_segments = self.spinBox_NSegments.value()
            segment_width = -1
            mode = 0
        else:
            n_segments = -1
            segment_width = self.spinBox_SegmentLength.value()
            mode = 1
        auto_segmentation(self.project, mode, self.main_window,
                          n_segments,
                          segment_width,
                          n_cluster_lb=self.spinBox_lowBound.value(),
                          n_cluster_hb=np.clip(self.spinBox_highBound.value(), self.spinBox_lowBound.value(), None))
        self.close()


class AutoSegmentingJobHistogram(IConcurrentJob):
    def __init__(self, args, show_modify_progress= False, max_width=1920):
        super(AutoSegmentingJobHistogram, self).__init__(args, show_modify_progress)
        self.max_width = max_width

    def run_concurrent(self, args, sign_progress):
        idx = 0
        movie_path = args[0]
        resolution = args[1]
        in_hists = args[3]
        fps = args[2]
        indices = args[4]
        frame_resolution = args[5]
        n_cluster_range = args[6]
        alt_resolution = args[7]
        cluster_sizes = range(n_cluster_range[0], n_cluster_range[1] + 1, 1)
        histograms = []
        frames = []

        cap = cv2.VideoCapture(movie_path)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        step = length / (10 * n_cluster_range[1])
        resize_f = 192.0 / cap.get(cv2.CAP_PROP_FRAME_WIDTH)

        counter = 0
        tot = len(list(range(0, int(length), int(step))))
        for i in range(0, int(length), int(step)):
            sign_progress(counter / tot)
            counter += 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if frame is not None:
                frames.append(dict(
                    pixmap=numpy_to_pixmap(cv2.resize(frame, None, None, resize_f, resize_f, cv2.INTER_CUBIC)),
                    pos=i)
                )

        data_idx = 0
        read_img = -1 # We only want to read every second image
        if indices is None:
            indices = []
            resolution = alt_resolution
        for i in range(int(length)):
            if self.aborted:
                return None
            if i % resolution == 0:
                read_img += 1
                if in_hists is not None and data_idx >= len(in_hists):
                    break

                sign_progress(i / length)
                if in_hists is not None:
                    histograms.append(np.resize(in_hists[data_idx], new_shape=16 ** 3))
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                    ret, frame = cap.read()
                    if frame is None:
                        break

                    frame = preprocess_frame(frame, self.max_width)
                    frame = cv2.cvtColor(floatify_img(frame), cv2.COLOR_BGR2LAB)
                    data = np.resize(frame, (frame.shape[0] * frame.shape[1], 3))
                    hist = cv2.calcHist([data[:, 0], data[:, 1], data[:, 2]], [0, 1, 2], None,
                                        [16, 16, 16],
                                        [0, 100, -128, 128,
                                         -128, 128])
                    indices.append(i)
                    histograms.append(np.resize(hist, new_shape=16 ** 3))
                data_idx += 1

        connectivity = np.zeros(shape=(len(histograms), len(histograms)), dtype=np.uint8)
        for i in range(1, len(histograms) - 1, 1):
            connectivity[i][i - 1] = 1
            connectivity[i][i] = 1
            connectivity[i][i + 1] = 1

        clusterings = []
        for i, n_cluster in enumerate(cluster_sizes):
            sign_progress(i / len(cluster_sizes))

            if len(histograms) > n_cluster:
                model = AgglomerativeClustering(linkage="ward",
                                                connectivity=connectivity,
                                                n_clusters=n_cluster, compute_full_tree=True)
                model.fit(histograms)
                clusterings.append(model.labels_)

        frames_total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        pcounter, p_max = 0, len(np.unique(clusterings[0])) * 30

        cap.release()
        return dict(clusterings=clusterings, frames=frames, indices=indices, fps=fps, frame_resolution=frame_resolution, cluster_range=n_cluster_range)

    def modify_project(self, project, result, sign_progress=None, main_window = None):
        if result is not None:
            widget = self.get_widget(main_window, result)
            widget.show()

    def get_widget(self, parent, result):
        return ApplySegmentationWindow(parent, **result)


class AutoSegmentingJobAudio(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        idx = 0
        movie_path = args[0]
        resolution = args[1]
        in_hists = args[3]
        fps = args[2]
        indices = args[4]
        frame_resolution = args[5]
        n_cluster_range = args[6]
        alt_resolution = args[7]
        cluster_sizes = range(n_cluster_range[0], n_cluster_range[1], 1)
        histograms = []
        frames = []

        cap = cv2.VideoCapture(movie_path)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = cap.get(cv2.CAP_PROP_FPS)
        step = length / (10 * n_cluster_range[1])
        resize_f = 192.0 / cap.get(cv2.CAP_PROP_FRAME_WIDTH)

        counter = 0
        tot = len(list(range(0, int(length), int(step))))
        for i in range(0, int(length), int(step)):
            sign_progress(counter / tot)
            counter += 1
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            frames.append(dict(
                pixmap=numpy_to_pixmap(cv2.resize(frame, None, None, resize_f, resize_f, cv2.INTER_CUBIC)),
                pos=i)
            )

        data_idx = 0
        read_img = -1 # We only want to read every second image
        if indices is None:
            indices = []
            resolution = alt_resolution
        for i in range(int(length)):
            if self.aborted:
                return None
            if i % resolution == 0:
                read_img += 1
                if in_hists is not None and data_idx >= len(in_hists):
                    break

                sign_progress(i / length)
                if in_hists is not None:
                    histograms.append(np.resize(in_hists[data_idx], new_shape=16 ** 3))
                else:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                    ret, frame = cap.read()
                    if frame is None:
                        break

                    frame = cv2.cvtColor(floatify_img(frame), cv2.COLOR_BGR2LAB)
                    data = np.resize(frame, (frame.shape[0] * frame.shape[1], 3))
                    hist = cv2.calcHist([data[:, 0], data[:, 1], data[:, 2]], [0, 1, 2], None,
                                        [16, 16, 16],
                                        [0, 100, -128, 128,
                                         -128, 128])
                    indices.append(i)
                    histograms.append(np.resize(hist, new_shape=16 ** 3))
                data_idx += 1

        connectivity = np.zeros(shape=(len(histograms), len(histograms)), dtype=np.uint8)
        for i in range(1, len(histograms) - 1, 1):
            connectivity[i][i - 1] = 1
            connectivity[i][i] = 1
            connectivity[i][i + 1] = 1

        clusterings = []
        for i, n_cluster in enumerate(cluster_sizes):
            sign_progress(i / len(cluster_sizes))

            if len(histograms) > n_cluster:
                model = AgglomerativeClustering(linkage="ward",
                                                connectivity=connectivity,
                                                n_clusters=n_cluster, compute_full_tree=True)
                model.fit(histograms)
                clusterings.append(model.labels_)

        frames_total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        pcounter, p_max = 0, len(np.unique(clusterings[0])) * 30

        cap.release()
        return dict(clusterings=clusterings, frames=frames, indices=indices, fps=fps, frame_resolution=frame_resolution, cluster_range=n_cluster_range)

    def modify_project(self, project, result, sign_progress=None, main_window = None):
        if result is not None:
            widget = self.get_widget(main_window, result)
            widget.show()

    def get_widget(self, parent, result):
        return ApplySegmentationWindow(parent, **result)


class ApplySegmentationWindow(QMainWindow):
    def __init__(self, parent, clusterings, frames, indices, fps, frame_resolution, cluster_range):
        super(ApplySegmentationWindow, self).__init__(parent)
        self.setWindowTitle("Apply Segmentation")
        self.setWindowFlags(Qt.Tool)
        self.project = parent.project
        self.clusterings = clusterings
        self.frames = frames
        self.indices = indices
        self.fps = fps
        self.frame_resolution = frame_resolution
        self.cluster_range = cluster_range
        self.w = QWidget(self)
        self.setCentralWidget(self.w)
        self.w.setLayout(QVBoxLayout(self.w))
        self.view = EGraphicsView(self.w)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(cluster_range[0], np.clip(cluster_range[1] + 1, None, len(self.clusterings) + cluster_range[0]) - 1)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.w_slider = QWidget(self)
        self.hbox = QHBoxLayout(self.w)
        self.w_slider.setLayout(self.hbox)

        self.segments = []

        self.hbox.addWidget(QLabel("n-Clusters:"))
        self.hbox.addWidget(self.slider)
        self.lbl_n_cluster = QLabel("1")

        self.hbox.addWidget(self.lbl_n_cluster)
        self.btn_ok = QPushButton("Apply Segmentation")
        self.btn_ok.clicked.connect(self.apply_segmentation)
        self.btn_cancel = QPushButton("Cancel")

        self.w_buttons = QWidget(self)
        self.w_buttons.setLayout(QHBoxLayout(self.w_buttons))
        self.w_buttons.layout().addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed))
        self.w_buttons.layout().addWidget(self.btn_ok)
        self.w_buttons.layout().addWidget(self.btn_cancel)
        self.btn_cancel.clicked.connect(self.close)

        self.w.layout().addWidget(self.view)
        self.w.layout().addWidget(self.w_slider)
        self.w.layout().addWidget(self.w_buttons)

        dialog_with_margin(parent, self)
        self.show()
        self.on_slider_changed()


    def on_slider_changed(self):
        self.lbl_n_cluster.setText(str(self.slider.value()))
        index = int(self.slider.value()) - self.cluster_range[0]

        segments = []
        curr_lbl = -1
        indices = []
        for idx, lbl in enumerate(self.clusterings[index]):
            if curr_lbl != lbl:
                if len(indices) > 0:
                    start_index = self.indices[indices[0]]
                    if len(indices) > 1:
                        end_index = self.indices[indices[len(indices) - 1]]
                    else:
                        end_index = self.indices[indices[np.clip(start_index + 1, 0, len(indices) - 1)]]

                    segments.append(dict(start=start_index,
                                         end = end_index,
                                         indices=indices))
                    indices = []
                    curr_lbl = lbl
            indices.append(idx)

        for idx, s in enumerate(segments):
            if idx == 0:
                s['start'] = 0
            if idx != len(segments) - 1:
                s['end'] = segments[idx + 1]['start']
            s['images'] = []
            for img in self.frames:
                if s['start'] <= img['pos'] < s['end']:
                    s['images'].append(img)

        self.view.scene().clear()
        x, y, = 0, 0
        img_h, img_w = 200, 200

        for i, segm in enumerate(segments):
            for img in segm['images']:
                itm = self.view.scene().addPixmap(img['pixmap'])
                itm.setPos(x, y)
                x += img_w
            x = 0
            y += img_h

        self.segments = segments
        rect = QRectF(self.view.scene().itemsBoundingRect().x(), self.view.scene().itemsBoundingRect().y(), 100, self.view.scene().itemsBoundingRect().height())
        self.view.fitInView(self.view.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def apply_segmentation(self):
        segmentation = self.project.create_segmentation("Auto Segmentation", dispatch=False)
        for i, s in enumerate(self.segments):
            if i < len(self.segments) - 1:
                s['end'] = self.segments[i + 1]['start'] - 1
            elif i == len(self.segments) - 1:
                print("Final Duration")
                s['end'] = ms_to_frames(self.project.movie_descriptor.duration, self.fps)

            segmentation.create_segment2(frame2ms(s['start'], self.fps),
                                         frame2ms(s['end'], self.fps),
                                         mode=SegmentCreationMode.INTERVAL,
                                         inhibit_overlap=False,
                                         dispatch=False)
            self.close()

        QMessageBox.information(self, "Segmentation Created", "Segmentation has been created!")
        self.project.dispatch_changed()
