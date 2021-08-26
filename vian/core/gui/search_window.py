from PyQt5.QtWidgets import QMainWindow, QWidget, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QScrollArea, QFrame, QGridLayout, QCompleter, QPushButton
from PyQt5.QtCore import pyqtSlot, pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QPixmap, QMouseEvent, QPainter, QColor, QPen

from vian.core.container.project import Segment, VIANProject, Screenshot, UniqueKeyword, Annotatable


class SearchWindow(QMainWindow):
    """
    This is a search window which can be opened in VIAN to query the current project
    """

    def __init__(self, parent):
        super(SearchWindow, self).__init__(parent)
        self.main_window = parent
        self.project = None
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.setWindowFlags(Qt.Popup|Qt.FramelessWindowHint)

        self.central = QWidget(self)
        self.central.setLayout(QVBoxLayout(self))

        self.line_edit_input = QLineEdit(self)
        self.w_search_line = QWidget(self)
        self.w_search_line.setLayout(QHBoxLayout(self.w_search_line))
        self.w_search_line.layout().addWidget(QLabel("Search: ", self.w_search_line))
        self.w_search_line.layout().addWidget(self.line_edit_input)
        self.central.layout().addWidget(self.w_search_line)

        self.w_result = ResultWidget(self, self)
        self.central.layout().addWidget(self.w_result)
        self.w_result.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.setCentralWidget(self.central)

        self.project = VIANProject()
        self.last_results = []

        self.line_edit_input.textChanged.connect(self.on_search)
        self.completer = QCompleter()
        self.keyword_mapping = dict()

    def on_search(self):
        if self.project is None:
            return

        s_notes = True
        s_body = True
        s_keywords = True

        t = self.line_edit_input.text().lower()
        if t == "":
            self.show_result([])
            return

        result = []
        kwds_to_search = []
        if s_keywords:
            kwds = []
            for e in self.project.experiments:
                kwds.extend(e.get_unique_keywords())

            kwds_to_search = []
            for k in kwds:
                if t in k.word_obj.name:
                    kwds_to_search.append(k)

        searchable = self.project.get_annotations()
        for s in searchable:
            if s_notes and t in s.get_notes().lower():
                result.append((s, "notes", s.get_notes()))
            if s_body and isinstance(s, Annotatable):
                for an in s.get_annotations():
                    if t in an.to_string().lower():
                        result.append((s, "body", an.to_string()))
                        break

            for k in kwds_to_search:
                if k in s.tag_keywords:
                    result.append((s, "keywords"))
                    break

        t = self.line_edit_input.text()
        for k in t.split(" "):
            if "Keyword:" in k and k in self.keyword_mapping:
                keyword = self.keyword_mapping[k] #type:UniqueKeyword
                for c in keyword.tagged_containers:
                    result.append((c, "keywords"))
        self.show_result(result)

    def show_result(self, result):
        self.w_result.clear()
        self.clear_highlighted()

        for r in result:
            self.last_results.append(r[0])
            r[0].set_classification_highlight(True)
            self.w_result.add_entry(r[0], self.main_window)

    def clear_highlighted(self):
        for r in self.last_results:
            r.set_classification_highlight(False)
        self.last_results = []


    @pyqtSlot(object)
    def on_loaded(self, project):
        self.project = project

    def on_close(self):
        self.project = None

    @pyqtSlot(object)
    def on_go_to(self, container):
        self.main_window.player.set_media_time(container.get_start())
        self.hide()

    def showEvent(self, a0) -> None:
        super(SearchWindow, self).showEvent(a0)
        self.keyword_mapping = dict()
        for e in self.project.experiments:
            for k in e.get_unique_keywords():
                self.keyword_mapping["Keyword:" + k.get_full_name()] = k

        self.completer = QCompleter(self.keyword_mapping.keys())
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.line_edit_input.setCompleter(self.completer)

        self.line_edit_input.setFocus()


class ResultWidget(QWidget):
    def __init__(self, parent, wnd):
        super(ResultWidget, self).__init__(parent)
        self.dialog = wnd
        self.setLayout(QVBoxLayout())
        self.list = QWidget(self)
        self.area = QScrollArea(self)
        self.area.setWidget(self.list)
        self.area.setWidgetResizable(True)

        self.list.setLayout(QVBoxLayout())
        self.layout().addWidget(self.area)

        self.span = QWidget(self.list)
        self.list.layout().addWidget(self.span)
        self.span.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.hovered = False
        self.entries = []

    def add_entry(self, container, main_window):
        self.list.layout().removeWidget(self.span)
        e = Entry(self.list, container)
        e.onDoubleClicked.connect(self.dialog.on_go_to)
        self.entries.append(e)
        self.list.layout().addWidget(e)
        self.list.layout().addWidget(self.span)
        e.show()

    def clear(self):
        for e in self.entries:
            e.close()
        self.entries = []


class Entry(QFrame):
    onDoubleClicked = pyqtSignal(object)

    def __init__(self, parent, container):
        super(Entry, self).__init__(parent)
        self.container = container

        self.setStyleSheet("QFrame{background: rgb(17, 17, 17)}")

        self.setLayout(QVBoxLayout())
        self.label = QLabel(self)
        self.preview = QWidget(self)
        self.layout().addWidget(self.preview)
        self.preview.setLayout(QHBoxLayout(self.preview))

        self.layout().addWidget(self.label)
        self.label.setText(str(self.container.__class__.__name__) + ": " + self.container.get_name())

        self.project = VIANProject
        self.hovered = False
        if isinstance(self.container, Segment):
            for i, t in enumerate(self.container.project.get_screenshots_of_segment(self.container)):
                (qimage, qpixmap) = t.get_preview()

                lbl = QLabel(self)
                lbl.setPixmap(qpixmap.scaledToHeight(100))
                self.preview.layout().addWidget(lbl)
                if i == 10:
                    break
            lbl_annotation = QLabel("Body: " + self.container.get_first_annotation_string(), self)
            self.layout().addWidget(lbl_annotation)
        elif isinstance(self.container, Screenshot):
            (qimage, qpixmap) = self.container.get_preview()
            lbl = QLabel(self)
            lbl.setPixmap(qpixmap.scaledToHeight(100))
            self.preview.layout().addWidget(lbl)

        lbl_notes = QLabel("Notes: " + self.container.get_notes(), self)
        self.layout().addWidget(lbl_notes)

    def paintEvent(self, a0) -> None:
        super(Entry, self).paintEvent(a0)
        if self.hovered:
            qp = QPainter()
            pen = QPen()

            qp.begin(self)
            pen.setColor(QColor(255, 160, 47, 100))
            pen.setWidth(5)
            qp.setPen(pen)
            # qp.fillRect(self.rect(), QColor(255, 160, 47, 50))
            qp.drawRect(self.rect())

            qp.end()

    def enterEvent(self, a0) -> None:
        super(Entry, self).enterEvent(a0)
        self.hovered = True
        self.update()

    def leaveEvent(self, a0) -> None:
        super(Entry, self).leaveEvent(a0)
        self.hovered = False
        self.update()

    def mouseDoubleClickEvent(self, a0: QMouseEvent) -> None:
        self.onDoubleClicked.emit(self.container)


