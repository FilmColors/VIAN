from sklearn.cluster.hierarchical import AgglomerativeClustering
import numpy as np

from core.gui.ewidgetbase import *
from PyQt5.QtCore import QRect, Qt
from core.data.interfaces import IConcurrentJob
from core.data.enums import *
from core.container.project import VIANProject

from core.data.computation import frame2ms

AUTO_SEGM_EVEN = 0
AUTO_SEGM_CHIST = 1


def auto_segmentation(project:VIANProject, mode, main_window, n_segment = -1, segm_width = 10000, nth_frame = 4, n_cluster_lb =1, n_cluster_hb = 100):
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

            # segmentation.create_segment(i * segm_width, i * segm_width + segm_width, dispatch=False)
        project.dispatch_changed()

    elif mode == AUTO_SEGM_CHIST:
        ready, colormetry = project.get_colormetry()

        job = AutoSegmentingJob(
            [project.movie_descriptor.get_movie_path(),
             30,
             project.movie_descriptor.fps,
             colormetry.get_histogram(),
             colormetry.get_frame_pos(),
             nth_frame,
             [n_cluster_lb, n_cluster_hb]
             ])
        main_window.run_job_concurrent(job)


class DialogAutoSegmentation(EDialogWidget):
    def __init__(self, parent, project):
        super(DialogAutoSegmentation, self).__init__(parent, parent, "_docs/build/html/step_by_step/segmentation/auto_segmentation.html")
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
                                    "The progress is indicated by the green line on the Timeline.")
        self.lbl_not_ready.setStyleSheet("QLabel{foreground: red;}")
        self.btn_start_colormetry = QPushButton("Start Colorimetry")
        self.btn_start_colormetry.clicked.connect(self.main_window.toggle_colormetry)

        self.widget_colorhist.layout().addWidget(self.lbl_not_ready)
        self.widget_colorhist.layout().addWidget(self.btn_start_colormetry)
        self.btn_Run.clicked.connect(self.on_ok)
        self.btn_Help.clicked.connect(self.on_help)
        self.btn_Cancel.clicked.connect(self.close)

    def on_mode_changed(self, idx):
        self.stackedWidget.setCurrentIndex(idx)
        ret, c =  self.project.get_colormetry()
        if ret is False and idx == 1:
            self.lbl_not_ready.show()
            if c is None:
                self.lbl_not_ready.setText(self.not_run_text)
                self.btn_start_colormetry.show()
            else:
                self.lbl_not_ready.setText(self.not_finished_text)
                self.btn_start_colormetry.hide()
            self.btn_Run.setEnabled(False)
        else:
            self.lbl_not_ready.hide()
            self.btn_Run.setEnabled(True)

    def on_ok(self):
        if self.comboBox_Distribution.currentIndex() == 0:
            n_segments = self.spinBox_NSegments.value()
            segment_width = -1
        else:
            n_segments = -1
            segment_width = self.spinBox_SegmentLength.value()
        auto_segmentation(self.project, self.comboBox_Mode.currentIndex(), self.main_window,
                          n_segments,
                          segment_width,
                          self.spinBox_nthFrame.value(),
                          self.spinBox_lowBound.value(),
                          np.clip(self.spinBox_highBound.value(), self.spinBox_lowBound.value(), None))
        self.close()


class AutoSegmentingJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        idx = 0
        movie_path = args[0]
        resolution = args[1]
        in_hists = args[3]
        fps = args[2]
        indices = args[4]
        frame_resolution = args[5]
        n_cluster_range = args[6]

        cluster_sizes = range(n_cluster_range[0], n_cluster_range[1], 1)
        histograms = []
        frames = []

        cap = cv2.VideoCapture(movie_path)
        length = cap.get(cv2.CAP_PROP_FRAME_COUNT)

        resize_f = 192.0 / cap.get(cv2.CAP_PROP_FRAME_WIDTH)

        data_idx = 0
        read_img  = -1 # We only want to read every second image
        for i in range(int(length)):
            if self.aborted:
                return None
            if i % resolution == 0:
                read_img += 1
                if data_idx >= len(in_hists):
                    break
                if read_img % frame_resolution == 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                    ret, frame = cap.read()
                    frames.append(cv2.resize(frame, None, None, resize_f, resize_f, cv2.INTER_CUBIC))
                    read_img = 0

                sign_progress(i / length)
                histograms.append(np.resize(in_hists[data_idx], new_shape=16 ** 3))
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

        return [clusterings, frames, indices, fps, frame_resolution, n_cluster_range]

    def modify_project(self, project, result, sign_progress=None, main_window = None):
        if result is not None:
            widget = self.get_widget(main_window, result)
            widget.show()

    def get_widget(self, parent, result):
        return ApplySegmentationWindow(parent, result[0], result[1], result[2], result[3], result[4], result[5])


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
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(cluster_range[0], np.clip(cluster_range[1] - 1, None, len(self.clusterings) + cluster_range[0]) - 1)
        self.slider.valueChanged.connect(self.on_slider_changed)

        self.w_slider = QWidget(self)
        self.hbox = QHBoxLayout(self.w)
        self.w_slider.setLayout(self.hbox)

        self.hbox.addWidget(QLabel("n-Clusters:"))
        self.hbox.addWidget(self.slider)
        self.lbl_n_cluster = QLabel("1")

        self.hbox.addWidget(self.lbl_n_cluster)
        self.btn_ok = QPushButton("Apply Segmentation")
        self.btn_ok.clicked.connect(self.apply_segmentation)
        self.btn_cancel = QPushButton("Cancel")

        self.w_buttons = QWidget(self)
        self.w_buttons.setLayout(QHBoxLayout(self.w_buttons))
        self.w_buttons.layout().addItem(QSpacerItem(1, 1, QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.w_buttons.layout().addWidget(self.btn_ok)
        self.w_buttons.layout().addWidget(self.btn_cancel)
        self.btn_cancel.clicked.connect(self.close)

        self.w.layout().addWidget(self.view)
        self.w.layout().addWidget(self.w_slider)
        self.w.layout().addWidget(self.w_buttons)

        self.resize(800, 500)
        self.on_slider_changed()

    def on_slider_changed(self):
        index = int(self.slider.value()) - 1 - self.cluster_range[0]

        self.lbl_n_cluster.setText(str(self.slider.value()))
        images = []
        segm_imgs = []
        curr_lbl = -1
        for i, c in enumerate(self.clusterings[index]):
            if i % self.frame_resolution == 0:
                i = int(i / self.frame_resolution)
                if c == curr_lbl:
                    segm_imgs.append(numpy_to_pixmap(self.frames[i]))
                else:
                    images.append(segm_imgs)
                    segm_imgs = []
                    segm_imgs.append(numpy_to_pixmap(self.frames[i]))
                    curr_lbl = c

        self.view.scene().clear()
        x = 0
        img_h = 200
        img_w = 200
        max_height = 0
        m_base = 0
        n_groups = int(len(images) / 2)
        for i, group in enumerate(images):
            y = 0 + m_base
            x += img_w
            for img in group:
                itm = self.view.scene().addPixmap(img)
                itm.setPos(x, y)
                y += 180
                if y > max_height:
                    max_height = y
            if i == n_groups:
                self.view.scene().addLine(0, max_height + 50, self.view.scene().itemsBoundingRect().width(), max_height + 50)
                m_base = max_height + 100
                x = img_w

        # rect = QRectF(self.view.scene().itemsBoundingRect().x(), self.view.scene().itemsBoundingRect().y(), 100, self.view.scene().itemsBoundingRect().height())
        self.view.fitInView(self.view.scene().itemsBoundingRect(), Qt.KeepAspectRatio)

    def apply_segmentation(self):
        index = int(self.slider.value()) - 1 - self.cluster_range[0]
        segments = []
        curr_lbl = -1
        curr_segment = [0, 0]
        last_idx = -1
        for i, c in enumerate(self.clusterings[index]):
            if i == 0:
                last_idx = 0
                curr_lbl = c

            elif c == curr_lbl:
                last_idx = i

            else:
                curr_segment[1] = self.indices[last_idx]
                segments.append(curr_segment)
                curr_segment = [self.indices[last_idx], 0]
                curr_lbl = c
                last_idx = i

        curr_segment[1] = self.indices[last_idx]
        segments.append(curr_segment)

        segmentation = self.project.create_segmentation("Auto Segmentation", dispatch=False)
        for s in segments:
            segmentation.create_segment2(frame2ms(s[0], self.fps),
                                         frame2ms(s[1], self.fps),
                                         mode=SegmentCreationMode.INTERVAL,
                                         inhibit_overlap=False,
                                         dispatch=False)

        self.project.dispatch_changed()

