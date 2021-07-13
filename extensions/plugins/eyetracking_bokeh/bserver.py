if __name__ == '__main__':
    import sys, os
    os.chdir("../../../")

import glob

import cv2
import numpy as np

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import os
from core.data.plugin import *
from core.data.computation import numpy_to_pixmap, ms_to_frames, lch_to_human_readable
from core.gui.ewidgetbase import EGraphicsView
from flask_server.server import FlaskWebWidget

from core.analysis.analysis_utils import run_analysis
from core.analysis.analysis_import import ColormetryJob2
from core.analysis.motion.optical_flow import OpticalFlowAnalysis

from core.container.corpus import VIANProject, Corpus

import pandas as pd
from core.data.settings import UserSettings

from core.analysis.eyetracking.parser import XEyeTrackingHandler
from core.analysis.eyetracking.eyetracking import EyetrackingAnalysis
# from extensions.plugins.eyetracking_comparator.eyetracking import XEyeTrackingHandler



class EyetrackingComparatorPlugin(GAPlugin):
    def __init__(self, main_window):
        super(EyetrackingComparatorPlugin, self).__init__(main_window)
        self.plugin_name = "Eyetracking Comparator Bokeh"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = EyetrackingComparator(parent, self)
        wnd.show()


class EyetrackingRenderer(EGraphicsView):
    def __init__(self, parent):
        super(EyetrackingRenderer, self).__init__(parent, auto_frame=True)

    def add_point(self, x, y):
        p = QPen()
        p.setColor(QColor(255,255,255))
        p.setWidth(10)
        self.gscene.addEllipse(x, y, 3, 3,p,QBrush(QColor(255,255,255)))
        pass


class EyetrackingComparator(QMainWindow):
    onTimeStep = pyqtSignal(int)
    actionIntervalSegmentStart = pyqtSignal(int)
    # onTimeStep = pyqtSignal(int)

    def __init__(self, parent, extension):
        super(EyetrackingComparator, self).__init__(parent)
        self.extension = extension
        self.dock_widgets = []
        self.settings = UserSettings()
        self.player = None

        self.brower = FlaskWebWidget(self)
        self.addDockWidget(Qt.BottomDockWidgetArea,self.brower )

        self.m_file = self.menuBar().addMenu("File")
        self.m_file.addAction("Open")
        self.center = QWidget(self)
        self.center.setLayout(QVBoxLayout())
        self.setCentralWidget(self.center)

        self.splitter = QSplitter()
        self.center.layout().addWidget(self.splitter)

        self.slider = QSlider(self, orientation=Qt.Horizontal)
        self.center.layout().addWidget(self.slider)

        self.slider.valueChanged.connect(self.update_movie_position)

        self.view1 = EyetrackingRenderer(self)
        self.view2 = EyetrackingRenderer(self)
        self.splitter.addWidget(self.view1)
        self.splitter.addWidget(self.view2)
        self.changer = QComboBox()

        self.corpus = Corpus()
        self.p1 = None
        self.p1 = None

        self.changer.addItems([
            "14_1_2_UneFemmeEstUneFemme_1961_DVD",
            "16_1_3_AgeOfInnocence_1993_DVD",
            "215_1_3_TheCookTheThiefHisWifeAndHerLover_1990_DVD",
            "216_1_2_ParapluiesdeCherbourg_1964_DVD",
            "240_1_2_InTheMoodForLove_2000_DVD",
            "240_1_3_InTheMoodForLove_2000_DVD",
            "246_1_4_SayatNova_1969_DVD",
            "261_1_3_SeiDonnePerLAssassino_1964_DVD",
            "315_1_2_Playtime_1967_DVD",
            "766_1_2_DasParfum_2006_DVD",
            "902_1_2_MorteAVenezia_1971_DVD"
        ])

        self.changer.currentTextChanged.connect(self.change_stimulus)
        self.center.layout().addWidget(self.changer)
        self.r1 = None
        self.r2 = None
        self.sample_fps = 30

        # self.load_corpus("C:/Users/gaude/Documents/VIAN/corpora/eyetracking_corpus/eyetracking_corpus.vian_corpus")

        self.create_corpus("E:\Programming\Datasets\eye-tracking",
                           "extensions/plugins/eyetracking_comparator/eyetracking-fixations.txt",
                           "C:/Users/gaude/Documents/VIAN/corpora/eyetracking_corpus2")
        self.load_corpus("C:/Users/gaude/Documents/VIAN/corpora/eyetracking_corpus2/eyetracking_corpus.vian_corpus")

        # self.open("E:\Programming\Git\ERC_FilmColors/resources\eyetracking\snippets/14_1_2_UneFemmeEstUneFemme_1961_DVD.mp4", None)
        # self.load_fixations("extensions/plugins/eyetracking_comparator/eyetracking-fixations.txt")

    def create_corpus(self, stimuli_directory, import_path, corpus_dir):
        if not os.path.isfile(import_path) or not os.path.isdir(stimuli_directory):
            return

        handler = XEyeTrackingHandler()
        handler.import_(import_path, delimiter="\t", sfilter=None)

        stimuli = glob.glob(stimuli_directory + "/*")
        handler.import_movie_meta(stimuli)

        result = handler.subsample()

        c_dir = os.path.join(corpus_dir)
        c_file = os.path.join(c_dir, "eyetracking_corpus")
        os.mkdir(c_dir)

        p_dir = os.path.join(c_dir, "projects")
        os.mkdir(p_dir)

        corpus = Corpus("Eyetracking Corpus", )
        corpus.save(c_file)

        for k, v in result.items():
            v_dir = os.path.join(p_dir, k)
            os.mkdir(v_dir)

            project_path = None

            with VIANProject(k, folder=v_dir, movie_path=v['stimulus']['path']) as project:
                analysis = EyetrackingAnalysis().from_importer(v['df'])
                project.add_analysis(analysis)
                run_analysis(project, OpticalFlowAnalysis(), [project.movie_descriptor], None)

                cmetry = ColormetryJob2(10, None)
                args = cmetry.prepare(project)
                cmetry.run_concurrent(args, None)

                project.store_project()
                project_path = project.path

            corpus.add_project(file=project_path)

        corpus.save(c_file)
        self.load_corpus(c_file)

    def load_corpus(self, path):
        self.corpus.load(path)
        self.corpus.reload()

        self.changer.clear()

        for k, p in self.corpus.projects_loaded.items():
            self.changer.addItem(p.name.replace("True", "").replace("False", ""))
            p.connect_hdf5()
            for i, entry in enumerate(p.colormetry_analysis.iter_avg_color()):
                l, c, h = lch_to_human_readable([entry['l'], entry['c'], entry['h']])
                print(l, c, h)
                # data[i] = [
                #     entry['time_ms'],
                #     entry['l'],
                #     entry['a'],
                #     entry['b'],
                #     c,
                #     h,
                # ]
                # timestamps.append(ms_to_string(entry['time_ms']))

    def on_interval_segment(self):
        pass

    def change_stimulus(self, s):
        name = self.changer.currentText()
        projects = []
        for p in self.corpus.projects_loaded.values():
            if name in p.name:
                projects.append(p)

        self.open(m1 = os.path.join("E:\Programming\Datasets\eye-tracking", s) + ".mp4")

    def open(self, m1, m2 = None):
        self.r1 = cv2.VideoCapture(m1)
        if m2 is not None:
            self.r2 = cv2.VideoCapture(m2)
            frame_count = min(self.r1.get(cv2.CAP_PROP_FRAME_COUNT), self.r2.get(cv2.CAP_PROP_FRAME_COUNT)) - 1
        else:
            frame_count = self.r1.get(cv2.CAP_PROP_FRAME_COUNT)

        self.sample_fps = self.r1.get(cv2.CAP_PROP_FPS)
        self.slider.setMaximum(frame_count)
        self.update_movie_position()

        self.stimulus = os.path.split(m1)[1].split(".")[0]

    def load_fixations(self, file_path,  reference_frame = (1680, 1050)):
        pass

    def update_movie_position(self):
        pos = self.slider.value()
        self.r1.set(cv2.CAP_PROP_POS_FRAMES, pos)
        r, f1 = self.r1.read()

        if f1 is None:
            return

        if self.r2 is not None:
            self.r2.set(cv2.CAP_PROP_POS_FRAMES, pos)
            r, f2 = self.r2.read()

        else:
            f2 = cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY)

        self.view1.set_image(numpy_to_pixmap(f1))
        self.view2.set_image(numpy_to_pixmap(f2))



if __name__ == '__main__':

    import sys
    # os.chdir("../../../")

    print("Currdir", os.path.abspath(os.curdir))
    def my_exception_hook(exctype, value, traceback):
        # Print the error and traceback
        print((exctype, value, traceback))
        # Call the normal Exception hook after
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)


    def set_style_sheet(app, path):
        style_sheet = open(os.path.abspath(path), 'r')
        style_sheet = style_sheet.read()
        app.setStyleSheet(style_sheet)

    sys._excepthook = sys.excepthook
    sys.excepthook = my_exception_hook

    app = QApplication(sys.argv)

    set_style_sheet(app, "qt_ui/themes/qt_stylesheet_very_dark.css")

    main = EyetrackingComparator(None, None)
    main.show()
    sys.exit(app.exec_())


