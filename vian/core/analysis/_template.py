from typing import List
import numpy as np

from PyQt6.QtCore import QObject

from vian.core.data.enums import *
from vian.core.data.log import log_info, log_warning, log_error, log_debug
from vian.core.data.interfaces import IAnalysisJob, ParameterWidget, VisualizationTab

from vian.core.gui.ewidgetbase import EGraphicsView

from vian.core.container.hdf5_manager import vian_analysis
from vian.core.container.analysis import IAnalysisJobAnalysis
from vian.core.container.project import VIANProject, Segmentation

# Uncomment to enable the Analysis in VIAN
# @vian_analysis
class FooAnalysis(IAnalysisJob):
    """
    This is the BaseClass for all Analyses.
    Subclass it to implement your own Analyses.

    """

    def __init__(self, resolution=30):
        super(FooAnalysis, self).__init__("Barcode", [MOVIE_DESCRIPTOR, SEGMENTATION, SEGMENT],
                                                 dataset_name="Barcodes",
                                                 dataset_shape=(3, 3),
                                                 dataset_dtype=np.uint8,
                                                 author="Gaudenz Halter",
                                                 version="1.0.0",
                                                 multiple_result=True)
        self.resolution = resolution

    def prepare(self, project: VIANProject, targets: List[Segmentation], fps, class_objs=None):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
        and gather all data we need.

        """
        super(FooAnalysis, self).prepare(project, targets, fps, class_objs)
        args = []
        return args

    def process(self, args, sign_progress):
        """
        This is the actual analysis, which takes place in a WorkerThread.
        Do NOT and NEVER modify the project within this function.

        We want to read though the movie and get the Average Colors from each Segment.

        Once done, we create an Analysis Object from it.
        """
        args, sign_progress = super(FooAnalysis, self).process(args, sign_progress)
        # Signal the Progress
        sign_progress(0.0)

        # Creating an IAnalysisJobAnalysis Object that will be handed back to the Main-Thread
        analysis = IAnalysisJobAnalysis(name="My Analysis",
                                        results=dict(data="some_data"),
                                        analysis_job_class=self.__class__,
                                        parameters=dict(resolution=self.resolution),
                                        container=args[4])
        sign_progress(1.0)
        return analysis

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
        """
        This Function will be called after the processing is completed.
        Since this function is called within the Main-Thread, we can modify our project here.
        """
        pass

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """

        return EGraphicsView(None)

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        return [VisualizationTab(widget=EGraphicsView(None), name="Barcode", use_filter=False, controls=None)]

    def get_parameter_widget(self):
        """
        Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user
        activates the Analysis.
        """
        return BarcodeParameterWidget()


class BarcodeParameterWidget(ParameterWidget):
    """
    We want the User to be able to determine the resolution of frames when reading and the
    interpolation type for the Preview.

    To do so we create a Parameter Widget and override the get_parameters function
    """

    def __init__(self):
        super(BarcodeParameterWidget, self).__init__()
        # Put UI Here

    def get_parameters(self):
        """
        This function is called by VIAN to retrieve the user given parameters.
        Override to add functionality
        :return:
        """
        parameters = dict(
        )
        return parameters