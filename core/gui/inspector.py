from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QTableWidgetItem, QTableWidget, QHBoxLayout
from PyQt5 import uic
from core.gui.ewidgetbase import EDockWidget
from core.data.interfaces import IProjectChangeNotify
from core.data.containers import *
from core.data.computation import ms_to_string, numpy_to_qt_image
from core.data.enums import MovieSource
from extensions.colormetrics.hilbert_colors import HilbertHistogramVis

class Inspector(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(Inspector, self).__init__(main_window)
        path = os.path.abspath("qt_ui/Inspector.ui")
        uic.loadUi(path, self)


        self.max_width = 450
        self.current_att_widgets = []
        self.lineEdit_Name.editingFinished.connect(self.set_name)
        self.textEdit_Notes.textChanged.connect(self.set_notes)
        self.item = None
        self.allow_change = False

    def set_name(self):
        if self.item is not None and self.allow_change:
            self.item.set_name(self.lineEdit_Name.text())

    def add_attribute_widget(self, AttributeWidget):
        self.contentWidget.layout().addWidget(AttributeWidget)
        self.current_att_widgets.append(AttributeWidget)

        AttributeWidget.show()

    def set_notes(self):
        if self.item is not None and self.allow_change:
            self.item.set_notes(self.textEdit_Notes.toPlainText())

    def on_changed(self, project, item):
        if item:
            self.on_selected(None, [item])

    def on_selected(self,sender, selected):
        if sender is self:
            return
        self.cleanup()

        if len(selected) == 0:
            return
        target_item = selected[len(selected) - 1]
        self.allow_change = False
        self.lineEdit_Name.setText(target_item.get_name())
        self.lbl_Type.setText(str(target_item.get_type()))
        self.item = target_item


        self.textEdit_Notes.setPlainText(self.item.get_notes())

        widgets = []
        s_type = selected[len(selected) - 1].get_type()
        if s_type == MOVIE_DESCRIPTOR:
            self.lbl_Type.setText("Movie Descriptor")
            widgets = [AttributesMovieDescriptor(self, target_item)]

        if s_type == SCREENSHOT:
            self.lbl_Type.setText("Screenshot")
            widgets = [AttributesScreenshot(self, target_item)]

        if s_type == SEGMENTATION:
            self.lbl_Type.setText("Segmentation")
            widgets = [AttributesSegmentation(self, target_item)]

        if s_type == SEGMENT:
            self.lbl_Type.setText("Segment")
            widgets = [AttributesITimeRange(self, target_item)]

        if s_type == ANNOTATION:
            self.lbl_Type.setText("Annotation")
            widgets = [AttributesITimeRange(self, target_item)]

        if s_type == ANNOTATION_LAYER:
            self.lbl_Type.setText("Annotation Layer")
            widgets = [AttributesITimeRange(self, target_item)]

        if s_type == ANALYSIS:
            self.lbl_Type.setText("Analysis")
            widgets = [AttributesAnalysis(self, target_item)]

        for w in widgets:
            self.add_attribute_widget(w)

        self.allow_change = True
    def on_loaded(self, project):
        self.cleanup()


    def cleanup(self):
        for w in self.current_att_widgets:
            w.close()
            w.deleteLater()
        self.current_att_widgets = []


class AttributesMovieDescriptor(QWidget):
    def __init__(self,parent, descriptor):
        super(AttributesMovieDescriptor, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesMovieDescriptor.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor


        self.lbl_movie_path.setText(self.descriptor.movie_path)
        self.lineEdit_MovieID.setText(str(self.descriptor.movie_id))
        self.lineEdit_MovieYear.setText(str(self.descriptor.year))
        self.lbl_Duration.setText(ms_to_string(self.descriptor.duration))

        for s in MovieSource:
            self.comboBox_Source.addItem(s.name)

        self.comboBox_Source.setCurrentText(self.descriptor.source)
        self.comboBox_Source.currentTextChanged.connect(self.on_source_changed)
        self.show()

    def on_source_changed(self):
        current_text = self.comboBox_Source.currentText()
        self.descriptor.source = current_text


class AttributesScreenshot(QWidget):
    def __init__(self,parent, descriptor):
        super(AttributesScreenshot, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesScreenshot.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor

        self.lbl_timestamp.setText(ms_to_string(self.descriptor.movie_timestamp))
        self.lbl_segment_id.setText(str(self.descriptor.scene_id))
        self.lbl_global_id.setText(str(self.descriptor.shot_id_global))
        self.lbl_segm_id.setText(str(self.descriptor.shot_id_segm))

        self.lbl_Preview.setPixmap(numpy_to_qt_image(self.descriptor.img_movie, target_width=400)[1])
        self.show()


class AttributesITimeRange(QWidget):
    def __init__(self,parent, descriptor):
        super(AttributesITimeRange, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesITimeRange.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor

        self.lbl_start.setText(ms_to_string(descriptor.get_start()))
        self.lbl_end.setText(ms_to_string(descriptor.get_end()))
        self.lbl_duration.setText(ms_to_string(descriptor.get_end() - descriptor.get_start()))
        self.show()


class AttributesSegmentation(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesSegmentation, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesSegmentation.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor
        # self.table_segments = QTableWidget()
        self.table_segments.setColumnCount(4)
        self.table_segments.setHorizontalHeaderItem(0,QTableWidgetItem("ID"))
        self.table_segments.setHorizontalHeaderItem(1,QTableWidgetItem("Start"))
        self.table_segments.setHorizontalHeaderItem(2,QTableWidgetItem("Stop"))
        self.table_segments.setHorizontalHeaderItem(2, QTableWidgetItem("Name"))
        self.table_segments.verticalHeader().hide()

        for i,s in enumerate(self.descriptor.segments):
            self.table_segments.setRowCount(self.table_segments.rowCount() + 1)
            self.table_segments.setItem(i, 0, QTableWidgetItem(str(s.ID)))
            self.table_segments.setItem(i, 1, QTableWidgetItem(ms_to_string(s.get_start())))
            self.table_segments.setItem(i, 2, QTableWidgetItem(ms_to_string(s.get_end())))
            self.table_segments.setItem(i, 3, QTableWidgetItem(str(s.get_name())))
        self.table_segments.resizeColumnsToContents()
        self.table_segments.resizeRowsToContents()
        self.show()


class AttributesAnalysis(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesAnalysis, self).__init__(parent)
        self.descriptor = descriptor
        self.setLayout(QGridLayout(self))
        self.layout().addWidget(QLabel("<b>Target: " +self.descriptor.get_target_item().get_name()))
        index = self.descriptor.procedure_id
        self.vis = self.parent().main_window.analyzes_list[index].get_visualization(self, descriptor)
        self.layout().addWidget(self.vis)
        self.show()

