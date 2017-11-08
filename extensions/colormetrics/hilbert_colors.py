import cv2
import numpy as np

from core.data.containers import Analysis
from core.data.containers import *
from core.data.interfaces import IAnalysisJob
from core.gui.ewidgetbase import EMatplotLibVis
from computation import calculate_histogram
from hilbert import create_hilbert_color_pattern, hilbert_mapping_3d, HilbertMode


__version__ = "1.0.0"
class HilbertHistogramVis(EMatplotLibVis):
    def __init__(self, parent, analysis):
        super(HilbertHistogramVis, self).__init__(parent, analysis)
        self.plot()

    def plot(self):
        x = range(len(self.analyze.data[0]))
        y = self.analyze.data[0]
        colors = []
        for c in self.analyze.data[1]:
            colors.append([float(c[2])/255,float(c[1])/255,float(c[0])/255, 1.0])


        # plot data
        self.figure.axes.bar(x, y, width=1, color=colors,log=1)

        # refresh canvas
        self.show()

class HilbertHistogramProc(IAnalysisJob):
    name = "Hilbert Histogram"
    source_types = [SEGMENTATION, SCREENSHOT, SEGMENT, ANNOTATION_LAYER, ANNOTATION]

    def __init__(self, id):
        self.name = "Hilbert Histogram"
        self.procedure_id = id

    def process(self, args, sign_progress):
        movie_path = args[0]
        start = args[1]
        end = args[2]

        length = end - start

        video_capture = cv2.VideoCapture(movie_path)
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, start)

        width = video_capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT)

        grad_bokeh, grad_in_bgr = create_hilbert_color_pattern(8, 32)

        hist_stack = np.zeros(shape=(length, 8, 8, 8))

        for i in range(length):
            if i % 10 == 0:
                progress = float(i) / length
                sign_progress(progress)

            ret, frame = video_capture.read()
            if frame is not None:
                frame = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_BGR2Lab)
                hist = calculate_histogram(frame, 8)
                hist_stack[i] = hist
            else:
                print "Not worked"

        result = np.sum(hist_stack, axis=0)
        result = np.divide(result, length * width * height)
        hist = hilbert_mapping_3d(8, result, HilbertMode.Values_All)

        analysis = Analysis("Hilbert Colors", start, end, [hist, grad_in_bgr[0]], procedure_id=self.procedure_id)
        sign_progress(1.0)
        return analysis

    def get_visualization(self, parent, analysis):
        return HilbertHistogramVis(parent, analysis)

    def get_name(self):
        return self.name

    def get_source_types(self):
        return self.source_types

class HilbertTSNEProc(IAnalysisJob):
    name = "Hilbert Histogram based t-SNE"
    source_types = [SCREENSHOT, SEGMENT, ANNOTATION_LAYER, ANNOTATION]

    def __init__(self, id):
        self.procedure_id = id

    def process(self, args, sign_progress):
        print "Do Something"

