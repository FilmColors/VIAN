"""
Gaudenz Halter
University of Zurich
June 2018

"""

from vian.core.data.interfaces import IAnalysisJob, ParameterWidget, TimelineDataset, SpatialOverlayDataset
from vian.core.container.project import BaseProjectEntity, VIANProject, MOVIE_DESCRIPTOR, DataSerialization, FileAnalysis
from vian.core.container.corpus import Corpus
from vian.core.container.analysis import IAnalysisJobAnalysis

from vian.core.analysis.color.palette_extraction import *
from vian.core.container.hdf5_manager import vian_analysis
from vian.core.visualization.palette_plot import *

import pandas as pd
from matplotlib import cm

colormap = cm.get_cmap("viridis")


@vian_analysis
class EyetrackingAnalysis(IAnalysisJob):
    def __init__(self, resolution=30):
        super(EyetrackingAnalysis, self).__init__("Eyetracking",
                                                  [MOVIE_DESCRIPTOR],
                                                  author="Gaudenz Halter",
                                                  version="1.0.0",
                                                  multiple_result=False,
                                                  data_serialization=DataSerialization.FILE)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[BaseProjectEntity], fps, class_objs=None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.

        """
        super(EyetrackingAnalysis, self).prepare(project, targets, fps, class_objs)

        cap = cv2.VideoCapture(project.movie_descriptor.movie_path)
        width, height = cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        args = dict(
            file=QFileDialog.getOpenFileName(filter="*.csv")[0],
            fps=project.movie_descriptor.fps, width=width,
            frame_count=frame_count,
            height=height,
            target=targets[0]
        )

        return args

    def process(self, argst, sign_progress):
        file_path = argst['file_path']
        fps = argst['fps']
        stimulus_to_import = argst['stimulus']
        fixations = pd.read_csv(file_path,  delimiter="\t")

        q = []
        for index, r in fixations.iterrows():
            try:
                stimulus = os.path.splitext(r['Stimulus'])[0].replace("bw_", "")
                if stimulus != stimulus_to_import:
                    continue

                x = int(round(float(r['Fixation Position X [px]'])))
                y = int(round(float(r['Fixation Position Y [px]'])))
                t0 = int(round(float(r['Event Start Trial Time [ms]'])))
                t1 = int(round(float(r['Event End Trial Time [ms]'])))
            except Exception as e:
                print (e)
                continue

            n = ms_to_frames(t1 - t0, fps)
            if fps != 0:
                n = int(np.floor(n / fps))
                f_step = fps
            else:
                f_step = 1

            f0 = ms_to_frames(t0, fps)
            # print(n)

            for i in range(n):
                q.append(dict(
                    Stimulus = stimulus,
                    FixationX = x,
                    FixationY = y,
                    FramePos = f0 + (i * f_step)
                ))

        fixations_sampled = pd.DataFrame(q)

        return FileAnalysis(
            name="Eyetracking Dataset",
            results=fixations_sampled,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution)
        )

    def from_importer(self, fixations_sampled):

        return FileAnalysis(
            name="Eyetracking Dataset",
            results=fixations_sampled,
            analysis_job_class=self.__class__,
            parameters=dict(resolution=self.resolution)
        )


    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed. 
        Since this function is called within the Main-Thread, we can modify our project here.
        """

        super(EyetrackingAnalysis, self).modify_project(project, result, main_window)

    def get_timeline_datasets(self, analysis, project) -> List[TimelineDataset]:
        df = analysis.get_adata()
        fps = project.movie_descriptor.fps
        ms_to_idx = 1000 / (fps / self.resolution)

        time_np = np.zeros(len(df.index))
        fixations_np = np.zeros((len(df.index), 2))

        for i, row in df.iterrows():
            fixations_np[i] = [row.FixationX, row.FixationY]
            time_np[i] = row.FramePos

        time_np = np.array(time_np)
        fixations_np = np.array(fixations_np)

        result = []
        for pos in range(int(np.floor(ms_to_frames(project.movie_descriptor.duration, fps) / self.resolution))):
            pos = pos * self.resolution

            # Get all values which are within the time window
            indices = np.where(np.logical_and(pos - (fps / 2) < time_np, time_np < pos + (fps / 2)))
            points = fixations_np[indices]

            # Compute the vector magnitude (from the screen root)
            mag = np.linalg.norm(points, axis = 1)
            # Compute the variance in vector magnitude
            result.append(float(np.var(mag)))

        result = np.array(result)
        result -= np.amin(result)

        return [
            TimelineDataset("Eyetracking Variance",
                            result,
                            ms_to_idx=ms_to_idx,
                            vis_type=TimelineDataset.VIS_TYPE_LINE,
                            vis_color=QColor(188, 80, 144))
        ]

    def get_spatial_overlays(self, analysis, project) -> List[SpatialOverlayDataset]:
        ms_to_idx = 1000 / (project.movie_descriptor.fps / self.resolution)

        return [
            RawPointsSpatialDataset(ms_to_idx, fixations_sampled=analysis.get_adata(),
                                    fps=project.movie_descriptor.fps,
                                    analysis=analysis,
                                    project=project)
        ]

    def to_file(self, data, file_path):
        file_path = file_path + ".csv"
        data.to_csv(file_path)
        return file_path

    def from_file(self, file_path):
        file_path = file_path + ".csv"
        data = pd.read_csv(file_path)
        return data


class RawPointsSpatialDataset(SpatialOverlayDataset):
    def __init__(self, ms_to_idx, analysis, project, fixations_sampled, fps):
        super(RawPointsSpatialDataset, self).__init__("Eyetracking: Raw Points",
                                                      ms_to_idx,
                                                      project,
                                                      analysis,
                                                      vis_type=SpatialOverlayDataset.VIS_TYPE_HEATMAP)
        self.fixations_sampled = fixations_sampled
        self.time_np = np.zeros(len(self.fixations_sampled.index))
        self.fixations_np = np.zeros((len(self.fixations_sampled.index), 2))

        for i, row in self.fixations_sampled.iterrows():
            self.fixations_np[i] = [row.FixationX, row.FixationY]
            self.time_np[i] = row.FramePos

        self.time_np = np.array(self.time_np)
        self.fixations_np = np.array(self.fixations_np)

        print(self.fixations_np.shape, (self.time_np.nbytes + self.fixations_np.nbytes) / 1000000, "Megabytes")
        self.fps = fps
        cap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        self.width =  cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def get_data_for_time(self, time_ms, frame):
        if time_ms is not None:
            pos = ms_to_frames(time_ms, self.fps)
        else:
            pos = frame
        if self.fixations_sampled is not None:
            indices = np.where(np.logical_and(pos - (self.fps / 2) < self.time_np, self.time_np <  pos + (self.fps/2)))
            points = self.fixations_np[indices]

            return np.unique(points, axis=0)
        else:
            return None


from vian.core.data.importers import ImportDevice
from vian.core.gui.ewidgetbase import EDialogWidget
from PyQt5 import uic
from vian.core.analysis.eyetracking.parser import XEyeTrackingHandler
import glob


class DialogImportEyetracking(EDialogWidget):
    def __init__(self, main_window):
        super(DialogImportEyetracking, self).__init__(main_window, main_window, "https://www.vian.app/static/manual/step_by_step/project_management/export_segmentation.html")
        path = os.path.abspath("qt_ui/DialogImportEyetracking.ui")
        uic.loadUi(path, self)

        self.import_path = "extensions/plugins/eyetracking_comparator/eyetracking-fixations.txt"
        self.fixation = None
        self.stimuli_directory = "E:/Programming/Datasets/eye-tracking"

        self.btnBrowse.clicked.connect(self.on_browse)
        self.btnBrowseStimuli.clicked.connect(self.on_browse_stimuli)
        self.lineEditPath.textChanged.connect(self.on_path_changed)
        self.btnImport.clicked.connect(self.on_import)

    def on_browse(self):
        file = QFileDialog.getOpenFileName(filter="*.csv *.txt")[0]
        if os.path.isfile(file):
            self.import_path = file
            self.lineEditPath.setText(self.import_path)

    def on_browse_stimuli(self):
        directory = QFileDialog.getExistingDirectory()
        if os.path.isdir(directory):
            self.stimuli_directory = directory
            self.lineEditStimuli.setText(self.stimuli_directory)


    def on_path_changed(self):
            df = pd.read_csv(self.import_path, delimiter="\t")
            print(df)

            try:
                stimuli = df["Stimulus"].unique().tolist()
                self.cbStimulus.clear()
                self.cbStimulus.addItem("All")
                for s in stimuli:
                    self.cbStimulus.addItem(s)
            except Exception as e:
                print(e)

    def on_import(self, sfilter=None):
        if not os.path.isfile(self.import_path) or not os.path.isdir(self.stimuli_directory):
            return

        handler = XEyeTrackingHandler()
        handler.import_(self.import_path, delimiter="\t", sfilter=sfilter)


        stimuli = glob.glob(self.stimuli_directory + "/*")
        handler.import_movie_meta(stimuli)

        result = handler.subsample()

        c_dir = os.path.join(self.main_window.settings.DIR_CORPORA, "eyetracking_corpus")
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
                project.store_project()
                project_path = project.path
            corpus.add_project(file=project_path)

        corpus.save(c_file)
        self.main_window.corpus_widget.load_corpus(corpus.file)




