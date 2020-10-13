from core.container.media_objects import AbstractMediaObject
from core.data.computation import ms_to_string
from core.data.tracking import BasicTrackingJob
from core.gui.context_menu import open_context_menu
from core.gui.perspectives import Perspective
from core.node_editor.node_editor import *
from core.gui.annotation_editor import AnnotationEditor
from core.gui.misc.filmography_widget import FilmographyWidget2

from core.gui.tag_widget import TagWidget
from PyQt5 import QtCore

class Inspector(EDockWidget, IProjectChangeNotify):
    def __init__(self, main_window):
        super(Inspector, self).__init__(main_window, limit_size=True, width=450)
        path = os.path.abspath("qt_ui/Inspector.ui")
        uic.loadUi(path, self)

        self.max_width = 450
        self.current_att_widgets = []
        self.lineEdit_Name.editingFinished.connect(self.set_name)
        self.textEdit_Notes.textChanged.connect(self.set_notes)

        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.btn_VocMatrix.clicked.connect(self.main_window.create_vocabulary_matrix)

        self.visibilityChanged.connect(self.on_visibility_changed)
        self.lineEdit_Vocabulary.setCompleter(self.completer)

        # self.widget().setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        # self.widget().setMaximumWidth(self.max_width)
        # self.widget().setMinimumWidth(self.max_width // 2)

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

    def vocabulary_key_press(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Tab:
            self.lineEdit_Vocabulary.setText(self.completer.currentCompletion())

    def set_voc_words(self):
        if self.item is not None and isinstance(self.item, IClassifiable):
            text = ""
            for word in self.item.tag_keywords:
                text += word.get_name() + ", "
            self.textEdit_VocList.setPlainText(text)

    # def add_voc_word(self):
    #     if self.lineEdit_Vocabulary.text() != "" and self.item is not None:
    #         new_word = self.project().get_word_object_from_name(self.lineEdit_Vocabulary.text())
    #         if new_word is not None:
    #             self.item.add_word(new_word)
    #     self.set_voc_words()
    #     self.lineEdit_Vocabulary.setText("")

    def on_changed(self, project, item):
        if item is not None and not isinstance(item, AbstractMediaObject):
            self.on_selected(None, [item])

    @pyqtSlot(bool)
    def on_visibility_changed(self, visibility):
        if visibility:
            if self.main_window.project is not None:
                self.on_selected(None, self.main_window.project.selected)

    def on_selected(self,sender, selected):
        if sender is self or not self.isVisible():
            return
        self.cleanup()

        if len(selected) == 0:
            return
        target_item = selected[len(selected) - 1]
        self.allow_change = False
        self.lineEdit_Name.setText(target_item.get_name())
        self.lbl_Type.setText(str(target_item.get_type()))
        self.item = target_item

        self.completer.setModel(self.project().get_auto_completer_model())
        self.textEdit_Notes.setPlainText(self.item.get_notes())
        self.set_voc_words()

        widgets = []
        s_type = selected[len(selected) - 1].get_type()
        if s_type == MOVIE_DESCRIPTOR:
            self.lbl_Type.setText("Movie Descriptor")
            t = FilmographyWidget2(self, self.project())

            def update_filmography(self, t):
                self.project().movie_descriptor.meta_data = t.get_filmography()

            t.onFilmographyChanged.connect(partial(update_filmography, self, t))
            widgets = [AttributesMovieDescriptor(self, target_item), t]

        if s_type == SCREENSHOT:
            self.lbl_Type.setText("Screenshot")
            widgets = [AttributesScreenshot(self, target_item)]

        if s_type == SEGMENTATION:
            self.lbl_Type.setText("Segmentation")
            widgets = [AttributesSegmentation(self, target_item)]

        if s_type == SEGMENT:
            self.lbl_Type.setText("Segment")
            widgets = [AttributesITimeRange(self, target_item), AttributesSegment(self, target_item)]

        if s_type == ANNOTATION:
            self.lbl_Type.setText("Annotation")

            if target_item.a_type == AnnotationType.Text:
                widgets = [AttributesITimeRange(self, target_item), AttributesAnnotation(self, target_item), AttributesTextAnnotation(self, target_item)]
            else:
                widgets = [AttributesITimeRange(self, target_item), AttributesAnnotation(self, target_item)]

        if s_type == ANNOTATION_LAYER:
            self.lbl_Type.setText("Annotation Layer")
            widgets = [AttributesITimeRange(self, target_item)]

        if s_type == ANALYSIS_JOB_ANALYSIS:
            self.lbl_Type.setText("Analysis")
            widgets = [AttributesAnalysis(self, target_item)]

        if s_type == NODE:
            self.lbl_Type.setText("Node")
            widgets = [AttributesNode(self, target_item)]

        if s_type == VOCABULARY or s_type == VOCABULARY_WORD:
            self.lbl_Type.setText("Vocabulary")
            widgets = [AttributesVocabulary(self, target_item)]

        if s_type in [SEGMENT, SCREENSHOT, ANNOTATION]:
            for analysis in target_item.connected_analyses:
                widgets.append(AttributesAnalysis(self, analysis))

        if isinstance(target_item, VIANProject):
            widgets.append(AttributesProject(self, target_item))

        if isinstance(target_item, IHasMediaObject):
            widgets.append(AttributesMediaObject(self, target_item))

        if isinstance(target_item, IClassifiable):
            widgets.append(AttributesClassifiable(self, target_item))

        for w in widgets:
            self.add_attribute_widget(w)


        # TODO VOcabularies should be removed completely from the Inspector
        # if self.item is not None and isinstance(self.item, IHasVocabulary):
        #     self.widget_vocabulary_section.show()
        # else:
        #     self.widget_vocabulary_section.hide()

        self.widget_vocabulary_section.hide()

        self.allow_change = True

    def on_loaded(self, project):
        self.setDisabled(False)
        self.cleanup()

    def on_closed(self):
        self.setDisabled(True)

    def cleanup(self):
        for w in self.current_att_widgets:
            w.close()
            w.deleteLater()
        self.current_att_widgets = []


class AttributesProject(QWidget):
    def __init__(self,parent, project:VIANProject):
        super(AttributesProject, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesProject.ui")
        uic.loadUi(path, self)
        self.project = project

        self.lbl_ProjectTitle.setText(self.project.name)

        self.lbl_MovieFile.setText(self.project.movie_descriptor.movie_path)

        self.lbl_Segmentations.setText(str(len(self.project.segmentation)))
        n_segments = 0
        for s in self.project.segmentation:
            n_segments += len(s.segments)

        self.lbl_Segments.setText(str(n_segments))
        self.lbl_Screenshots.setText(str(len(self.project.screenshots)))

        self.lbl_Colorimetry.setText("Incomplete" if self.project.colormetry_analysis is None or not self.project.colormetry_analysis.has_finished else "Finished")
        n_tags = 0
        for e in self.project.experiments:
            n_tags += len(e.classification_results)
        self.lbl_Classification.setText("{t} Tags applied".format(t=n_tags))
        # self.lbl_ProjectTitle.setText(self.project.name)


        self.show()


class AttributesMovieDescriptor(QWidget):
    def __init__(self,parent, descriptor):
        super(AttributesMovieDescriptor, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesMovieDescriptor.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor


        self.lbl_movie_path.setText(self.descriptor.movie_path)
        self.lineEdit_MovieYear.setText(str(self.descriptor.year))
        self.lbl_Duration.setText(ms_to_string(self.descriptor.duration))

        self.lineEdit_MovieYear.editingFinished.connect(self.on_movie_year_changed)

        try:
            self.spinBox_ID_0.setValue(int(self.descriptor.movie_id.split("_")[0]))
            self.spinBox_ID_1.setValue(int(self.descriptor.movie_id.split("_")[1]))
            self.spinBox_ID_2.setValue(int(self.descriptor.movie_id.split("_")[2]))
        except:
            pass

        self.spinBox_ID_0.valueChanged.connect(self.on_desc_id_changed)
        self.spinBox_ID_1.valueChanged.connect(self.on_desc_id_changed)
        self.spinBox_ID_2.valueChanged.connect(self.on_desc_id_changed)

        for s in MovieSource:
            self.comboBox_Source.addItem(s.name)

        self.comboBox_Source.setCurrentText(self.descriptor.source)
        self.comboBox_Source.currentTextChanged.connect(self.on_source_changed)
        self.show()

    def on_desc_id_changed(self):
        self.descriptor.movie_id = str(self.spinBox_ID_0.value()) + "_" + str(self.spinBox_ID_1.value()) + "_" + str(self.spinBox_ID_2.value())

    def on_movie_year_changed(self):
        try:
            self.descriptor.year = int(self.lineEdit_MovieYear.text())
        except:
            pass

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

        self.lbl_Preview.setPixmap(numpy_to_qt_image(self.descriptor.get_img_movie_orig_size(), target_width=400)[1])
        self.show()


class AttributesITimeRange(QWidget):
    def __init__(self,parent, descriptor):
        super(AttributesITimeRange, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesITimeRange.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor

        self.lbl_start.setText(ms_to_string(descriptor.get_start(), include_ms=True))
        self.lbl_end.setText(ms_to_string(descriptor.get_end(), include_ms=True))
        self.lbl_duration.setText(ms_to_string(descriptor.get_end() - descriptor.get_start(), include_ms=True))
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


class AttributesAnnotation(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesAnnotation, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesAnnotation.ui")
        uic.loadUi(path, self)
        self.annotation = descriptor
        self.main_window = parent.main_window

        self.comboBox_Tracking.setCurrentText(self.annotation.tracking)
        # self.comboBox_Tracking.currentIndexChanged.connect(self.on_tracking_changed)
        self.btn_Track.clicked.connect(self.on_track)

        self.show()

    def on_track(self):
        index =  self.comboBox_Tracking.currentIndex()
        if index != 0:
            # Removing all keys from the Annotation
            self.annotation.remove_keys()


            bbox = (float(self.annotation.orig_position[0]),
                    float(self.annotation.orig_position[1]),
                    float(int(self.annotation.size[0])),
                    float(int(self.annotation.size[1])))

            job = BasicTrackingJob([self.annotation.unique_id,
                                    bbox,
                                    self.main_window.project.movie_descriptor.get_movie_path(),
                                    self.annotation.get_start(),
                                    self.annotation.get_end(),
                                    self.main_window.player.get_fps(),
                                    self.comboBox_Tracking.currentText(),
                                    self.spinBox_Resolution.value()
                                    ])
            self.annotation.tracking = self.comboBox_Tracking.currentText()
            self.main_window.run_job_concurrent(job)


class AttributesTextAnnotation(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesTextAnnotation, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesTextAnnotation.ui")
        uic.loadUi(path, self)
        self.annotation = descriptor
        self.main_window = parent.main_window

        self.checkBox_TextAutomation.setChecked(self.annotation.is_automated)

        self.source_objects = []
        for obj in self.main_window.project.get_all_containers():
            if isinstance(obj, AutomatedTextSource):
                self.comboBox_AutoSourceObject.addItem(obj.get_name())
                self.source_objects.append(obj)

        self.update_source_property_cb()

        try:
            self.comboBox_AutoSourceObject.setCurrentText(self.main_window.project.get_by_id(self.annotation.automated_source).get_name())
            self.comboBox_AutoSourceProperty.setCurrentText(self.annotation.automate_property)
        except:
            pass

        self.comboBox_AutoSourceObject.currentIndexChanged.connect(self.on_source_changed)
        self.comboBox_AutoSourceProperty.currentIndexChanged.connect(self.on_automation_changed)
        self.checkBox_TextAutomation.stateChanged.connect(self.on_automation_changed)
        self.show()


    def update_source_property_cb(self):
        self.comboBox_AutoSourceProperty.clear()
        obj =  self.source_objects[self.comboBox_AutoSourceObject.currentIndex()]
        for attr in obj.get_source_properties():
            self.comboBox_AutoSourceProperty.addItem(attr)

    def on_source_changed(self):
        self.update_source_property_cb()

    def on_automation_changed(self):
        self.annotation.is_automated = self.checkBox_TextAutomation.isChecked()
        if self.annotation.is_automated:
            self.annotation.automated_source = self.source_objects[self.comboBox_AutoSourceObject.currentIndex()].get_id()
            self.annotation.automate_property = self.comboBox_AutoSourceProperty.currentText()


class AttributesVocabulary(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesVocabulary, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesVocabulary.ui")
        uic.loadUi(path, self)
        self.voc_entry = descriptor
        self.textEdit_Comment.setText(self.voc_entry.comment)
        self.textEdit_Comment.textChanged.connect(self.on_comment_changed)
        self.lineEdit_HelpURL.setText(self.voc_entry.info_url)
        self.lineEdit_HelpURL.editingFinished.connect(self.on_comment_changed)

    def on_comment_changed(self):
        self.voc_entry.comment = self.textEdit_Comment.toPlainText()

    def on_url_changed(self):
        self.voc_entry.help_url = self.textEdit_HelpURL.text()

#textEdit_AnnotationBody
class AttributesSegment(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesSegment, self).__init__(parent)
        path = os.path.abspath("qt_ui/AttributesSegment.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor

        self.annotation_editor = AnnotationEditor(self, self.descriptor)
        self.widgetInner.layout().addWidget(self.annotation_editor)

        # self.textEdit_AnnotationBody.setPlainText(self.descriptor.get_annotation_body())
        # self.textEdit_AnnotationBody.installEventFilter(self)

    # def on_body_changed(self):
    #     text = self.textEdit_AnnotationBody.toPlainText()
    #     self.descriptor.set_annotation_body(text)

    # def eventFilter(self, QObject, QEvent):
    #     if QEvent.type() == QtCore.QEvent.FocusOut:
    #         self.on_body_changed()
    #
    #     return super(AttributesSegment, self).eventFilter(QObject, QEvent)


class AttributesMediaObject(QWidget):
    def __init__(self, parent, descriptor:IHasMediaObject):
        super(AttributesMediaObject, self).__init__(parent)
        self.inspector = parent
        path = os.path.abspath("qt_ui/AttributesMediaObject.ui")
        uic.loadUi(path, self)
        self.descriptor = descriptor
        self.setAcceptDrops(True)

        self.listWidget_AttachedMedia = MediaObjectsList(self, self)
        self.layout().addWidget(self.listWidget_AttachedMedia)
        self.update_list()

    def update_list(self):
        self.listWidget_AttachedMedia.clear()
        self.listWidget_AttachedMedia.setToolTip("Drop Files you want to attach here.")
        for obj in self.descriptor.media_objects:
            self.listWidget_AttachedMedia.addItem(QListWidgetItem(obj.get_name()))

    def context_menu(self, pos):
        try:
            media_object = self.descriptor.media_objects[self.listWidget_AttachedMedia.currentIndex().row()]
            open_context_menu(self.inspector.main_window, pos, [media_object], media_object.project)
        except Exception as e:
            log_error(e)
            pass


    def keyPressEvent(self, a0: QtGui.QKeyEvent):
        if a0.key() == Qt.Key_Delete:
            idx = self.listWidget_AttachedMedia.currentIndex()
            self.descriptor.remove_media_object(self.descriptor.media_objects[idx])
            self.update_list()

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent):
        a0.acceptProposedAction()

    def dropEvent(self, a0: QtGui.QDropEvent):
        self.descriptor.project.create_media_object("New Object",
                                                    a0.mimeData().urls()[0].toLocalFile(),
                                                    self.descriptor)

        self.update_list()


class MediaObjectsList(QListWidget):
    def __init__(self, parent, attr_widget):
        super(MediaObjectsList, self).__init__(parent)
        self.attr_widget = attr_widget

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        super(MediaObjectsList, self).mousePressEvent(e)
        if e.button() == Qt.RightButton:
            self.attr_widget.context_menu(self.mapToGlobal(e.pos()))


class AttributesAnalysis(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesAnalysis, self).__init__(parent)
        self.descriptor = descriptor
        self.setLayout(QVBoxLayout(self))
        self.main_window = parent.main_window

        clobj_name = "Default"
        if self.descriptor.target_classification_object is not None:
            clobj_name = self.descriptor.target_classification_object.name

        title = QLabel("Analysis: " + descriptor.name.replace("_", " "))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold;")
        self.layout().addWidget(title)
        self.layout().addWidget(QLabel("Target: " + clobj_name))

        # index = self.descriptor.procedure_id
        # self.vis_button = QPushButton("Show Visualization", self)
        # self.layout().addWidget(self.vis_button)
        # self.vis_button.clicked.connect(self.on_show_vis)
        self.vis = descriptor.get_preview()

        # Vis could be none because of a failed Visualization creation
        if self.vis is not None:
            self.vis.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred))
            self.layout().addWidget(self.vis)
        self.show()

    def on_show_vis(self):
        self.descriptor.project.set_selected(sender = self, selected = [self.descriptor])
        self.main_window.switch_perspective(Perspective.Results)
        # self.descriptor.get_visualization()


class AttributesNode(QWidget):
    def __init__(self, parent, descriptor):
        super(AttributesNode, self).__init__(parent)
        self.descriptor = descriptor

        self.setLayout(QVBoxLayout(self))
        self.default_values = []

        self.layout().addWidget(QLabel("Default Parameters", self))
        if descriptor.node_widget is None:
            info = QLabel("Set this script as current script to modify the default parameters", self)
            info.setWordWrap(True)
            self.layout().addWidget(info)
            return

        for i, f in enumerate(self.descriptor.node_widget.fields):
            if isinstance(f, InputField):
                if f.connection is None:
                    if f.data_type_slot.default_value is not None:
                        slot = f.data_type_slot.default_data_type
                        item = None

                        if slot == DT_Numeric:
                            item = DefaultValueNumeric(self, f)

                        elif slot == DT_Vector:
                            item = DefaultValueVector(self, f)

                        elif slot == DT_Vector2:
                            item = DefaultValueVector2(self, f)

                        elif slot == DT_Vector3:
                            item = DefaultValueVector3(self, f)

                        elif slot == DT_Literal:
                            item = DefaultLiteral(self, f)

                        if item is not None:
                            item.setStyleSheet("QWidget{margin: 1px; padding: 1px;}")
                            self.layout().addWidget(item)

        self.layout().addWidget(QLabel("Cache Size:" + str(round(float(self.descriptor.node_widget.cache_size) / 1000000, 2)) + " MB", self))

        self.show()


class AttributesNodeDefaultValues(QWidget):
    def __init__(self, parent, field):
        super(AttributesNodeDefaultValues, self).__init__(parent)
        self.field = field
        self.slot = field.data_type_slot
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(QLabel(field.data_type_slot.name.rjust(15)))

    def get_value(self):
        pass

    def on_value_changed(self):
        self.field.node.update_output_types()


class DefaultValueNumeric(AttributesNodeDefaultValues):
    def __init__(self, parent, field):
        super(DefaultValueNumeric, self).__init__(parent, field)
        self.sp = QSpinBox(self)
        self.sp.setRange(0, 9999999)
        self.sp.setValue(self.slot.default_value)
        self.layout().addWidget(self.sp)

        self.sp.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self):
        self.slot.default_value = self.sp.value()
        super(DefaultValueNumeric, self).on_value_changed()


class DefaultValueVector(AttributesNodeDefaultValues):
    def __init__(self, parent, field):
        super(DefaultValueVector, self).__init__(parent, field)
        self.lineEdit = QLineEdit(self)
        self.layout().addWidget(self.lineEdit)

        text = ""
        # if not isinstance(self.slot.default_value, list):
        #     self.slot.default_value = [self.slot.default_value]
        #     print "Silenced Default Value Vector error in Inspector line 279"

        for v in self.slot.default_value:
            text += str(v) + ","
        self.lineEdit.setText(text)

        self.lineEdit.textChanged.connect(self.on_value_changed)
        validator = QRegExpValidator()
        regex = QRegExp("^[0-9]+[.]?[0-9]*(,[0-9]+[.]?[0-9]*)*$")
        validator.setRegExp(regex)
        self.lineEdit.setValidator(validator)


    def on_value_changed(self):
        text = self.lineEdit.text() + ","
        numbers = text.replace(" ", "").split(",")
        result = []
        try:
            for n in numbers:
                if n != "":
                    result.append(float(n))
            self.slot.default_value = np.array(result)
            super(DefaultValueVector, self).on_value_changed()
        except:
            log_error("error", n)


class DefaultValueVector2(AttributesNodeDefaultValues):
    def __init__(self, parent, field):
        super(DefaultValueVector2, self).__init__(parent, field)
        self.sp1 = QSpinBox(self)
        self.sp1.setRange(0, 9999999)
        self.sp1.setValue(self.slot.default_value[0])
        self.layout().addWidget(self.sp1)
        self.sp2 = QSpinBox(self)
        self.sp2.setRange(0, 9999999)
        self.sp2.setValue(self.slot.default_value[1])
        self.layout().addWidget(self.sp2)

        self.sp1.valueChanged.connect(self.on_value_changed)
        self.sp2.valueChanged.connect(self.on_value_changed)


    def on_value_changed(self):
        self.slot.default_value = np.array([self.sp1.value(), self.sp2.value()])
        super(DefaultValueVector2, self).on_value_changed()


class DefaultValueVector3(AttributesNodeDefaultValues):
    def __init__(self, parent, field):
        super(DefaultValueVector3, self).__init__(parent, field)
        self.sp1 = QSpinBox(self)
        self.sp1.setRange(0, 9999999)
        self.sp1.setValue(self.slot.default_value[0])
        self.layout().addWidget(self.sp1)
        self.sp2 = QSpinBox(self)
        self.sp2.setRange(0, 9999999)
        self.sp2.setValue(self.slot.default_value[1])
        self.layout().addWidget(self.sp2)
        self.sp3 = QSpinBox(self)
        self.sp3.setRange(0, 9999999)
        self.sp3.setValue(self.slot.default_value[2])
        self.layout().addWidget(self.sp3)

        self.sp1.valueChanged.connect(self.on_value_changed)
        self.sp2.valueChanged.connect(self.on_value_changed)
        self.sp3.valueChanged.connect(self.on_value_changed)

    def on_value_changed(self):
        self.slot.default_value = np.array([self.sp1.value(), self.sp2.value(), self.sp3.value()])
        super(DefaultValueVector3, self).on_value_changed()


class DefaultLiteral(AttributesNodeDefaultValues):
    def __init__(self, parent, field):
        super(DefaultLiteral, self).__init__(parent, field)
        self.lineEdit = QLineEdit(self)
        self.lineEdit.setText(self.slot.default_value)
        self.layout().addWidget(self.lineEdit)

        self.lineEdit.textChanged.connect(self.on_value_changed)

    def on_value_changed(self):
        self.slot.default_value = self.lineEdit.text()
        super(DefaultLiteral, self).on_value_changed()


class AttributesClassifiable(QWidget):
    def __init__(self, parent, descriptor:IClassifiable):
        super(AttributesClassifiable, self).__init__(parent)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(QLabel("Classification"))
        self.tag_widget = TagWidget(self)
        self.layout().addWidget(self.tag_widget)

        self.descriptor = descriptor
        for t in descriptor.tag_keywords:
            self.tag_widget.add_tag(":".join([t.class_obj.name, t.voc_obj.name, t.word_obj.name]))
        self.show()

