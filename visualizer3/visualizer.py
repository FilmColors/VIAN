from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from core.gui.classification import CheckBoxGroupWidget
from PyQt5 import uic
import os
from typing import List

from core.corpus.shared.sqlalchemy_entities import *
from visualizer3.worker import QueryWorker, CORPUS_PATH
from functools import partial


class VIANVisualizer(QMainWindow):
    onSegmentQuery = pyqtSignal(object, object)
    onMovieQuery = pyqtSignal(object)
    onCorpusQuery = pyqtSignal()

    def __init__(self, parent = None):
        super(VIANVisualizer, self).__init__(parent)
        self.query_widget = KeywordWidget(self, self)
        self.setCentralWidget(QWidget(self))
        self.worker = QueryWorker(CORPUS_PATH)
        self.worker.signals.onCorpusQueryResult.connect(self.on_corpus_result)
        self.onCorpusQuery.connect(self.worker.on_corpus_info)
        self.centralWidget().setLayout(QVBoxLayout())

        self.cb_corpus = QComboBox(self)
        self.cb_query_type = QComboBox(self)
        self.cb_query_type.addItems(["Segments", "Movies"])

        self.centralWidget().layout().addWidget(self.cb_corpus)
        self.centralWidget().layout().addWidget(self.cb_query_type)
        self.centralWidget().layout().addWidget(self.query_widget)

        self.classification_objects = []
        self.onCorpusQuery.emit()
        self.show()

    def on_corpus_result(self, projects:List[DBProject], keywords:List[DBUniqueKeyword], classification_objects: List[DBClassificationObject], subcorpora):
        self.classification_objects = classification_objects
        self.query_widget.clear()
        for kwd in keywords:
            voc = kwd.word.vocabulary
            cl_obj =kwd.classification_object
            word = kwd.word
            self.query_widget.add_unique_keyword(kwd, cl_obj, voc, word)
        self.query_widget.add_spacers()
        for c in subcorpora:
            self.cb_corpus.addItem(c.name)


class ClassificationObjectList(QListWidget):
    def __init__(self, parent):
        super(ClassificationObjectList, self).__init__(parent)
        self.item_entries = []
        self.clear_list()

    def clear_list(self):
        self.clear()
        self.item_entries = []
        itm = QListWidgetItem("Filmography")
        self.addItem(itm)

    def get_item(self, cl_obj):
        for item in self.item_entries:
            if item[0] == cl_obj:
                return item[2]

    def add_item(self, class_obj):
        itm = QListWidgetItem(class_obj.name)
        itm.setCheckState(Qt.Unchecked)
        self.addItem(itm)
        self.item_entries.append((class_obj, len(self.item_entries), itm))
        return itm


class KeywordWidget(QWidget):
    def __init__(self,parent, visualizer):
        super(KeywordWidget, self).__init__(parent)
        self.visualizer = visualizer
        self.setLayout(QHBoxLayout(self))
        self.class_obj_list = ClassificationObjectList(self)
        self.class_obj_list.setMaximumWidth(300)
        self.class_obj_list.currentItemChanged.connect(self.on_classification_object_changed)
        self.stack_widget = QStackedWidget(self)
        # self.stack_widget.setStyleSheet("QWidget{background: rgb(30,30,30);}")

        self.stack_map = dict()
        self.tabs_map = dict()
        self.voc_map = dict()
        self.keyword_map = dict()
        self.keyword_cl_obj_map = dict()
        self.layout().addWidget(self.class_obj_list)
        self.layout().addWidget(self.stack_widget)
        self.filmography_widget = None
        self.add_filmography_widget()

    def add_filmography_widget(self):
        stack = FilmographyWidget(self, self.visualizer)
        self.stack_map["Filmography"] = stack
        self.stack_widget.addWidget(stack)
        self.filmography_widget = stack

    def on_classification_object_changed(self):
        self.stack_widget.setCurrentIndex(self.class_obj_list.currentIndex().row())

    def clear(self):
        self.class_obj_list.clear_list()
        for s in self.stack_map.keys():
            self.stack_map[s].deleteLater()
        self.stack_map = dict()
        self.tabs_map = dict()
        self.voc_map = dict()
        self.keyword_map = dict()
        self.keyword_cl_obj_map = dict()

        self.add_filmography_widget()

    def add_spacers(self):
        for x in self.tabs_map.keys():
            for y in self.tabs_map[x].keys():
                self.tabs_map[x][y].widget().layout().addItem(QSpacerItem(2,2,QSizePolicy.Fixed, QSizePolicy.Expanding))

    def add_unique_keyword(self, ukw: DBUniqueKeyword, cl_obj: DBClassificationObject, voc: DBVocabulary, voc_word: DBVocabularyWord):
        if cl_obj.name not in self.tabs_map:
            stack = QTabWidget()
            self.stack_map[cl_obj.name] = stack
            self.stack_widget.addWidget(stack)
            self.tabs_map[cl_obj.name] = dict()
            self.voc_map[cl_obj.name] = dict()
            cl_obj_item = self.class_obj_list.add_item(cl_obj)
            stack.show()
        else:
            stack = self.stack_map[cl_obj.name]
            cl_obj_item = self.class_obj_list.get_item(cl_obj)

        if voc.vocabulary_category.name not in self.tabs_map[cl_obj.name]:
            tab = QScrollArea(stack)
            tab.setWidgetResizable(True)
            tab.setWidget(QWidget(tab))
            tab.widget().setLayout(QVBoxLayout(tab.widget()))
            stack.addTab(tab, voc.vocabulary_category.name)
            self.stack_map[cl_obj.name].addTab(tab, voc.vocabulary_category.name)
            self.tabs_map[cl_obj.name][voc.vocabulary_category.name] = tab
            self.voc_map[cl_obj.name][voc.vocabulary_category.name] = dict()
            tab.show()
        else:
            tab = self.tabs_map[cl_obj.name][voc.vocabulary_category.name]

        if voc.name not in self.voc_map[cl_obj.name][voc.vocabulary_category.name]:
            group = CheckBoxGroupWidget(self, voc.name)
            tab.widget().layout().addWidget(group)
            self.voc_map[cl_obj.name][voc.vocabulary_category.name][voc.name] = group
            group.show()
        else:
            group = self.voc_map[cl_obj.name][voc.vocabulary_category.name][voc.name]

        checkbox = WordCheckBox(None, voc_word)
        self.keyword_map[ukw.id] = checkbox
        self.keyword_cl_obj_map[ukw.id] = cl_obj_item
        group.add_checkbox(checkbox)
        checkbox.show()
        print(checkbox)

    def get_keyword_filters(self):
        result_include = []
        result_exclude = []
        for k in self.keyword_map.keys():
            cb = self.keyword_map[k]
            if cb.checkState() == Qt.Checked:
                result_include.append(cb.unique_keyword.unique_keyword_id)
            elif cb.checkState() == Qt.PartiallyChecked:
                result_exclude.append(cb.unique_keyword.unique_keyword_id)
        return dict(include=result_include, exclude=result_exclude)

    def get_classification_object_filters(self):
        result = []
        for item in self.class_obj_list.item_entries:
            try:
                if item[2].checkState() == Qt.Checked:
                    result.append(item[0].classification_object_id)
                print("ok")
            except Exception as e:
                print(e)
        return result


class WordCheckBox(QCheckBox):
    def __init__(self, parent, word):
        super(WordCheckBox, self).__init__(parent)
        self.word = word
        self.setText(word.name)


class FilmographyWidget(QWidget):
    def __init__(self,parent, visualizer):
        super(FilmographyWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/FilmographyQueryWidget.ui")
        uic.loadUi(path, self)

    def get_filmography_query(self):
        query = FilmographyQuery()
        if self.lineEdit_IMDB.text() != "":
            query.imdb_id = self.lineEdit_IMDB.text().split(",")
        if self.spinBox_Corpus_A.value() > 0:
            query.corpus_id = [self.spinBox_Corpus_A.value(), self.spinBox_Corpus_B.value(), self.spinBox_Corpus_C.value()]
        if self.lineEdit_Genre.text() != "":
            query.genre = self.lineEdit_Genre.text().split(",")
        if self.comboBox_ColorProcess.currentText() != "":
            query.color_process = self.comboBox_ColorProcess.text().split(",")
        if self.lineEdit_Director.text() != "":
            query.director = self.lineEdit_Director.text().split(",")
        if self.lineEdit_Cinematography.text() != "":
            query.cinematography = self.lineEdit_Cinematography.text().split(",")
        if self.lineEdit_ColorConsultant.text() != "":
            query.color_consultant = self.lineEdit_ColorConsultant.text().split(",")
        if self.lineEdit_ProductionDesign.text() != "":
            query.production_design = self.lineEdit_ProductionDesign.text().split(",")
        if self.lineEdit_ArtDirector.text() != "":
            query.art_director = self.lineEdit_ArtDirector.text().split(",")
        if self.lineEdit_CostumDesign.text() != "":
            query.costum_design = self.lineEdit_CostumDesign.text().split(",")
        if self.lineEdit_ProductionCompany.text() != "":
            query.production_company = self.lineEdit_ProductionCompany.text().split(",")
        if self.lineEdit_ProductionCountry.text() != "":
            query.country = self.lineEdit_ProductionCountry.text().split(",")
        if self.spinBox_YearA.value() > 0:
            query.year_start = self.spinBox_YearA.value()
        if self.spinBox_YearB.value() > 0:
            query.year_end = self.spinBox_YearB.value()

        return query



