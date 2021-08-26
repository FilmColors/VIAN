if __name__ == '__main__':
    import sys, os
    os.chdir("../../../")


import cv2
import numpy as np

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import os
from core.data.plugin import *
from core.data.computation import numpy_to_pixmap, ms_to_frames
from core.gui.ewidgetbase import EGraphicsView

from core.gui.timeline.timeline import TimelineContainer
import pandas as pd
from core.data.settings import UserSettings
from extensions.plugins.eyetracking_comparator.eyetracking import XEyeTrackingHandler



class EyetrackingComparatorPlugin(GAPlugin):
    def __init__(self, main_window):
        super(EyetrackingComparatorPlugin, self).__init__(main_window)
        self.plugin_name = "Eyetracking Comparator"
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

        self.timeline = TimelineContainer(self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.timeline)

        self.fixations = None
        self.fixations_sampled = None

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

        self.open("E:\Programming\Git\ERC_FilmColors/resources\eyetracking\snippets/14_1_2_UneFemmeEstUneFemme_1961_DVD.mp4",
                  None)
        # self.load_fixations("eyetracking-fixations.txt")

    def on_interval_segment(self):
        pass

    def change_stimulus(self, s):
        self.open( m1 = os.path.join("E:\Programming\Datasets\eye-tracking", s) + ".mp4")

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
        self.fixations = pd.read_csv(file_path, delimiter="\t")
        self.fixations_sampled = pd.DataFrame(["Stimulus", "FixationX", "FixationY", "FramePos", "isBlackWhite"])

        width = self.r1.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = self.r1.get(cv2.CAP_PROP_FRAME_HEIGHT)

        fw = width / reference_frame[0]
        fh = height / reference_frame[1]

        q = []
        for index, r in self.fixations.iterrows():
            try:
                is_bw = "bw_" in r.Stimulus
                stimulus = os.path.splitext(r['Stimulus'])[0].replace("bw_", "")
                x = int(round(float(r['Fixation Position X [px]'])))
                y = int(round(float(r['Fixation Position Y [px]'])))
                t0 = int(round(float(r['Event Start Trial Time [ms]'])))
                t1 = int(round(float(r['Event End Trial Time [ms]'])))
            except Exception as e:
                continue

            n = ms_to_frames(t1 - t0, self.sample_fps / 4)
            if self.sample_fps != 0:
                n = int(np.floor(n / (self.sample_fps / 4)))
                f_step = self.sample_fps / 4
            else:
                f_step = 1

            f0 = ms_to_frames(t0, self.sample_fps)
            # print(n)

            for i in range(n):
                q.append(dict(
                    Stimulus=stimulus,
                    isBlackWhite=is_bw,
                    FixationX=int(x * fw),
                    FixationY=int(y * fh),
                    FramePos=f0 + (i * f_step)
                ))
        self.fixations_sampled = pd.DataFrame(q)
        self.fixations = self.fixations_sampled

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

        if self.fixations_sampled is not None:
            points = self.fixations_sampled[self.fixations_sampled.Stimulus == self.stimulus]\
            [self.fixations_sampled.FramePos < pos + self.sample_fps]\
            [self.fixations_sampled.FramePos > pos - self.sample_fps]
            for i, d in points.iterrows():
                # if i == 0:
                #     self.view1.scene().clear()
                #     self.view2.scene().clear()
                if d.isBlackWhite:
                    self.view2.add_point(d.FixationX, d.FixationY)
                else:
                    self.view1.add_point(d.FixationX, d.FixationY)
        self.update()





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


