import cv2
import numpy as np
from matplotlib import pyplot as plt
from PyQt5.QtCore import QObject
from PyQt5.QtGui import *
from core.data.computation import numpy_to_qt_image
from random import randint
from core.node_editor.datatypes import *
from core.node_editor.script_results import *
from core.data.enums import *

from bokeh.plotting import figure
from bokeh.layouts import layout
from bokeh.resources import CDN
from bokeh.embed import file_html


# DT_IMAGE = (0, QColor(255,255,199))
# DT_COLOR = (1, QColor(252,170,103))
# DT_ARRAY = (2, QColor(71,51,53))
# DT_NUMERIC = (3, QColor(3,63,99))

class Slot():
    def __init__(self, name, data_type, default_value):
        self.name = name
        self.data_type = data_type
        self.default_value = default_value
        self.default_data_type = data_type


class Operation(QObject):
    onProgress = pyqtSignal(float)

    def __init__(self, name, input_types, output_types,
                 is_final_node = False, needs_project = False,
                 vis_type = VIS_TYPE_IMAGE, execute_output_fields_in_loop = True, multi_execute=False):
        super(Operation, self).__init__()
        self.name = name
        self.result = np.array([None] * len(output_types))
        self.node = None


        # self.input_types = input_types
        # self.output_types = output_types
        self.input_slots = input_types
        self.output_slots = output_types

        # for i in input_types:
        #     self.input_types.append(i())
        # for o in output_types:
        #     self.output_types.append(o())
        # Identifies to the executor, that this node has to be performed in the end
        self.is_final_node = is_final_node

        # The Visualization Type
        self.result_visualization_type = vis_type

        # Deprecated
        self.needs_project = needs_project

        # Identifies to the LoopNode, that this node has output fields which have to be
        # executed within the loop
        self.execute_output_fields_in_loop = execute_output_fields_in_loop

        # Identifies to the executor, that this node had been performed within a loop and thus has to be
        # skipped after the loop finished.
        self.is_in_loop_node = False

        # Indicates, that this node will be performed even if it has a result in cache (i.e. AggregationOperation)
        self.multi_execute = multi_execute
    def update_out_types(self, input_types):
        return [slot.data_type for slot in self.output_slots]

    def perform(self, args, progress_signal, project):
        self.result = [args]

    def get_input_types(self):
        return self.input_types

    def get_result(self):
        return self.result

    def handle_exception(self, exception):
        print("")
        print("Exception in Node")
        print(self.__class__.__name__)
        print(exception.message)
        print("")

    def reset_result(self):
        self.result = []


class ProjectOperation(Operation):
    on_modify_project = pyqtSignal(list)

    def __init__(self, name, input_types, output_types,
                 is_final_node = True, needs_project = False,
                 vis_type = VIS_TYPE_NONE, execute_output_fields_in_loop = True):

        super(ProjectOperation, self).__init__(name, input_types, output_types,
                 is_final_node, needs_project,
                 vis_type, execute_output_fields_in_loop)

    def perform_modify(self, args, progress_signal, project, modify_signal):
        try:
            self.on_modify_project.disconnect(modify_signal)
        except:
            pass
        self.on_modify_project.connect(modify_signal)


    def modify_project(self, project, args):
        """
        This function will be executed in the main-thread
        :param project: 
        :param args: 
        :return: 
        """
        pass


class OperationValue(Operation):
    def __init__(self, name, input, output):
        super(OperationValue, self).__init__( name, input, output)
        self.value = 100

    def perform(self, args, progress_signal, project):
        self.result = [self.value]


class OperationScalar(OperationValue):
    def __init__(self):
        super(OperationScalar, self).__init__("Scalar", [], [Slot("Value", DT_Numeric, 0)])


class OperationVector2(OperationValue):
    def __init__(self):
        super(OperationVector2, self).__init__("Vector2", [], [Slot("Value", DT_Vector2, [0,1])])

    def perform(self, args, progress_signal, project):
        self.result = [self.spin_box_1.value(), self.spin_box_2.value()]


#region InputNodes
class OperationFrameReader(Operation):
    def __init__(self):
        super(OperationFrameReader, self).__init__("Read Frame Movie", [Slot("Path", DT_Literal, "C:\\Users\\Gaudenz Halter\\Desktop\\Series_Movies\\input\\Frozen.mp4"), Slot("Frame Index", DT_Numeric, 3000)], [Slot("Frame", DT_Image, None)])

    def perform(self, args, progress_signal, project):
        try:
            progress_signal(0.0)
            cap = cv2.VideoCapture(args[0])
            cap.set(cv2.CAP_PROP_POS_FRAMES, args[1])
            self.onProgress.emit(0.5)
            ret, frame = cap.read()
            self.result = [frame]
            progress_signal(1.0)
            if frame is None:
                raise Exception("Frame returned None, couldn't read Movie")
        except Exception as e:
            self.handle_exception(e)


class OperationRangeReader(Operation):
    def __init__(self):
        super(OperationRangeReader, self).__init__("Read Range Movie",
                                                   [Slot("Path", DT_Literal, "C:\\Users\\Gaudenz Halter\\Desktop\\Series_Movies\\input\\Frozen.mp4"),
                                                    Slot("Start Index", DT_Numeric, 0),
                                                    Slot("End Index", DT_Numeric, 500)],
                                                   [Slot("Frame", DT_ImageStack, None)])

    def perform(self, args, progress_signal, project):
        try:

            start = args[1]
            end = args[2]

            cap = cv2.VideoCapture(args[0])

            if start >= end:
                end = cap.get(cv2.CAP_PROP_FRAME_COUNT)

            cap.set(cv2.CAP_PROP_POS_FRAMES, start)

            frame_stack = []
            for idx in range(start, end):
                self.onProgress.emit(float(idx - start + 1) / len(list(range(start, end))))
                ret, frame = cap.read()
                if frame  is None:
                    raise IOError("OperationRangeReader: OpenCV couldn't read frame")
                frame_stack.append(frame)

            self.result = [frame_stack]

            if frame_stack is None:
                raise Exception("Frame returned None, couldn't read Movie")
        except Exception as e:
            self.handle_exception(e)


class OperationRange(Operation):
    def __init__(self):
        super(OperationRange, self).__init__("Range Sequence",
                                                   [Slot("Start", DT_Numeric, 0), Slot("End", DT_Numeric, 10), Slot("Step", DT_Numeric, 1)],
                                                   [Slot("Range", DT_Vector, None)], vis_type=VIS_TYPE_NONE)

    def perform(self, args, progress_signal, project):
        self.result = [list(range(args[0], args[1], args[2]))]



class ProjectNode(Operation):
    def __init__(self):
        super(ProjectNode, self).__init__("Project",
                                                   [],
                                                   [Slot("MoviePath", DT_Literal,"C:\\Users\\Gaudenz Halter\\Desktop\\Series_Movies\\input\\Frozen.mp4"),
                                                    Slot("Movie Duration", DT_Numeric, 0),
                                                    Slot("Segments", DT_VectorArray, 0),
                                                    Slot("Annotation Layers", DT_VectorArray, 500),
                                                    ],
                                                    
                                          needs_project=True)


    def perform(self, args, progress_signal, project):
        self.result = [project.movie_descriptor.movie_path, project.movie_descriptor.duration, None]
    

#endregion

#region Computation

class OperationMean(Operation):
    def __init__(self):
        super(OperationMean, self).__init__("Mean", [
            Slot("Data", DT_Numeric, None),
            Slot("Axis", DT_Vector, [0, 1])],
                                            [Slot("Mean", DT_Numeric, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.onProgress.emit(0.0)
            axis = tuple(np.array(args[1]).astype(np.uint8).tolist())
            avg = np.mean(args[0], axis=axis)
            self.onProgress.emit(1.0)
            self.result = [avg]
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        # if isinstance(input_types[0], DT_ImageStack):
        #     self.output_types = [DT_Image]
        #
        # if isinstance(input_types[0], DT_Image):
        #     self.output_types = [DT_Vector3]

        return cast_numeric_axis_reduction([input_types[0]], input_types[1])


class OperationAdd(Operation):
    def __init__(self):
        super(OperationAdd, self).__init__("Addition", [Slot("a", DT_Numeric, 0), Slot("b", DT_Numeric, 0)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.onProgress.emit(0.0)
            sum = np.add(args[0], args[1])

            self.onProgress.emit(1.0)
            self.result = [sum]
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        return cast_numeric_output_type_highest(input_types)


class OperationSubtract(Operation):
    def __init__(self):
        super(OperationSubtract, self).__init__("Subtract", [Slot("a", DT_Numeric, 0), Slot("b", DT_Numeric, 0)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.onProgress.emit(0.0)
            subtract = np.subtract(args[0], args[1])
            self.result = [subtract]
            self.onProgress.emit(1.0)
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        return cast_numeric_output_type_highest(input_types)


class OperationMultiply(Operation):
    def __init__(self):
        super(OperationMultiply, self).__init__("Multiply", [Slot("a", DT_Numeric, 1), Slot("b", DT_Numeric, 1)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.onProgress.emit(0.0)
            subtract = np.multiply(args[0], args[1])
            self.result = [subtract]
            self.onProgress.emit(1.0)
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        self.output_types = cast_numeric_output_type_highest(input_types)
        return self.output_types


class OperationDivision(Operation):
    def __init__(self):
        super(OperationDivision, self).__init__("Division", [Slot("a", DT_Numeric, 1), Slot("b", DT_Numeric, 1)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.onProgress.emit(0.0)
            subtract = np.divide(args[0], args[1])
            self.result = [subtract]
            self.onProgress.emit(1.0)
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        return cast_numeric_output_type_highest(input_types)


class OperationNormalize(Operation):
    def __init__(self):
        super(OperationNormalize, self).__init__("Normalization", [Slot("In", DT_Numeric, None)], [Slot("Result", DT_Numeric, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.onProgress.emit(0.0)
            result = np.subtract(np.array(args[0]).astype(np.float64), np.amin(args[0]))
            result = np.multiply(np.divide(result, np.amax(result)), 255)
            self.onProgress.emit(1.0)
            self.result = [result]
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_types):
        input_types = [s.data_type() for s in input_types]
        self.output_types = [input_types[0].__class__]

        return self.output_types


class OperationResize(Operation):
    def __init__(self):
        super(OperationResize, self).__init__("Resize", [Slot("Image(s)", DT_ImageStack, None), Slot("New Dimensions", DT_Vector2, (512, 320))],
                                                 [Slot("Result", DT_ImageStack, None)])

    def perform(self, args, progress_signal, project):
        try:
            imgs = args[0]
            result = []
            if len(imgs.shape) == 4:
                for i in range(imgs.shape[0]):
                    self.onProgress.emit(imgs.shape[0]/i)
                    result.append(cv2.resize(imgs[i], (args[1][0], args[1][1]), interpolation=cv2.INTER_CUBIC))
            else:
                self.onProgress.emit(0.25)
                result = cv2.resize(imgs, (args[1][0], args[1][1]), interpolation=cv2.INTER_CUBIC)

            self.onProgress.emit(1.0)
            self.result = [np.array(result)]
        except Exception as e:
            self.handle_exception(e)

    def update_out_types(self, input_slots):
        input_types = [s.data_type() for s in input_slots]

        self.output_types = [input_types[0].__class__]

        return self.output_types


class OperationRandomInt(Operation):
    def __init__(self):
        super(OperationRandomInt, self).__init__("Random Numeric [Int]",
                                                   [Slot("Start", DT_Numeric, 0), Slot("End", DT_Numeric, 10)],
                                                   [Slot("Random", DT_Numeric, 0)], vis_type=VIS_TYPE_NONE)

    def perform(self, args, progress_signal, project):
        # print args
        self.result = [randint(int(args[0]), int(args[1]))]



#endregion

#region MISC
class OperationIterate(Operation):
    def __init__(self):
        super(OperationIterate, self).__init__("Iterate", [Slot("Iterable", DataType, None)],
                                              [Slot("Item", DataType, None), Slot("Finished", DT_Numeric, 0)])
        self.current_index = 0
        self.iterable_length = 0
        self.current_item = None

    def perform(self, args, progress_signal, project):

        try:
            iterable = np.array(args[0])
            self.iterable_length = iterable.shape[0]

            self.onProgress.emit(float(self.current_index) / self.iterable_length)


            if self.current_index < self.iterable_length - 1:
                self.current_item = iterable[self.current_index]
                self.result = [self.current_item, True]



            else:
                self.current_item = iterable[self.current_index]
                self.result = [self.current_item, False]

            self.current_index += 1


        except Exception as e:
            self.handle_exception(e)
            self.result = [None, False]

    def update_out_types(self, input_types):
        item_type = cast_numeric_axis_reduction(input_types, Slot("", DT_Vector, default_value=[0]))
        item_type.append(DataType)
        return item_type


class OperationAggregate(Operation):
    def __init__(self):
        super(OperationAggregate, self).__init__("Aggregate", [Slot("Item", DataType, None)],
                                               [Slot("Item", DataType, None)], execute_output_fields_in_loop=False, multi_execute=True)
        self.aggregation = []

    def perform(self, args, progress_signal, project):
        try:
            self.aggregation.append(args[0])
            self.result = [np.array(self.aggregation)]

        except Exception as e:
            self.handle_exception(e)
            self.result = [None, False]

    def update_out_types(self, input_types):
        item_type = cast_axis_extension(input_types)
        return item_type


class OperationPrintToConsole(Operation):
    def __init__(self):
        super(OperationPrintToConsole, self).__init__("Print", [Slot("Item", DataType, None)],
                                               [], is_final_node=True, vis_type=VIS_TYPE_NONE)

    def perform(self, args, progress_signal, project):

        try:
            print(args[0])

        except Exception as e:
            self.handle_exception(e)

#endregion

#region Visualization
class OperationShowImage(Operation):
    def __init__(self):
        super(OperationShowImage, self).__init__("Show Image", [Slot("Image", DT_Image, None)], [], is_final_node= True)

    def perform(self, args, progress_signal, project):
        try:
            img = np.array(np.clip(args[0], 0, 255)).astype(np.uint8)
            # qimage, qpixmap = numpy_to_qt_image(img)
            # cv2.imshow("ImShow Output", img)
            self.result = [img]

        except Exception as e:
            self.handle_exception(e)


class OperationColor2Image(Operation):
    def __init__(self):
        super(OperationColor2Image, self).__init__("Color -> Image", [Slot("Color", DT_Vector3, [0,0,0])], [Slot("Image", DT_Image, None)])

    def perform(self, args, progress_signal, project):
        try:
            data = np.zeros(shape=(500, 500, 3)).astype(np.uint8)
            data[:, :] = args[0]
            self.result = [data]
        except Exception as e:
            self.handle_exception(e)


class OperationColorHistogram(Operation):
    def __init__(self):
        super(OperationColorHistogram, self).__init__("Color Histogram", [Slot("Color", DT_ImageStack, None)], [Slot("Histogram", DT_Vector, None)])

    def perform(self, args, progress_signal, project):
        try:
            n_bins = 16
            range_min = 0
            range_max = 255

            imgs = np.array(args[0])

            hists = []
            if len(imgs.shape) == 3:
                imgs = np.array([imgs])

            for idx in range(imgs.shape[0]):
                img = imgs[idx]
                data = np.resize(img, (img.shape[0] * img.shape[1], 3))
                hist = cv2.calcHist([data[:, 0], data[:, 1], data[:, 2]], [0, 1, 2], None,
                                    [n_bins, n_bins, n_bins],
                                    [range_min, range_max, range_min, range_max,
                                     range_min, range_max])
                hists.append(hist)
            self.result = [hists]
        except Exception as e:
            self.handle_exception(e)


class OperationBarPlot(Operation):
    def __init__(self):
        super(OperationBarPlot, self).__init__("Bar Plot", [Slot("Values", DT_Vector, None)], [], is_final_node= True, vis_type=VIS_TYPE_WEB)

    def perform(self, args, progress_signal, project):
        try:
            # print args[0].shape
            # if not isinstance(args[0], list) or not isinstance(args[0], np.ndarray):
            #     y = np.array([args[0]])

            # y = args[0]
            #
            # plt.bar(range(y.shape[0]), y)
            # plt.show()
            plot = figure()
            plot.circle([1, 2], [3, 4])

            vis = layout([[plot]], sizing_mode="scale_width")

            html = file_html(vis, CDN, "my plot")
            self.result = [html]

        except Exception as e:
            self.handle_exception(e)


#endregion

#region ProjectModification
class OperationAddSegmentation(ProjectOperation):
    def __init__(self):
        super(OperationAddSegmentation, self).__init__(
            "Add Segmentation",
            [Slot("Name", DT_Literal, "New Segmentation"),
             Slot("Segments", DT_Segment, "New Segmentation")],
            [],
            is_final_node=True)
        self.value = 100

    def perform_modify(self, args, progress_signal, project, modify_signal):
        super(OperationAddSegmentation, self).perform_modify(args, progress_signal, project, modify_signal)
        self.on_modify_project.emit([self.modify_project, args])

    def modify_project(self,project, args):
        segmentation = project.create_segmentation(args[0])
        if len(np.array(args[1]).shape) == 1:
            segms = [args[1]]
        else:
            segms = args[1]

        for s in segms:
            segmentation.create_segment(int(s[1]), int(s[2]), s[0])


class OperationCreateSegment(Operation):
    def __init__(self):
        super(OperationCreateSegment, self).__init__("Create Segment",
                                                       [Slot("Name", DT_Literal, "New Segmentation"),
                                                        Slot("Start", DT_Numeric, 0),
                                                        Slot("End", DT_Numeric, 100)],
                                                     [Slot("Segment", DT_Segment, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.result = [[args[0],args[1],args[2]]]

        except Exception as e:
            self.handle_exception(e)


class OperationAddAnnotationLayer(ProjectOperation):
    def __init__(self):
        super(OperationAddAnnotationLayer, self).__init__(
            "Add Annotation Layer",
            [Slot("Name", DT_Literal, "New Segmentation"),
             Slot("Start", DT_Numeric, 0),
             Slot("End", DT_Numeric, 1000),
             Slot("Annotations", DT_Annotation, None)],
            [],
            is_final_node=True)
        self.value = 100

    def perform_modify(self, args, progress_signal, project, modify_signal):
        super(OperationAddAnnotationLayer, self).perform_modify(args, progress_signal, project, modify_signal)
        self.on_modify_project.emit([self.modify_project, args])

    def modify_project(self, project, args):
        name = args[0]
        start = args[1]
        end = args[2]
        layer = project.create_annotation_layer(name, start, end)

        print(isinstance(args[3][0], list))

        if not isinstance(args[3][0], list):
            annotations = [args[3]]
        else:
            annotations = args[3]

        for a in annotations:
            name = a[0]
            pos = a[1]
            size = a[2]
            annotation = layer.create_annotation(type = AnnotationType.Rectangle, position = pos, size=size, color = (255,255,255), line_width = 5, name = name)
            layer.add_annotation(annotation)






class OperationCreateAnnotation(Operation):
    def __init__(self):
        super(OperationCreateAnnotation, self).__init__("Create Annotation",
                                                     [Slot("Name", DT_Literal, "New Segmentation"),
                                                      Slot("Position", DT_Vector2, (0,0)),
                                                      Slot("Size", DT_Vector2, (50, 50))],
                                                     [Slot("Segment", DT_Annotation, None)])

    def perform(self, args, progress_signal, project):
        try:
            self.result = [[args[0], args[1], args[2]]]

        except Exception as e:
            self.handle_exception(e)


#endregion











""