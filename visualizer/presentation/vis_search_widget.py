from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic
import os

from random import sample
from visualizer.presentation.presentation_widget import *
from core.gui.classification import CheckBoxGroupWidget
from visualizer.widgets.search_bar import *
from core.corpus.shared.entities import *
from visualizer.widgets.representation_widgets import *


class VisSearchLayout(PresentationWidget):
    def __init__(self, parent, visualizer):
        super(VisSearchLayout, self).__init__(parent, visualizer, "qt_ui/visualizer/VisSearchLayout.ui")
        self.search_widget = VisSearchBar(self, visualizer)
        self.lower_stack = QStackedWidget(self)
        self.keyword_widget = KeywordWidget(self, visualizer)
        self.query_result_widget = QueryResultWidget(self, self.visualizer)
        self.lower_stack.addWidget(self.keyword_widget)
        self.lower_stack.addWidget(self.query_result_widget)
        self.lower_stack.setCurrentIndex(0)
        self.query_result_widget.onClosed.connect(partial(self.lower_stack.setCurrentIndex, 0))

        self.hbox_SearchField.addWidget(self.search_widget)
        self.hbox_Keywords.addWidget(self.lower_stack)
        self.search_widget.onQuery.connect(self.on_query)

        self.search_widget.comboBox_History.currentTextChanged.connect(self.on_history_select)
        self.all_filmographies = dict()
        self.history = dict()

        self.file_path = os.path.expanduser("~") + "/" + "documents/VIAN/" + "search_queries.pickle"
        if os.path.isfile(self.file_path):
            try:
                with open(self.file_path, "rb") as f:
                    self.history = pickle.load(f)
            except:
                self.history = dict()

        for k in sorted(self.history.keys(),reverse=True):
            self.search_widget.comboBox_History.addItem(k)

    def on_query_result(self, obj):
        if obj['type'] == "keywords":
            self.keyword_widget.clear()
            for kwd in obj['data']['keywords']:
                voc = obj['data']['vocabularies'][kwd.vocabulary_id]
                cl_obj = obj['data']['cl_objs'][kwd.class_obj_id]
                word = obj['data']['vocabulary_words'][kwd.word_id]
                self.keyword_widget.add_unique_keyword(kwd, cl_obj, voc, word)
                self.visualizer.all_keywords[kwd.unique_keyword_id] = dict(keyword=kwd, voc=voc, cl_obj=cl_obj, word=word)
            self.keyword_widget.add_spacers()

        elif obj['type'] == "movies":
            self.query_result_widget.clear()
            filmographies = dict()
            for dbfilmography in obj['data']['filmographies']:
                filmographies[dbfilmography.project_id] = dbfilmography
            for dbproject in obj['data']['projects']:
                if dbproject.project_id in filmographies:
                    self.query_result_widget.add_result(dbproject,filmographies[dbproject.project_id])
                else:
                    self.query_result_widget.add_result(dbproject, None)
            self.lower_stack.setCurrentIndex(1)

        elif obj['type'] == "segments":
            self.visualizer.set_current_perspective(4)

    @pyqtSlot(str, str, int)
    def on_query(self, qtype, search_string, corpus_id):
        cl_obj_filters = self.keyword_widget.get_classification_object_filters()
        keyword_filters = self.keyword_widget.get_keyword_filters()
        filmography = self.keyword_widget.filmography_widget.get_filmography_query()
        self.visualizer.on_query(qtype, filmography, keyword_filters, cl_obj_filters, None)

        itm = [qtype + " " + str(datetime.datetime.strftime(datetime.datetime.now(), "%d-%m-%Y %H:%M:%S")), (qtype, filmography, keyword_filters, cl_obj_filters, None)]
        self.history[itm[0]] = itm[1]
        self.search_widget.comboBox_History.addItem(itm[0])
        with open(self.file_path, "wb") as f:
            pickle.dump(self.history, f)

    def on_history_select(self, text):
        text = self.search_widget.comboBox_History.currentText()
        print(text)
        if text in self.history:
            d = self.history[text]
            self.visualizer.on_query(d[0], d[1], d[2], d[3], d[4])



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

    def add_unique_keyword(self, ukw:DBUniqueKeyword, cl_obj:DBClassificationObject, voc:DBVocabulary, voc_word:DBVocabularyWord):
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

        if voc.category not in self.tabs_map[cl_obj.name]:
            tab = QScrollArea(stack)
            tab.setWidgetResizable(True)
            tab.setWidget(QWidget(tab))
            tab.widget().setLayout(QVBoxLayout(tab.widget()))
            stack.addTab(tab, voc.category)
            self.stack_map[cl_obj.name].addTab(tab, voc.category)
            self.tabs_map[cl_obj.name][voc.category] = tab
            self.voc_map[cl_obj.name][voc.category] = dict()
            tab.show()
        else:
            tab = self.tabs_map[cl_obj.name][voc.category]

        if voc.name not in self.voc_map[cl_obj.name][voc.category]:
            group = CheckBoxGroupWidget(self, voc.name)
            tab.widget().layout().addWidget(group)
            self.voc_map[cl_obj.name][voc.category][voc.name] = group
            group.show()
        else:
            group = self.voc_map[cl_obj.name][voc.category][voc.name]

        checkbox = WordCheckBox(None, voc_word, ukw)
        self.keyword_map[ukw.unique_keyword_id] = checkbox
        self.keyword_cl_obj_map[ukw.unique_keyword_id] = cl_obj_item
        group.add_checkbox(checkbox)
        checkbox.show()

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

class WordCheckBox(QCheckBox):
    def __init__(self, parent, word, unique_keyword):
        super(WordCheckBox, self).__init__(parent)
        self.word = word
        self.setText(word.name)
        self.unique_keyword = unique_keyword
        self.setTristate(True)


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


class QueryResultWidget(QWidget):
    onClosed = pyqtSignal()

    def __init__(self, parent, visualizer):
        super(QueryResultWidget, self).__init__(parent)
        path = os.path.abspath("qt_ui/visualizer/QueryResultWidget.ui")
        uic.loadUi(path, self)
        self.visualizer = visualizer
        self.btn_Close.clicked.connect(self.onClosed.emit)
        self.widget = QWidget(self.scrollArea)
        self.scrollArea.setWidget(self.widget)
        self.scrollArea.setWidgetResizable(True)
        self.widget.setLayout(QGridLayout())
        self.entries = []
        self.n_columns = 3

    def clear(self):
        for e in self.entries:
            e.deleteLater()
        self.entries = []

    def add_result(self, r, filmography):
        w = None
        if isinstance(r, DBProject):
            w = ProjectListEntry(self.widget, self.visualizer, None, r, filmography=filmography)

        if w is not None:
            lt = self.widget.layout()
            curr_x = len(self.entries) % self.n_columns
            curr_y = np.floor(len(self.entries) / self.n_columns)
            lt.addWidget(w, curr_y, curr_x)
            self.entries.append(w)



