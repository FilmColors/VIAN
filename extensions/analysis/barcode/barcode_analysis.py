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


# from bokeh.plotting import figure,save
# from bokeh.layouts import layout
# from bokeh.colors import RGB

class BarcodeAnalysisJob(IAnalysisJob):
    def __init__(self):
        super(BarcodeAnalysisJob, self).__init__("Barcode", [SEGMENTATION], author="Gaudenz Halter", version="1.0.0", multiple_result=True)

    def prepare(self, project: VIANProject, targets: List[Segmentation], parameters, fps):
        """
        This function is called before the analysis takes place. Since it is in the Main-Thread, we can access our project, 
        and gather all data we need.
        
        """
        # Since multiple_result is True, we want to generate a Barcode for each Segmentation
        # Thus an array of arguments has to be returned. For each Segmentation one argument Array
        args = []
        movie_path = project.movie_descriptor.movie_path


        # Targets are Segmentations
        for tgt in targets:
            name = tgt.get_name()
            # Collecting all Segment start and end point in Frame-Indices
            segments = []
            for segm in tgt.segments:
                start = ms_to_frames(segm.get_start(), fps)
                end = ms_to_frames(segm.get_end(), fps)

                segments.append([start, end])

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

            # Looping over all Frames of the Segment and
            # Calculate the Average Color
            for i in range(duration):
                if i / resolution != 0:
                    continue

                ret, frame = video_capture.read()

                if frame is None:
                    break

                # segm_colors[i] = np.mean(frame, axis=(0,1))
                segm_colors.append(np.mean(frame, axis=(0,1)))

            barcode[idx] = np.mean(np.array(segm_colors), axis=(0))

        # Creating an IAnalysisJobAnalysis Object that will be handed back to the Main-Thread
        analysis = IAnalysisJobAnalysis(name="Barcode_" + name,
                                        results=[barcode, width],
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
        barcode_colors = result.data[0]
        image_width = result.data[1]

        if result.parameters['interpolation'] == "Cubic":
            interpolation = cv2.INTER_CUBIC
        else:
            interpolation = cv2.INTER_LINEAR

        # Creating an Image from the Color Array
        image = self.barcode_to_image(barcode_colors, image_width, image_height=50, interpolation=interpolation)

        # Storing the Image to Disc
        dir = project.results_dir
        print(dir, result, result.get_name())
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

        image = self.barcode_to_image(analysis.data[0], 400, image_height=50, interpolation=interpolation)
        barcode_pixm = numpy_to_pixmap(image)
        print(barcode_pixm.height(), barcode_pixm.width())
        view = QGraphicsView(QGraphicsScene())
        view.scene().addPixmap(barcode_pixm)
        return view

    def get_visualization(self, analysis: IAnalysisJobAnalysis, result_path, data_path):
        """
        This function should show the complete Visualization
        """
        barcode = analysis.data[0]
        colors = []
        #TODO pyqtGraph Visualization
        # for c in barcode:
        #     colors.append(RGB(c[2], c[1], c[0]))
        #
        # path = data_path +"/"+ analysis.get_name() + ".html"
        #
        # plot = figure(width=800, height=400)
        # plot.rect(x=range(barcode.shape[0]), y = 0.5, width = 1, height=1, color=colors)
        #
        # l = layout(
        #     [
        #         [plot]
        #     ]
        # )
        #
        # print(path)
        # save(l, path)
        # open_web_browser(path)

    def barcode_to_image(self, barcode_colors, image_width, image_height, interpolation):

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
        self.spin_frame.setMaximum(100)
        self.spin_frame.setValue(1)
        l2.addWidget(QLabel("Frame Resolution".ljust(25)))
        l2.addWidget(self.spin_frame)


        self.layout().addItem(l1)
        self.layout().addItem(l2)

    def get_parameters(self):
        resolution = self.spin_frame.value()
        interpolation = self.interpolation.currentText()
        parameters = dict(
            resolution=resolution,
            interpolation=interpolation,
        )
        return parameters