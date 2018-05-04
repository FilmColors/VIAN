"""
Gaudenz Halter
University of Zurich
December 2017

This Script should be a basic example of how to use the IAnalysisJob Interface. 

The Goal is: 
    Creating a Barcode from the Segmentation of the user. 

"""

from core.data.interfaces import IAnalysisJob, ParameterWidget
from core.data.containers import *
from core.data.computation import ms_to_frames, numpy_to_pixmap

import webbrowser
from typing import List
import cv2
import numpy as np

from core.gui.ewidgetbase import EGraphicsView
BARCODE_MODE_BOTH = 0
BARCODE_MODE_HORIZONTAL = 1

# from bokeh.plotting import figure,save
# from bokeh.layouts import layout
# from bokeh.colors import RGB

class BarcodeAnalysisJob(IAnalysisJob):
    def __init__(self):
        super(BarcodeAnalysisJob, self).__init__("Barcode", [MOVIE_DESCRIPTOR, SEGMENTATION],
                                                 author="Gaudenz Halter",
                                                 version="1.0.0",
                                                 multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[Segmentation], parameters, fps):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.
        
        """
        # Since multiple_result is True, we want to generate a Barcode for each Segmentation
        # Thus an array of arguments has to be returned. For each Segmentation one argument Array
        args = []
        movie_path = project.movie_descriptor.get_movie_path()

        # Targets are Segmentations
        for tgt in targets:
            name = tgt.get_name()
            # Collecting all Segment start and end point in Frame-Indices

            segments = []
            if tgt.get_type() == SEGMENTATION:
                for segm in tgt.segments:
                    start = ms_to_frames(segm.get_start(), fps)
                    end = ms_to_frames(segm.get_end(), fps)

                    segments.append([start, end])

            else:
                duration = project.movie_descriptor.duration
                slice_size = parameters['slize_size']
                for i in range(int(duration / slice_size)):
                    segments.append([ms_to_frames(i, fps) * slice_size,
                                     ms_to_frames(i, fps) * slice_size + slice_size])
            args.append([segments, parameters, movie_path, name])

        return args

    def process(self, args, sign_progress):
        """
        This is the actual analysis, which takes place in a WorkerThread. 
        Do NOT and NEVER modify the project within this function.
        
        We want to read though the movie and get the Average Colors from each Segment.
        
        Once done, we create an Analysis Object from it.
        """
        # Signal the Progress
        sign_progress(0.0)

        segments = args[0]
        parameters = args[1]
        movie_path = args[2]
        name = args[3]

        resolution = parameters['resolution']

        # Creating the VideoCapture
        video_capture = cv2.VideoCapture(movie_path)
        width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))

        barcode = np.zeros(shape=(len(segments), 3))
        for idx, segm in enumerate(segments):
            sign_progress(idx / len(segments))
            start = segm[0]
            end   = segm[1]

            duration = end - start

            video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)
            segm_colors = []
            print(idx, len(segments), duration)
            # Looping over all Frames of the Segment and
            # Calculate the Average Color
            for i in range(duration):
                if i % resolution == 0:
                    video_capture.set(cv2.CAP_PROP_POS_FRAMES, i + start)
                    ret, frame = video_capture.read()
                else:
                    continue

                if frame is None:
                    break

                # segm_colors[i] = np.mean(frame, axis=(0,1))
                segm_colors.append(np.mean(frame, axis=(0,1)))

            barcode[idx] = np.mean(np.array(segm_colors), axis=0)

        # Creating an IAnalysisJobAnalysis Object that will be handed back to the Main-Thread
        analysis = IAnalysisJobAnalysis(name="Barcode_" + name,
                                        results=dict(barcode=barcode, width=width),
                                        analysis_job_class=self.__class__,
                                        parameters=parameters)

        sign_progress(1.0)
        return analysis

    def modify_project(self, project: VIANProject, result: IAnalysisJobAnalysis):
        """
        This Function will be called after the processing is completed. 
        Since this function is called within the Main-Thread, we can modify our project here.
        """
        # We want to create an Image Annotation with the Barcode in the upper part of the Display
        barcode_colors = result.data["barcode"]
        image_width = result.data["width"]

        if result.parameters['interpolation'] == "Cubic":
            interpolation = cv2.INTER_CUBIC
        else:
            interpolation = cv2.INTER_LINEAR

        # Creating an Image from the Color Array
        image = self.barcode_to_image(barcode_colors, image_width, image_height=50, interpolation=interpolation)

        # Storing the Image to Disc
        dir = project.results_dir

        path  = dir + "/" + result.get_name() + ".png"
        cv2.imwrite(path, image)

        # Modifying the Project by creating a new Layer and a new Annotation
        layer = project.create_annotation_layer("Barcode", 0, project.movie_descriptor.duration)
        layer.create_annotation(AnnotationType.Image,
                                             position = (0, 0),
                                             size = (image_width, 50),
                                             resource_path=path)

    def get_preview(self, analysis: IAnalysisJobAnalysis):
        """
        This should return the Widget that is shown in the Inspector when the analysis is selected
        """
        if analysis.parameters['interpolation'] == "Cubic":
            interpolation = cv2.INTER_CUBIC
        else:
            interpolation = cv2.INTER_LINEAR

        image = self.barcode_to_image(analysis.data['barcode'], 400, image_height=50, interpolation=interpolation)
        barcode_pixm = numpy_to_pixmap(image)
        view = QGraphicsView(QGraphicsScene())
        view.scene().addPixmap(barcode_pixm)
        return view

    def get_visualization(self, analysis, result_path, data_path, project, main_window):
        """
        This function should show the complete Visualization
        """
        widget = EGraphicsView(None, auto_frame=True)
        widget.set_image(numpy_to_pixmap(self.barcode_to_image(analysis.data['barcode'])))
        return [VisualizationTab(widget=widget,name="Barcode", use_filter=False,controls=None)]

    def barcode_to_image(self, barcode_colors, image_width = 4096, image_height=1024, interpolation=cv2.INTER_CUBIC):

        # Creating an Image from the Color Array
        image = np.zeros(shape=(image_height, barcode_colors.shape[0], 3), dtype=np.uint8)
        image[:, :] = barcode_colors
        image = cv2.resize(image, (image_width, image_height), interpolation=interpolation)

        return image

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
        self.setLayout(QVBoxLayout(self))

        l1 = QHBoxLayout(self)
        self.interpolation = QComboBox(self)
        self.interpolation.addItem("Cubic")
        self.interpolation.addItem("Linear")
        l1.addWidget(QLabel("Sizing Interpolation".ljust(25)))
        l1.addWidget(self.interpolation)

        l2 = QHBoxLayout(self)
        self.spin_frame = QSpinBox(self)
        self.spin_frame.setMinimum(1)
        self.spin_frame.setMaximum(10000)
        self.spin_frame.setValue(1000)
        l2.addWidget(QLabel("Frame Resolution".ljust(25)))
        l2.addWidget(self.spin_frame)

        l3 = QHBoxLayout(self)
        self.spin_slice = QSpinBox(self)
        self.spin_slice.setMinimum(1)
        self.spin_slice.setMaximum(10000)
        self.spin_slice.setValue(1000)
        l3.addWidget(QLabel("Slice Width".ljust(25)))
        l3.addWidget(self.spin_slice)


        self.layout().addItem(l1)
        self.layout().addItem(l2)
        self.layout().addItem(l3)

    def get_parameters(self):
        resolution = self.spin_frame.value()
        interpolation = self.interpolation.currentText()
        slize_size = self.spin_slice.value()
        parameters = dict(
            resolution=resolution,
            interpolation=interpolation,
            slize_size = slize_size
        )
        return parameters