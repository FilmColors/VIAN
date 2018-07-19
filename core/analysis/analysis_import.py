from core.analysis.color_feature_extractor import *
from core.analysis.palette_analysis import *
from core.analysis.barcode_analysis import *
from core.analysis.movie_mosaic.movie_mosaic import *
from core.analysis.colorimetry.colormetry2 import *
try:
    from core.analysis.semantic_segmentation import *
except:
    from core.data.enums import DataSerialization
    from core.analysis.deep_learning.labels import *

    class SemanticSegmentationAnalysis(IAnalysisJob):
        def __init__(self):
            super(SemanticSegmentationAnalysis, self).__init__("Semantic Segmentation", [SCREENSHOT, SCREENSHOT_GROUP],
                                                               author="Gaudenz Halter",
                                                               version="1.0.0",
                                                               multiple_result=False,
                                                               data_serialization=DataSerialization.MASKS)

        def prepare(self, project: VIANProject, targets: List[IProjectContainer], parameters, fps, class_objs=None):
            """
            This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project,
            and gather all data we need.

            """
            super(SemanticSegmentationAnalysis, self).prepare(project, targets, parameters, fps, class_objs)

            args = []
            fps = project.movie_descriptor.fps
            for tgt in targets:
                if tgt.get_type() == SCREENSHOT_GROUP:
                    for s in tgt.screenshots:
                        args.append([ms_to_frames(s.get_start(), fps), ms_to_frames(s.get_end(), fps),
                                     project.movie_descriptor.movie_path, parameters, s.get_id()])
                else:
                    args.append([ms_to_frames(tgt.get_start(), fps), ms_to_frames(tgt.get_end(), fps),
                                 project.movie_descriptor.movie_path, parameters, tgt.get_id()])
            return args

        def process(self, args, sign_progress):
            print("No KERAS Backend Installed, you can not peform this analysis")

        def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis, main_window=None):
            """
            This Function will be called after the processing is completed.
            Since this function is called within the Main-Thread, we can modify our project here.
            """
            result.set_target_container(project.get_by_id(result.target_container))
            result.set_target_classification_obj(self.target_class_obj)

        def get_preview(self, analysis: IAnalysisJobAnalysis):
            """
            This should return the Widget that is shown in the Inspector when the analysis is selected
            """
            widget = EGraphicsView(None, auto_frame=True)
            widget.set_image(numpy_to_pixmap(cv2.cvtColor(analysis.get_adata()['mask'], cv2.COLOR_GRAY2BGR)))
            return widget

        def get_visualization(self, analysis, result_path, data_path, project, main_window):
            """
            This function should show the complete Visualization
            """
            widget = EGraphicsView(None, auto_frame=True)
            widget.set_image(numpy_to_pixmap(cv2.cvtColor(analysis.get_adata()['mask'], cv2.COLOR_GRAY2BGR)))
            return [VisualizationTab(widget=widget, name="Semantic Segmentation Mask", use_filter=False, controls=None)]

        def get_parameter_widget(self):
            """
            Returning a ParameterWidget subclass which will be displayed in the Analysis Dialog, when the user
            activates the Analysis.
            """
            return SemanticSegmentationParameterWidget()

        def serialize(self, data_dict):
            data = dict(
                mask=pickle.dumps(data_dict['mask']),
                frame_sizes=data_dict['frame_sizes'],
                dataset=data_dict['dataset']
            )
            return data

        def deserialize(self, data_dict):
            data = dict(
                mask=pickle.loads(data_dict['mask']),
                frame_sizes=data_dict['frame_size'],
                dataset=data_dict['dataset']
            )
            return data

        def from_json(self, database_data):
            # return json.loads(database_data)
            return pickle.loads(database_data)

        def to_json(self, container_data):
            return pickle.dumps(container_data)
            # return json.dumps(self.serialize(container_data))
