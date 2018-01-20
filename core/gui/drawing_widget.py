import os

import cv2
import numpy as np
from functools import partial
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QToolBar, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QFont

from core.data.computation import *
from core.data.containers import AnnotationLayer, Annotation
from core.data.enums import *
from core.gui.perspectives import Perspective
from core.data.interfaces import IProjectChangeNotify, ITimeStepDepending, IConcurrentJob
from core.gui.color_palette import ColorSelector
from core.gui.context_menu import open_context_menu

from core.concurrent.worker import LiveWidgetThreadWorker, run_minimal_worker
from .ewidgetbase import EDockWidget, EToolBar


ALWAYS_VLC = 0
ALWAYS_OPENCV = 1
TIMELINE_SCALE_DEPENDENT = 2

class AnnotationToolbar(EToolBar):
    def __init__(self, main_window, drawing_widget):
        super(AnnotationToolbar, self).__init__(main_window, "Annotation Toolbar")
        self.drawing_widget = drawing_widget
        self.color_picker = ColorSelector(self, main_window.settings)

        self.action_rect = self.addAction(create_icon("qt_ui/icons/icon_rectangle.png"), "")
        self.action_ellipse = self.addAction(create_icon("qt_ui/icons/icon_ellipse.png"), "")
        self.action_text = self.addAction(create_icon("qt_ui/icons/icon_text.png"), "")
        self.action_image = self.addAction(create_icon("qt_ui/icons/icon_image.png"), "")
        self.action_freehand = self.addAction(create_icon("qt_ui/icons/icon_freehand.png"), "")
        self.action_test = self.addAction("Test")
        self.addWidget(self.color_picker)

        self.setIconSize(QtCore.QSize(64,64))


        self.action_rect.triggered.connect(self.on_rectangle)
        self.action_ellipse.triggered.connect(self.on_ellipse)
        self.action_text.triggered.connect(self.on_text)
        self.action_image.triggered.connect(self.on_image)
        self.action_test.triggered.connect(self.main_window.test_function)
        self.action_freehand.triggered.connect(self.on_freehand)

        self.spinBox_LineThickness = QtWidgets.QSpinBox(self)
        self.spinBox_LineThickness.setValue(5)
        self.spinBox_FontSize = QtWidgets.QSpinBox(self)
        self.spinBox_FontSize.setValue(12)


        w_font_size = QWidget()
        w_line_width = QWidget()
        w_font_size.setLayout(QHBoxLayout())
        w_line_width.setLayout(QHBoxLayout())

        widget = QWidget(self)
        widget.setLayout(QVBoxLayout(widget))
        w_line_width.layout().addWidget(QLabel("Line Width:"))
        w_line_width.layout().addWidget(self.spinBox_LineThickness)

        w_font_size.layout().addWidget(QLabel("Font Size:"))
        w_font_size.layout().addWidget(self.spinBox_FontSize)
        widget.layout().addWidget(w_font_size)
        widget.layout().addWidget(w_line_width)
        self.addWidget(widget)


        self.current_color = (0, 0, 0)
        self.line_width = 5


        self.color_picker.on_selection.connect(self.on_color_change)
        self.spinBox_LineThickness.valueChanged.connect(self.on_line_width_change)


    #region Events
    def on_color_change(self, color):
        self.current_color = color

    def on_line_width_change(self):
        self.line_width = self.spinBox_LineThickness.value()

    def on_rectangle(self):
        self.drawing_widget.create_rectangle(self.current_color, self.spinBox_LineThickness.value())

    def on_ellipse(self):
        self.drawing_widget.create_ellipse(self.current_color, self.spinBox_LineThickness.value())

    def on_text(self):
        self.drawing_widget.create_text(self.current_color, self.spinBox_LineThickness.value(),
                                        self.spinBox_FontSize.value())

    def on_line(self):
        pass

    def on_image(self):
        image_path = QFileDialog.getOpenFileUrl()[0].url()
        image_path = parse_file_path(image_path)
        self.drawing_widget.create_image(image_path)

    def on_freehand(self):
        freehand = self.drawing_widget.create_freehand(self.current_color, self.spinBox_LineThickness.value())

    def on_arrow(self):
        self.main_window.test_function()

    pass
    #endregion


class DrawingOverlay(QtWidgets.QMainWindow, IProjectChangeNotify, ITimeStepDepending):
    """
    Implements IProjectChangeNotify
    """

    onSourceChanged = pyqtSignal(str)

    def __init__(self, main_window, videoframe, project):
        super(DrawingOverlay, self).__init__(main_window)
        path = os.path.abspath("qt_ui/DrawingWidget.ui")
        uic.loadUi(path, self)
        self.main_window = main_window

        self.settings = main_window.settings
        self.videoframe = videoframe
        self.initUI()
        self.project = project
        self.current_time = 0

        self.selected = []
        self.current_key_tuple = None
        self.widgets = []
        self.is_freehand_drawing = False
        self.multi_selection = False

        self.opencv_pixmap = None
        self.videoCap = None
        self.opencv_image_visible = False
        self.current_opencv_frame_index = 0

        self.show_annotations = True



        self.show()

        self.main_window.onTimeStep.connect(self.on_timestep_update)
        self.main_window.player.started.connect(partial(self.on_opencv_frame_visibilty_changed, False))
        self.main_window.onOpenCVFrameVisibilityChanged.connect(self.on_opencv_frame_visibilty_changed)
        self.main_window.frame_update_worker.signals.onOpenCVFrameUpdate.connect(self.assign_opencv_image)



    def on_loaded(self, project):
        self.cleanup()
        self.project = project
        # try:
        #     if self.videoCap:
        #         self.videoCap.release()
        #         self.videoCap = None
        #
        #     self.videoCap = cv2.VideoCapture(self.project.movie_descriptor.movie_path)
        # except Exception as e:
        #     print(e, "OpenCV Error: ", self.project.movie_descriptor.movie_path)
        if len(self.project.get_annotation_layers()) > 0:
            for l in self.project.get_annotation_layers():
                for a in l.annotations:
                    if a.widget is None:
                        self.create_drawing_widget(a)
                        a.widget.is_active = False

            self.set_current_layer(len(self.project.get_annotation_layers()) - 1)
            self.update_annotation_widgets()

    def on_changed(self, project, item):
        if len(self.project.get_annotation_layers()) > 0:

            for l in self.project.get_annotation_layers():
                for a in l.annotations:
                    if a.widget is None:
                        self.create_drawing_widget(a)
                        a.widget.is_active = False
                        self.widgets.append(a.widget)

            # self.set_current_layer(len(self.project.get_annotation_layers()) - 1)
            self.update_annotation_widgets()

    def on_selected(self, sender, selected):
        if sender is self:
            return
        self.abort_freehand_drawing()

        if not self.multi_selection:
            for sel in self.selected:
                if sel.get_type() == ANNOTATION:
                    sel.widget.is_selected = False

            self.selected = []

        for sel in selected:
            if sel.get_type() == ANNOTATION:
                sel.widget.is_selected = True
            self.selected.append(sel)

    def create_annotation_layer(self,name, t_start, t_end):
        layer = AnnotationLayer(name, t_start, t_end)
        self.project.add_annotation_layer(layer)
        self.set_current_layer(len(self.project.get_annotation_layers())-1)

    def set_current_layer(self, index):
        if index < len(self.project.get_annotation_layers()):

            # If there is already a Layer active, hide it
            # if self.project.current_annotation_layer is not None:
            #     for a in self.project.current_annotation_layer.annotations:
            #         a.widget.is_active = False

            # set the new layer as the current layer
            self.project.current_annotation_layer = self.project.get_annotation_layers()[index]
            for i,l in enumerate(self.project.get_annotation_layers()):
                if i == index:
                    l.set_is_current_layer(True)
                else:
                    l.set_is_current_layer(False)

            # Make the new Layer Visible
            for a in self.project.current_annotation_layer.annotations:
                a.widget.is_active = True

            # self.main_window.annotation_viewer.expand_layer(index)

            self.main_window.player.pause()
            # self.main_window.player.set_media_time(self.project.current_annotation_layer.t_start)

            self.update()

    def remove_annotation_layer(self):
        if self.project.current_annotation_layer is not None:
            for a in self.project.current_annotation_layer.annotations:
                a.widget.close()
                a.widget.deleteLater()
            self.project.remove_annotation_layer(self.project.current_annotation_layer)
        if len(self.project.get_annotation_layers()) > 0:
            self.project.current_annotation_layer = self.project.get_annotation_layers()[len(self.project.get_annotation_layers())-1]
        else:
            self.project.current_annotation_layer = None
        self.cleanup()

    def create_rectangle(self, color = None, line = None, start = None, end = None):
        if start == None:
            start = self.current_time

        if end == None:
            end = start + 1000

        if color == None:
            color = (200, 200, 200)

        if line == None:
            line = 5

        if self.project.current_annotation_layer is not None:
            rectangle = Annotation(AnnotationType.Rectangle,
                                   size=(150,150),
                                   color=color,
                                   line_w=line,
                                   name="New Rectangle",
                                   t_start=start, t_end=end)
            self.project.current_annotation_layer.add_annotation(rectangle)
            rectangle.set_project(self.project)
            # self.main_window.annotation_viewer.update_list()
            self.update_annotation_widgets()
            rectangle.widget.select()

    def create_ellipse(self, color = None, line= None, start = None, end = None):
        if start == None:
            start = self.current_time
        if end == None:
            end = start + 1000

        if color == None:
            color = (200, 200, 200)
        if line == None:
            line = 5

        if self.project.current_annotation_layer is not None:
            ellipse = Annotation(AnnotationType.Ellipse, (150, 150), color=color, line_w=line, name="New Ellipse",
                                 t_start = start, t_end = end)
            ellipse.set_project(self.project)
            self.project.current_annotation_layer.add_annotation(ellipse)
            # self.main_window.annotation_viewer.update_list()
            self.update_annotation_widgets()
            ellipse.widget.select()

    def create_text(self, color= None, line = None, font_size = None, start = None, end = None):
        if start == None:
            start = self.current_time
        if end == None:
            end = start + 1000

        if color == None:
            color = (200, 200, 200)
        if font_size == None:
            font_size = 12
        if line == None:
            line = 5

        if self.project.current_annotation_layer is not None:
            a_text = Annotation(AnnotationType.Text, (200, 200), color=color, line_w=line,
                                text="^This is some sample text", name="New Text",
                                t_start=start, t_end=end)
            a_text.set_project(self.project)
            self.project.current_annotation_layer.add_annotation(a_text)
            # self.main_window.annotation_viewer.update_list()
            self.update_annotation_widgets()
            a_text.widget.select()

    def create_image(self, image_path = None, start = None, end = None):
        if start == None:
            start = self.current_time
        if end == None:
            end = start + 1000

        if image_path == None:
            image_path = QFileDialog.getOpenFileUrl()[0].url()
            image_path = parse_file_path(image_path)

        if self.project.current_annotation_layer is not None:
            image_path = str(image_path)
            print (image_path)
            img = cv2.imread(image_path)
            if img is None:
                self.main_window.print_message("Error occured when reading the image", "Red")
                return

            image_size = (img.shape[1], img.shape[0])
            a_image = Annotation(AnnotationType.Image, image_size, resource_path=image_path, name="New Image",
                                 t_start=start, t_end=end)
            a_image.set_project(self.project)
            self.project.current_annotation_layer.add_annotation(a_image)
            self.update_annotation_widgets()
            a_image.widget.select()

    def create_freehand(self, color = None, line = None, start = None, end = None):
        if start == None:
            start = self.current_time
        if end == None:
            end = start + 1000

        if color == None:
            color = (200, 200, 200)

        if line == None:
            line = 5

        if self.project.current_annotation_layer is not None:
            a_hand = Annotation(AnnotationType.FreeHand, (200, 200), color=color, line_w=line, name= "New FreeHand",
                                t_start=start, t_end=end)
            a_hand.set_project(self.project)
            self.project.current_annotation_layer.add_annotation(a_hand)
            # self.main_window.annotation_viewer.update_list()
            self.update_annotation_widgets()
            a_hand.widget.select()

    def remove_drawing(self, drawing):
        self.project.current_annotation_layer.annotations.remove(drawing)
        # self.main_window.annotation_viewer.update_list()
        self.a_widgets.remove(drawing)
        drawing.deleteLater()

    def cleanup(self):
        children = self.children()
        for c in children:
            if isinstance(c, DrawingBase):
                c.deleteLater()

    def render_annotation(self, frame, target_width = 1920):
        """
        Rendering is currently done by resizing the DrawingWidget to the size of the movie, 
        make a snapshot of it, and overlaying it to the Screenshot of the movie
        :return: 
        """

        movie_w = self.main_window.player.get_source_width()
        movie_h = self.main_window.player.get_source_height()

        scale = float(target_width) / movie_w

        final_w = int(scale * movie_w)
        final_h = int(scale * movie_h)

        frame = cv2.resize(frame,(final_w, final_h), interpolation=cv2.INTER_CUBIC)


        if self.project.current_annotation_layer is None:
            self.main_window.print_message("No Annotation Layer created yet", "red")
            return None, frame
        if len(self.project.current_annotation_layer.annotations) == 0:
            self.main_window.print_message("No Annotations found", "red")
            return None, frame

        w = final_w
        h = final_h

        qimage = QtGui.QImage(QtCore.QSize(final_w, final_h), QtGui.QImage.Format_ARGB32_Premultiplied)
        qimage.fill(QtCore.Qt.transparent)
        qp = QtGui.QPainter(qimage)

        for a in self.project.current_annotation_layer.annotations:
            offset = a.get_position()
            x = offset.x() * scale
            y = offset.y() * scale

            size = a.get_size()
            width = size[0] * scale
            height = size[1] * scale

            offset = QtCore.QPoint(int(x), int(y))
            size = QtCore.QSize(int(width), int(height))
            a.widget.renderDrawing(qp, offset, size)

        qp.end()

        return qimage, frame

    def initUI(self):
        self.setWindowFlags(Qt.Tool|Qt.CustomizeWindowHint|Qt.FramelessWindowHint|Qt.NoDropShadowWindowHint)#|Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background: transparent;")
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_MacNoShadow)

    def update_annotation_widgets(self):
        if self.project.current_annotation_layer is None:
            return

        for a in self.project.current_annotation_layer.annotations:
            if a.widget is None:
                self.create_drawing_widget(a)
                a.widget.is_active = True
        for l in self.project.annotation_layers:
            if l.is_visible is True:
                for a in l.annotations:
                    if a.widget is None:
                        self.create_drawing_widget(a)
                        a.widget.is_active = True
                    else:
                        a.widget.is_active = True

    def create_drawing_widget(self, annotation):

        if annotation.a_type == AnnotationType.Rectangle:
            rect = DrawingRectangle(self.centralWidget(), annotation)
            rect.move(annotation.get_position())
            annotation.widget = rect
            return

        if annotation.a_type == AnnotationType.Ellipse:
            ellipse = DrawingEllipse(self.centralWidget(), annotation)
            ellipse.move(annotation.get_position())
            annotation.widget = ellipse
            return

        if annotation.a_type == AnnotationType.Text:
            text = DrawingText(self.centralWidget(), annotation)
            text.move(annotation.get_position())
            text.set_text(annotation.text)
            annotation.widget = text
            return

        if annotation.a_type == AnnotationType.Image:
            image = DrawingImage(self.centralWidget(), annotation)
            image.move(annotation.get_position())
            annotation.widget = image
            return

        if annotation.a_type == AnnotationType.FreeHand:
            hand = DrawingFreeHand(self.centralWidget(), annotation)
            hand.move(annotation.get_position())
            annotation.widget = hand
            return

    def abort_freehand_drawing(self):
        for s in self.selected:
            if s.get_type() == ANNOTATION:
                if isinstance(s.widget, DrawingFreeHand):
                    s.widget.abort_drawing()

        if self.is_freehand_drawing:
            self.main_window.annotation_toolbar.show_indicator(False)
            self.is_freehand_drawing = False

    def update(self):
        if self.isVisible():
            if self.main_window.current_perspective == Perspective.Segmentation:
                self.show_annotations = False
            else:
                self.show_annotations = True

            super(DrawingOverlay, self).update()
            # self.synchronize_transforms()

    def set_input_transparent(self, transparent):
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents,transparent)

    def paintEvent(self, e):
        self.synchronize_transforms()
        if not self.main_window.player.is_playing():
            qp = QtGui.QPainter()
            pen = QtGui.QPen()
            pen.setWidth(4)
            pen.setColor(QtGui.QColor(255,100,100))

            qp.begin(self)
            qp.setPen(pen)
            qp.fillRect(self.rect(), QtGui.QColor(0,0,0,1))
            if self.opencv_pixmap is not None and self.opencv_image_visible:
                qp.drawPixmap(self.rect(), self.opencv_pixmap)
                pen.setWidth(1)

                pen.setColor(QtGui.QColor(105,143,63))
                qp.setPen(pen)
                qp.drawText(QtCore.QRect(self.width() - 100, self.height() - 50, 100, 50), 12, "OpenCV")

            qp.end()
        else:
            qp = QtGui.QPainter()
            pen = QtGui.QPen()
            pen.setWidth(1)
            pen.setColor(QtGui.QColor(255, 100, 100))

            qp.begin(self)
            qp.setPen(pen)
            qp.drawRect(QtCore.QRect(self.rect().x(), self.rect().y(), self.rect().width()-1, self.rect().height()-1))
            qp.end()

    def on_opencv_frame_visibilty_changed(self, visibility):
        if visibility:
            if not self.settings.OPENCV_PER_FRAME == ALWAYS_VLC:
                if self.opencv_image_visible == False:
                    self.opencv_image_visible = True
                    self.update()
                self.onSourceChanged.emit("OPENCV")
        else:
            if self.opencv_image_visible == True:
                self.opencv_image_visible = False
                self.update()
            self.onSourceChanged.emit("VLC")

    def synchronize_transforms(self):
        # old_size = self.size()

        s = self.main_window.player.movie_size
        # aspect =self.main_window.player.get_aspect_ratio()


        if s[0] == 0 or s[1] == 0:
            return

        m_width = float(s[0])
        m_height = float(s[1])

        f_width = float(self.videoframe.width())
        f_height = float(self.videoframe.height())

        if f_width <= 0 or f_height <= 0:
            f_width = 1
            f_height = 1
        # if the Movie is clamped by the Width of the MovieFrame
        if (m_height/m_width) < (f_height/f_width):
            x_offset = 0
            y_offset = (f_height/2) - ((f_width * (m_height/m_width))/2)
            x_size = f_width
            y_size = f_width * (m_height/m_width)

        else:
            x_offset = (f_width/2) - ((f_height * (m_width/m_height))/2)
            y_offset = 0
            x_size = f_height * (m_width/m_height)
            y_size = f_height

        location = self.videoframe.mapToGlobal(QtCore.QPoint(x_offset,y_offset))
        x = x_size
        y = y_size

        scale = float(x_size) / m_width

        self.move(location)
        self.setFixedSize(x,y)

        if self.show_annotations:
            for n in self.project.get_annotation_layers():
                for m in n.annotations:
                    m.widget.scale = scale
                    m.widget.interpolate_location()
                    m.widget.update()
        else:
            for n in self.project.get_annotation_layers():
                for m in n.annotations:
                    m.widget.hide()

    def drawLines(self, qp):
        pen = QtGui.QPen(QtCore.Qt.black, 2, QtCore.Qt.SolidLine)

        qp.setPen(pen)
        qp.drawLine(20, 40, 250, 40)

        pen.setStyle(QtCore.Qt.DashLine)
        qp.setPen(pen)
        qp.drawLine(20, 80, 250, 80)

        pen.setStyle(QtCore.Qt.DashDotLine)
        qp.setPen(pen)
        qp.drawLine(20, 120, 250, 120)

        pen.setStyle(QtCore.Qt.DotLine)
        qp.setPen(pen)
        qp.drawLine(20, 160, 250, 160)

        pen.setStyle(QtCore.Qt.DashDotDotLine)
        qp.setPen(pen)
        qp.drawLine(20, 200, 250, 200)

        pen.setStyle(QtCore.Qt.CustomDashLine)
        pen.setDashPattern([1, 4, 5, 4])
        qp.setPen(pen)
        qp.drawLine(20, 240, 250, 240)

    def eventFilter(self, QObject, QEvent):
        return super(DrawingOverlay, self).eventFilter(QObject, QEvent)

    def mousePressEvent(self, event):
        self.project.set_selected(None, [])
        self.main_window.mousePressEvent(event)
        self.abort_freehand_drawing()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.multi_selection = True

        self.main_window.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Shift:
            self.multi_selection = False

    def on_timestep_update(self, time):
        self.current_time = time

    def assign_opencv_image(self, qpixmap):
        self.opencv_pixmap = qpixmap.scaled(self.size(), Qt.KeepAspectRatio)
        self.update()


class DrawingBase(QtWidgets.QWidget):
    def __init__(self, parent, annotation_object):
        super(DrawingBase, self).__init__(parent)
        self.annotation_object = annotation_object
        # self.annotation_viewer = parent.parent().main_window.annotation_viewer
        self.overlay = parent.parent()
        self.is_selected = False
        self.is_currently_moved = False
        self.inner_rect_delta = 10
        self.inner_rect = None
        self.min_size = 50
        self.time_last_updated = 0
        self.offset = QtCore.QPoint(0,0)

        # The current color, this can be set for instance if a drawing is selected
        self.curr_col = annotation_object.get_color()


        # The thickness color, this can be set for instance if a drawing is selected
        self.curr_line_thickness = annotation_object.line_w

        # The scale referres to how the widgets are scaled according to the current screen size
        # so that they are kept on the relative location
        self.scale = 1.0
        self.setMouseTracking(True)
        self.current_handle = "Center"
        self.executed_handle = None
        self.calc_inner_rect()
        self.show()

    def calc_inner_rect(self):
        s = self.rect()
        l = self.curr_line_thickness
        self.inner_rect = QtCore.QRect(s.x() + l + (self.inner_rect_delta * self.scale),
                                       s.y() + l + self.inner_rect_delta  * self.scale,
                                       s.width() - 2 * l - 2 * self.inner_rect_delta  * self.scale ,
                                       s.height() - 2 * l - 2 * self.inner_rect_delta  * self.scale)

    def set_location(self, location):
        self.annotation_object.set_position(location)
        self.move(location)

    def set_size(self, height, width):
        self.annotation_object.set_size(height, width)
        self.resize(height, width)

    def createPainter(self):
        self.curr_col = self.annotation_object.get_color()
        self.curr_line_thickness = self.annotation_object.line_w
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)

        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setColor(self.curr_col)
        pen.setWidth(self.curr_line_thickness)
        qp.setPen(pen)

        return qp

    def paintEvent(self, QPaintEvent):
        if self.is_active:

            self.draw_selection_frame()
            self.calc_inner_rect()

            qp = self.createPainter()
            self.drawShape(qp)
            qp.end()

    def drawShape(self, qp, rect = None):
        print("not Implemented")

    def renderDrawing(self,qp, offset, size, scale = 1.0):

        pen = QtGui.QPen()
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setColor(self.curr_col)
        pen.setWidth(self.curr_line_thickness * scale)
        qp.setPen(pen)

        x = offset.x() + self.inner_rect.x()
        y = offset.y() + self.inner_rect.y()
        # w = self.inner_rect.width()
        # h = self.inner_rect.height()
        w = size.width() - 2 * self.inner_rect_delta
        h = size.height() - 2 * self.inner_rect_delta
        local_rect = QtCore.QRect(x, y, w, h)

        self.drawShape(qp, local_rect)

    def draw_selection_frame(self):
        if self.is_selected:
            s = self.rect()
            qp = QtGui.QPainter()
            pen = QtGui.QPen()

            qp.begin(self)
            qp.setRenderHint(QtGui.QPainter.Antialiasing)
            pen.setColor(QtGui.QColor(200,200,200))
            pen.setWidth(2)
            pen.setStyle(QtCore.Qt.DashDotDotLine)
            pen.setJoinStyle(Qt.BevelJoin)
            pen.setCapStyle(Qt.RoundCap)
            qp.setPen(pen)

            qp.drawRect(QtCore.QRect(s.x(), s.y(), s.width(), s.height()))

            qp.fillRect(QtCore.QRect(s.x(), s.y(), s.width(), s.height()),  QtGui.QBrush(QtGui.QColor(255, 255, 255, 20)))

            # handle_color = QtGui.QColor(255, 160, 74, 100)
            handle_color = QtGui.QBrush(QtGui.QColor(255, 255, 255, 120))


            border_size = 0.025
            corner_size = 0.1

            border_h = np.clip(border_size * s.width(), 5, 1)
            border_v = np.clip(border_size * s.height(), 5, 1)
            corner = np.clip(corner_size * s.width(),20,20)


            # Draw the current Handle
            handle_rect = QtCore.QRect(np.clip(s.x() + s.width() * 0.4, 20, None),
                                       np.clip(s.y() + s.height() * 0.4,20, None),
                                               np.clip(s.width() * 0.2,20, None),
                                                       np.clip(s.height() * 0.2, 20, None))
            if self.current_handle == "UpperRightCorner":
                handle_rect = QtCore.QRect(s.x() + s.width() - corner,
                                         s.y(),
                                         corner,
                                         corner)

            if self.current_handle == "LowerRightCorner":
                handle_rect = QtCore.QRect(s.x() + s.width() - corner,
                                         s.y() + s.height() - corner,
                                         corner,
                                         corner)

            if self.current_handle == "LowerLeftCorner":
                handle_rect = QtCore.QRect(s.x(),
                                         s.y() + s.height() - corner,
                                         corner,
                                         corner)

            if self.current_handle == "UpperLeftCorner":
                handle_rect = QtCore.QRect(s.x(),
                                         s.y(),
                                         corner,
                                         corner)

            if self.current_handle == "UpperBorder":
                handle_rect = QtCore.QRect(s.x(),
                                         s.y(),
                                        s.width(),
                                         border_v)

            if self.current_handle == "RightBorder":
                handle_rect = QtCore.QRect(s.x() + s.width() - border_h,
                                           s.y(),
                                           border_h,
                                           s.height())

            if self.current_handle == "LowerBorder":
                handle_rect = QtCore.QRect(s.x(),
                                           s.y() + (s.height()- border_v),
                                           s.width(),
                                           border_v)

            if self.current_handle == "LeftBorder":
                handle_rect = QtCore.QRect(s.x(),
                                           s.y(),
                                           border_h,
                                           s.height())




            qp.fillRect(handle_rect, handle_color)
            qp.end()
        else:
            s = self.rect()
            qp = QtGui.QPainter()
            pen = QtGui.QPen()

            qp.begin(self)
            qp.setRenderHint(QtGui.QPainter.Antialiasing)
            pen.setColor(QtGui.QColor(200, 200, 200))
            pen.setWidth(2)
            pen.setStyle(QtCore.Qt.DashDotDotLine)
            pen.setJoinStyle(Qt.BevelJoin)
            pen.setCapStyle(Qt.RoundCap)
            qp.setPen(pen)
            qp.fillRect(QtCore.QRect(s.x(), s.y(), s.width(), s.height()),
                        QtGui.QBrush(QtGui.QColor(255, 255, 255, 1)))
            qp.end()

    def interpolate_location(self):
        if self.overlay.current_time != self.time_last_updated:
                self.time_last_updated = self.overlay.current_time
        else:
            return

        if self.annotation_object.has_key:
            time = self.overlay.current_time
            key = self.annotation_object.keys
            if len(key) < 2:
                return
            # If the current time is before the first key, set it as current location
            if time <= key[0][0]:
                self.annotation_object.orig_position = (key[0][1][0], key[0][1][1])
                return

            # If the current time is after the last key, set it as current location
            if time >= key[len(key) - 1][0]:
                self.annotation_object.orig_position = (key[len(key)-1][1][0], key[len(key)-1][1][1])
                return

            else:
                low, high = 0, 0
                for i in range(len(key) - 1):
                    low = key[i]
                    high = key[i + 1]
                    if low[0] <= time < high[0]:
                        break

                path = QtGui.QPainterPath()
                path.moveTo(QtCore.QPoint(low[1][0], low[1][1]))
                path.lineTo(QtCore.QPoint(high[1][0], high[1][1]))

                delta_time = high[0] - low[0]
                percent = float(time - low[0]) / delta_time
                point = path.pointAtPercent(percent)

                self.annotation_object.orig_position = (point.x(), point.y())

    def move_widget(self):
        xpos = int(float(self.annotation_object.orig_position[0]) * self.scale)
        ypos = int(float(self.annotation_object.orig_position[1]) * self.scale)
        pos_scaled = QtCore.QPoint(xpos, ypos)
        self.move(pos_scaled)

    def scale_widget(self):
        x = self.annotation_object.size[0] * self.scale
        y = self.annotation_object.size[1] * self.scale
        self.resize(x, y)

    def mousePressEvent(self, QMouseEvent):
        if self.is_active and not self.overlay.main_window.player.is_playing():
            if QMouseEvent.button() == Qt.LeftButton:
                self.curr_loc = self.pos() / self.scale
                self.offset = QMouseEvent.pos()
                self.curr_size = self.size().width(), self.size().height()
                self.old_pos = self.annotation_object.orig_position
                self.old_size = self.annotation_object.size
                self.select()
                self.executed_handle = self.current_handle
                return
            if QMouseEvent.button() == Qt.RightButton:
                open_context_menu(self.overlay.main_window, self.mapToGlobal(QMouseEvent.pos()), [self.annotation_object], self.overlay.project)

    def select(self, dispatch = True):
        self.is_selected = True
        self.raise_()


        if dispatch:
            self.overlay.project.set_selected(None, self.annotation_object)


    def mouseReleaseEvent(self, QMouseEvent):
        if self.is_active and not self.overlay.main_window.player.is_playing():
            self.annotation_object.transform(self.annotation_object.size,self.annotation_object.orig_position, self.old_pos, self.old_size)
            self.executed_handle = None

    def mouseMoveEvent(self, QMouseEvent):
        if not self.is_active or self.overlay.main_window.player.is_playing():
            return

        self.current_handle = get_mouse_handle_by_location(QMouseEvent.pos(), self.rect(),0.2,0.2)
        if QMouseEvent.buttons() & Qt.LeftButton:
            if self.executed_handle == "Center":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale
                self.annotation_object.orig_position = (target.x(), target.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "LowerRightCorner":
                delta = self.mapToParent(QMouseEvent.pos() - self.offset) / self.scale
                x = delta.x() - self.pos().x() / self.scale + self.curr_size[0] / self.scale
                y = delta.y() - self.pos().y() / self.scale + self.curr_size[1] / self.scale

                self.annotation_object.size = (np.clip(x, self.min_size , None), np.clip(y, self.min_size , None))
                self.scale_widget()
                self.move_widget()
                return

            if self.executed_handle == "UpperLeftCorner":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale

                delta = target - (self.curr_loc)
                x = self.curr_size[0] / self.scale - delta.x()
                y = self.curr_size[1] / self.scale - delta.y()

                self.annotation_object.size = (np.clip(x, self.min_size , None), np.clip(y, self.min_size , None))
                self.annotation_object.orig_position = (target.x(), target.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "UpperRightCorner":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale

                delta = target - (self.curr_loc)
                x = self.curr_size[0] / self.scale + delta.x()
                y = self.curr_size[1] / self.scale - delta.y()

                self.annotation_object.size = (np.clip(x, self.min_size, None), np.clip(y, self.min_size, None))
                self.annotation_object.orig_position = (self.curr_loc.x(), target.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "LowerLeftCorner":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale


                delta = target - self.curr_loc
                x = self.curr_size[0] / self.scale - delta.x()
                y = self.curr_size[1] / self.scale + delta.y()

                loc_x = np.clip(target.x(),None,  self.curr_loc.x() + self.curr_size[0] / self.scale - self.min_size)

                self.annotation_object.size = (np.clip(x, self.min_size, None), np.clip(y, self.min_size, None))
                self.annotation_object.orig_position = (loc_x, self.curr_loc.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "LeftBorder":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale


                delta = target - self.curr_loc
                x = self.curr_size[0] / self.scale - delta.x()
                y = self.curr_size[1] / self.scale + delta.y()

                loc_x = np.clip(target.x(), None, self.curr_loc.x() + self.curr_size[0] / self.scale - self.min_size)

                self.annotation_object.size = (np.clip(x, self.min_size, None), np.clip(self.curr_size[1] / self.scale, self.min_size, None))
                self.annotation_object.orig_position = (loc_x, self.curr_loc.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "RightBorder":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale


                delta = target - self.curr_loc
                x = self.curr_size[0] / self.scale + delta.x()
                y = self.curr_size[1] / self.scale + delta.y()

                self.annotation_object.size = (np.clip(x, self.min_size, None), np.clip(self.curr_size[1] / self.scale, self.min_size, None))
                self.annotation_object.orig_position = (self.curr_loc.x(), self.curr_loc.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "UpperBorder":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale


                delta = target - self.curr_loc
                x = self.curr_size[0] / self.scale + delta.x()
                y = self.curr_size[1] / self.scale - delta.y()

                self.annotation_object.size = (np.clip(self.curr_size[0] / self.scale, self.min_size, None), np.clip(y, self.min_size, None))
                self.annotation_object.orig_position = (self.curr_loc.x(), target.y())
                self.move_widget()
                self.scale_widget()
                return

            if self.executed_handle == "LowerBorder":
                pos = (QMouseEvent.pos() - self.offset)
                target = self.mapToParent(pos) / self.scale

                delta = target - self.curr_loc
                x = self.curr_size[0] / self.scale + delta.x()
                y = self.curr_size[1] / self.scale + delta.y()

                self.annotation_object.size = (np.clip(self.curr_size[0] / self.scale, self.min_size, None),
                                                np.clip(y, self.min_size, None))
                self.annotation_object.orig_position = (self.curr_loc.x(), self.curr_loc.y())
                self.move_widget()
                self.scale_widget()
                return

        if QMouseEvent.buttons() & Qt.RightButton:
            delta = self.mapToParent(QMouseEvent.pos() - self.offset) / self.scale
            x = delta.x() - self.pos().x() / self.scale + self.curr_size[0] / self.scale
            y = delta.y() - self.pos().y() / self.scale + self.curr_size[1] / self.scale
            self.annotation_object.set_size(np.clip(x,20,None), np.clip(y,20,None))
            self.scale_widget()

    def enterEvent(self, QEvent):
        self.curr_col = QtGui.QColor(255, 100, 100)
        self.curr_line_thickness = self.annotation_object.line_w + 2

    def leaveEvent(self, QEvent):
        self.curr_col = self.annotation_object.get_color()
        self.curr_line_thickness = self.annotation_object.line_w

    def mouseDoubleClickEvent(self, QMouseEvent):
        self.drawing_editor = DrawingEditorWidget(self, self.overlay, self.overlay.settings)
        # self.drawing_editor.show()

    def update(self, *__args):
        #TODO Currently disabled for MACOSX
        # if self.overlay.current_time != self.time_last_updated:
        #     self.interpolate_location()
        #     self.time_last_updated = self.overlay.current_time
        # Scaling the Widgets according to the current size of the movie_player
        # This has to be done here, because if the location of the widget is outside the current renderframe )
        # For instance after reloading the project with a smaller window, it won't be updated
        self.scale_widget()
        self.move_widget()
        super(DrawingBase, self).update()


class DrawingEllipse(DrawingBase):
    def __init__(self, parent, annotation_object):
        super(DrawingEllipse, self).__init__(parent,annotation_object)

    def drawShape(self, qp, rect = None):
        if rect is None:
            rect = self.inner_rect

        qp.drawEllipse(rect)


class DrawingText(DrawingBase):
    def __init__(self, parent, annotation_object):
        super(DrawingText, self).__init__(parent, annotation_object)
        self.text = annotation_object.text
        self.font_size = annotation_object.font_size
        self.font = QtGui.QFont()
        self.font.setPointSize(annotation_object.font_size)


    def set_text(self, text = "Some Text"):
        self.text = text

    def drawShape(self, qp, rect = None, scale = 1.0):
        # Get the Automation Text
        if self.annotation_object.is_automated:
            source = self.annotation_object.project.get_by_id(self.annotation_object.automated_source)
            if source is not None:
               self.text = source.get_auto_text(self.annotation_object.automate_property, self.overlay.current_time, self.overlay.main_window.player.get_fps())

        self.font.setFamily(self.annotation_object.font)
        self.font.setPointSize(int(round(float(self.annotation_object.font_size) * self.scale, 0)))
        if rect is None:
            rect = self.inner_rect
        qp.setFont(self.font)
        qp.drawText(rect,Qt.TextWordWrap,  self.text)

    def mouseDoubleClickEvent(self, QMouseEvent):
        self.drawing_editor = DrawingEditorWidget(self, self.overlay, self.overlay.settings)


class DrawingRectangle(DrawingBase):
    def __init__(self, parent, annotation_object):
        super(DrawingRectangle, self).__init__(parent, annotation_object)

    def drawShape(self, qp, rect = None):
        if rect is None:
            rect = self.inner_rect

        qp.drawRect(rect)


class DrawingImage(DrawingBase):
    def __init__(self, parent, annotation_object):
        super(DrawingImage, self).__init__(parent, annotation_object)

    def drawShape(self, qp, rect = None):
        if rect is None:
            rect = self.inner_rect
        qp.drawImage(self.inner_rect, self.annotation_object.image)


class DrawingFreeHand(DrawingBase):
    def __init__(self, parent, annotation_object):
        super(DrawingFreeHand, self).__init__(parent, annotation_object)
        self.is_drawing = False
        self.button_pressed = False
        self.has_first_point = False
        self.new_path_index = 0
        self.new_path = None
        self.pen_location = QtCore.QPoint(0,0)
        self.current_color = (0,0,0)
        self.current_line_width = 5
        self.resolution_divisor = 2

        self.converted_paths = []
        self.update_paths()

    def update_paths(self):
        self.converted_paths = []
        for i, p in enumerate(self.annotation_object.free_hand_paths):
            self.converted_paths.append([[], p[1], p[2]])
            for j in range(len(p[0])):
                self.converted_paths[i][0].append(QtCore.QPointF(p[0][j][0], p[0][j][1]))

    def mouseDoubleClickEvent(self, QMouseEvent):
        self.is_drawing = True
        self.overlay.is_freehand_drawing = True
        self.overlay.main_window.annotation_toolbar.show_indicator(True)


    def abort_drawing(self):
        self.is_drawing = False
        self.overlay.is_freehand_drawing = False
        self.overlay.main_window.annotation_toolbar.show_indicator(False)


    def mousePressEvent(self, QMouseEvent):
        if not self.is_drawing:
            super(DrawingFreeHand, self).mousePressEvent(QMouseEvent)
        else:
            if QMouseEvent.button() == Qt.LeftButton:
                self.current_line_width = self.overlay.main_window.annotation_toolbar.line_width
                self.current_color = self.overlay.main_window.annotation_toolbar.current_color
                self.pen_location = QMouseEvent.pos()
                self.new_path = [[self.pen_location], self.current_color, self.current_line_width]
                self.has_first_point = True
                self.button_pressed = True

    def mouseMoveEvent(self, QMouseEvent):
        if not self.is_drawing:
            super(DrawingFreeHand, self).mouseMoveEvent(QMouseEvent)
        else:
            if self.button_pressed:
                self.new_path[0].append(QMouseEvent.pos())

    def mouseReleaseEvent(self, QMouseEvent):
        if not self.is_drawing:
            super(DrawingFreeHand, self).mouseReleaseEvent(QMouseEvent)
        else:
            if self.has_first_point:
                result = []
                color = self.new_path[1]
                width = self.new_path[2]

                for i, p in enumerate(self.new_path[0]):
                    if i < len(self.new_path[0]) - 1:
                        if i % self.resolution_divisor == 0:
                            point = p / self.scale
                            result.append([point.x(), point.y()])
                    else:
                        point = p / self.scale
                        result.append([point.x(), point.y()])

                # self.annotation_object.free_hand_paths.append([result, color, width])
                self.annotation_object.add_path(result, color, width)
                self.new_path = None

                # Abort Drawing
                self.has_first_point = False
                self.button_pressed = False
                self.update_paths()

                # self.is_drawing = False
                #
                # self.has_first_point = False
                # self.overlay.main_window.annotation_toolbar.show_indicator(False)
                # self.update_paths()


    def drawShape(self, qp, rect = None):
        if rect is None:
            rect = self.inner_rect

        if self.is_drawing:
            qp.drawRect(self.rect())



        if self.new_path is not None:
            path = QtGui.QPainterPath()
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(self.new_path[1][0], self.new_path[1][1], self.new_path[1][2]))
            pen.setWidth(self.new_path[2])
            qp.setPen(pen)

            if not len(self.new_path[0]) == 0:
                path.moveTo(self.new_path[0][0])
                for i in range(1, len(self.new_path[0]), 1):
                    path.lineTo(self.new_path[0][i])

            qp.drawPath(path)


        for p in self.converted_paths:
            path = QtGui.QPainterPath()
            pen = QtGui.QPen()
            pen.setColor(QtGui.QColor(p[1][0], p[1][1], p[1][2]))
            pen.setWidth(p[2])
            qp.setPen(pen)

            if not len(p[0]) == 0:
                path.moveTo(p[0][0] * self.scale)
                for i in range(1, len(p[0]), 1):
                    path.lineTo(p[0][i] * self.scale)

            qp.drawPath(path)


class DrawingEditorWidget(QtWidgets.QMainWindow):
    def __init__(self, drawing, parent, settings):
        super(DrawingEditorWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/DrawingEditorWidget.ui")
        uic.loadUi(path, self)
        self.drawing = drawing
        self.setWindowFlags(Qt.WindowStaysOnTopHint|Qt.FramelessWindowHint|Qt.Popup)

        self.setFocusPolicy(Qt.StrongFocus)
        x = drawing.width()/2
        y = drawing.height()
        if drawing.pos().x() > drawing.parent().width()/2:
            x = drawing.width()/2 - self.width()
        if drawing.pos().y() > drawing.parent().height() / 2:
            y = - self.height()

        self.move(drawing.mapToGlobal(QtCore.QPoint(x,y)))

        # self.textEdit.resize(self.size().width() - 100, self.size().height())
        self.color_picker = ColorSelector(self, settings)
        self.color_picker.on_selection.connect(self.on_color_change)
        # self.color_picker.move(self.size().width() - 50, 0)
        self.widget.layout().addWidget(self.color_picker)

        if isinstance(drawing, DrawingText):
            self.textEdit.setText(self.drawing.annotation_object.get_text())
            self.spinBox_FontSize.setValue(self.drawing.annotation_object.font_size)
            self.spinBox_FontSize.valueChanged.connect(self.on_fsize_changed)
            self.textEdit.textChanged.connect(self.on_text_change)
        else:
            self.textEdit.hide()
            self.font_widget.hide()
            self.setFixedWidth(200)
            self.setFixedHeight(100)

        self.spinBox_LineThickness.setValue(self.drawing.annotation_object.line_w)
        self.spinBox_LineThickness.valueChanged.connect(self.on_line_thickness_changed)
        self.fontComboBox.setCurrentFont(QFont(self.drawing.annotation_object.font))
        self.fontComboBox.currentFontChanged.connect(self.on_font_changed)

        self.setAttribute(Qt.WA_MacNoClickThrough, True)
        self.show()
        self.setFocus(Qt.MouseFocusReason)

    def on_text_change(self):
        text = self.textEdit.toPlainText()
        # self.drawing.annotation_object.set_text(text)
        self.drawing.text = text

    def on_text_finished(self):
        text = self.textEdit.toPlainText()
        self.drawing.annotation_object.set_text(text)

    def on_color_change(self, color):
        self.drawing.annotation_object.set_color(color)

    def on_font_changed(self, font):
        font = font.family()
        self.drawing.annotation_object.set_font(font)

    def on_fsize_changed(self):
        value = self.spinBox_FontSize.value()
        self.drawing.annotation_object.set_font_size(value)

    def on_line_thickness_changed(self, value):
        self.drawing.annotation_object.set_line_width(value)

    def paintEvent(self, *args, **kwargs):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()

        qp.begin(self)

        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing)
        pen.setColor(QtGui.QColor(80,80,80,100))
        qp.setPen(pen)

        qp.fillRect(self.rect(), QtGui.QColor(36,36,36))
        qp.end()

    def closeEvent(self, *args, **kwargs):
        text = self.textEdit.toPlainText()
        self.drawing.annotation_object.set_text(text)
        super(DrawingEditorWidget, self).closeEvent(*args, **kwargs)

    def focusOutEvent(self, *args, **kwargs):
        super(DrawingEditorWidget, self).focusOutEvent(*args, **kwargs)




