from core.gui.ewidgetbase import EDockWidget
from collections import namedtuple
from functools import partial
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

import numpy  as np

from core.data.containers import IAnalysisJobAnalysis
from core.data.interfaces import IProjectChangeNotify

FilterTuple = namedtuple("FilterTuple", ["name", "word_obj"])

class AnalysisResultsDock(EDockWidget):
    def __init__(self, main_window):
        super(AnalysisResultsDock, self).__init__(main_window, limit_size=False)
        self.setWindowTitle("Analysis Results")

        self.menu_display = self.inner.menuBar().addMenu("Display")
        self.a_fullscreen = self.menu_display.addAction("Fullscreen")
        self.a_fullscreen.triggered.connect(self.on_fullscreen)

        self.analysis_widget = None

    def set_analysis_widget(self, analysis_result_widget):
        self.setWidget(analysis_result_widget)
        self.analysis_widget = analysis_result_widget

    def on_fullscreen(self):
        view = AnalysisFullScreenWindow(self.main_window, self.analysis_widget)
        for v in self.analysis_widget.current_visualization:
            view.add_tab(v)
        view.select_tab(0)
        view.tab_selector.add_spacer()


class AnalysisResultsWidget(QWidget, IProjectChangeNotify):
    def __init__(self, parent, main_window):
        super(AnalysisResultsWidget, self).__init__(parent)
        self.main_window = main_window
        self.analysis_widget = QWidget(self)
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(self.analysis_widget)
        self.current_visualization = []
        self.current_analysis = None

        self.analysis_widget.setLayout(QHBoxLayout(self))

    def activate_analysis(self, analysis: IAnalysisJobAnalysis):
        self.clear_analysis_widget()
        self.current_analysis = analysis
        self.current_analysis.load_container(self.apply_analysis, sync=True)

    def apply_analysis(self):
        print("TEST, Applying Analysis")
        visualizations = self.current_analysis.get_visualization()
        print(visualizations)
        self.current_analysis.unload_container()
        if visualizations is not None:
            self.analysis_widget.layout().addWidget(visualizations[0].widget)
            self.current_visualization = visualizations
            self.current_visualization[0].widget.show()
        else:
            self.main_window.print_message("Visualization returned None", "Red")
            self.current_visualization = []

    def clear_analysis_widget(self):
        for c in self.analysis_widget.children():
            if isinstance(c, QWidget):
                c.close()
                c.deleteLater()

    def toggle_fullscreen(self, active):
        pass

    def on_changed(self, project, item):
        pass

    def on_loaded(self, project):
        self.clear_analysis_widget()
        pass

    def on_selected(self, sender, selected):
        if len(selected) > 0:
            if isinstance(selected[0], IAnalysisJobAnalysis):
                self.activate_analysis(selected[0])


class AnalysisFullScreenWindow(QMainWindow):
    def __init__(self, main_window, analysis_widget):
        super(AnalysisFullScreenWindow, self).__init__(main_window)
        self.setStyleSheet("AnalysisFullScreenWindow{background: rgb(30,30,30)}")
        # self.setWindowFlags(Qt.FramelessWindowHint)
        self.analysis_widget = analysis_widget
        self.tab_selector = AnalysisFullScreenTabSelector(self)
        self.tab_selector.move(0,0)
        self.tab_selector_width = 200
        self.filter_width = 300
        self.tab_selector_hover = HoverWidget(self)
        self.tab_selector_hover.resize(self.tab_selector_width, 0)

        self.btn_close_hint = QPushButton("Press ESC to Close", self)
        self.btn_close_hint.clicked.connect(self.close)

        self.main_window = main_window

        self.filter_section = AnalysisFullScreenFilterSection(self, self.main_window)
        self.filter_section_anim = QPropertyAnimation(self.filter_section, b"geometry")
        self.filter_section_anim.setStartValue(QRect(self.width(), 0, 0, self.height()))
        self.filter_section_anim.setEndValue(QRect(self.width() - self.filter_width, 0, self.filter_width, self.height()))
        self.filter_hover = HoverWidget(self)
        self.filter_hover.move(self.width() - 5, 0)
        self.filter_hover.resize(5, self.height())
        self.filter_hover.onEnter.connect(self.on_show_filter_tab)
        self.filter_section.onLeave.connect(self.on_hide_filter_tab)


        self.tabs = []
        self.current_tab = None

        self.tab_selector_anim = QPropertyAnimation(self.tab_selector, b"geometry")
        self.tab_selector_anim.setStartValue(QRect(0, 0, 0, 0))
        self.tab_selector_anim.setEndValue(QRect(0, 0, self.tab_selector_width, self.height()))
        self.tab_selector_hover.onEnter.connect(self.on_show_tab_selector)

        self.showFullScreen()

    def on_show_filter_tab(self):
        self.filter_section_anim.setDirection(self.filter_section_anim.Forward)
        self.filter_section_anim.start()

    def on_hide_filter_tab(self):
        self.filter_section_anim.setDirection(self.filter_section_anim.Backward)
        self.filter_section_anim.start()

    def on_show_tab_selector(self):
        self.tab_selector_anim.setDirection(self.tab_selector_anim.Forward)
        self.tab_selector_anim.start()

    def on_hide_tab_selector(self):
        self.tab_selector_anim.setDirection(self.tab_selector_anim.Backward)
        self.tab_selector_anim.start()

    def add_tab(self, tab):
        self.tabs.append(tab)
        self.tab_selector.add_tab(tab.name, len(self.tabs) - 1)

    def select_tab(self, idx):
        if idx > (len(self.tabs) - 1):
            return
        if self.current_tab is not None:
            self.current_tab.hide()
        self.current_tab = self.tabs[idx].widget
        self.setCentralWidget(self.current_tab)
        self.tab_selector_hover.raise_()
        self.tab_selector.raise_()
        self.filter_section.raise_()
        self.filter_hover.raise_()
        self.tab_selector_anim.setEndValue(QRect(0, 0, self.tab_selector_width, self.height()))
        self.current_tab.show()

    def keyPressEvent(self, a0: QKeyEvent):
        if a0.key() == Qt.Key_Escape:
            self.close()

    def resizeEvent(self, a0: QResizeEvent):
        super(AnalysisFullScreenWindow, self).resizeEvent(a0)
        self.btn_close_hint.move(self.width() - 200, self.height() - 50)
        self.btn_close_hint.resize(180, 30)
        self.tab_selector_anim.setEndValue(QRect(0, 0, self.tab_selector_width,self.height()))
        self.tab_selector_hover.resize(10, self.height())

        self.filter_hover.move(self.width() - 10, 0)
        self.filter_hover.resize(10, self.height())

        self.filter_section.move(0, 0)
        self.filter_section.resize(0, self.height())
        self.filter_section_anim.setStartValue(QRect(self.width(), 0, 0, self.height()))
        self.filter_section_anim.setEndValue(QRect(self.width() - self.filter_width, 0, self.filter_width, self.height()))


class HoverWidget(QWidget):
    onEnter = pyqtSignal()
    onLeave = pyqtSignal()

    def __init__(self, parent):
        super(HoverWidget, self).__init__(parent)
        self.setStyleSheet("QWidget {background: rgb(100,100,100)}")
        self.hovered = False
        self.show()

    def enterEvent(self, a0: QEvent):
        super(HoverWidget, self).enterEvent(a0)
        self.hovered = True
        self.onEnter.emit()

    def leaveEvent(self, a0: QEvent):
        super(HoverWidget, self).leaveEvent(a0)
        self.hovered = False
        self.onLeave.emit()

    def paintEvent(self, a0: QPaintEvent):
        qp = QPainter(self)
        qp.begin(self)
        if self.hovered:
            qp.fillRect(self.rect(), QColor(150, 150, 150, 200))
        else:
            qp.fillRect(self.rect(), QColor(100,100,100,100))
        qp.end()


class AnalysisFullScreenTabSelector(QWidget):
    def __init__(self, fullscreen_window):
        super(AnalysisFullScreenTabSelector, self).__init__(fullscreen_window)
        self.fullscreen_window = fullscreen_window
        self.setLayout(QVBoxLayout(self))
        self.resize(100, fullscreen_window.height())
        self.button_height = 100
        self.hovered = False

        self.show()

    def add_tab(self, name, idx):
        btn = QPushButton(name, self)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        btn.setStyleSheet("QPushButton{border-radius: 2px}")
        btn.setFixedHeight(self.button_height)
        btn.clicked.connect(partial(self.fullscreen_window.select_tab, idx))
        self.layout().addWidget(btn)

    def add_spacer(self):
        self.layout().addItem(QSpacerItem(10,10,QSizePolicy.Preferred, QSizePolicy.Expanding))

    def leaveEvent(self, a0: QEvent):
        self.fullscreen_window.on_hide_tab_selector()

    def paintEvent(self, a0: QPaintEvent):
        super(AnalysisFullScreenTabSelector, self).paintEvent(a0)
        qp = QPainter()
        qp.begin(self)
        qp.fillRect(self.rect(), QColor(28, 28, 28, 100))
        qp.end()


class AnalysisFullScreenFilterSection(QWidget):
    onLeave = pyqtSignal()

    def __init__(self, fullscreen_window, main_window):
        super(AnalysisFullScreenFilterSection, self).__init__(fullscreen_window)
        self.fullscreen_window = fullscreen_window
        self.main_window = main_window
        self.setAttribute(Qt.WA_AlwaysStackOnTop)
        self.setLayout(QVBoxLayout(self))
        self.filter_model = None
        self.filters = []
        self.scrollarea = QScrollArea(self)
        self.scrollarea.setWidget(QWidget(self))
        self.scrollarea.widget().resize(180, 2000)
        self.layout().addWidget(self.scrollarea)
        self.scrollarea.widget().setLayout(QVBoxLayout(self))
        self.scrollarea.widget().layout().setSpacing(2)
        self.add_filter_menu()
        self.scrollarea.widget().layout().addItem(QSpacerItem(10,10, QSizePolicy.Preferred, QSizePolicy.Expanding))

        self.scrollarea.widget().resize(self.fullscreen_window.filter_width - 20, (100 * len(self.main_window.project.vocabularies)))
        self.scrollarea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollarea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show()


    def add_filter_menu(self):
        c = 0
        project = self.main_window.project
        for voc in project.vocabularies:
            self.scrollarea.widget().layout().addWidget(FilterCategory(self, voc))
            if c == 30:
                break
            else:
                c+=1

    def leaveEvent(self, a0: QEvent):
        super(AnalysisFullScreenFilterSection, self).leaveEvent(a0)
        self.onLeave.emit()

    def paintEvent(self, a0: QPaintEvent):
        super(AnalysisFullScreenFilterSection, self).paintEvent(a0)
        qp = QPainter()
        qp.begin(self)
        qp.fillRect(self.rect(), QColor(28,28,28,100))
        qp.end()

    def enlarge(self, size):
        self.scrollarea.widget().resize(self.scrollarea.widget().width(), np.clip(self.scrollarea.widget().height() + size, self.height(), None))


class FilterCategory(QWidget):
    def __init__(self, parent, voc):
        super(FilterCategory, self).__init__(parent)
        self.voc = voc
        self.filter_section = parent
        self.setStyleSheet("QPushButton{border-radius: 0px;}")
        self.setLayout(QVBoxLayout(self))
        self.btn_expand = QPushButton(voc.name, self)
        self.btn_expand.clicked.connect(self.on_expand)
        self.btn_expand.setFixedHeight(30)
        self.layout().addWidget(self.btn_expand)
        self.w_words = QWidget(self)
        self.layout().addWidget(self.w_words)
        self.w_words.setLayout(QVBoxLayout(self.w_words))
        self.entries = []
        self.is_expanded = False
        # self.w_words.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        for w in voc.get_vocabulary_as_list():
            cb = QCheckBox(w.name, self.w_words)
            self.entries.append(cb)
            self.w_words.layout().addWidget(cb)
            cb.show()

        self.show()
        self.collapse()


    def on_expand(self):
        if self.is_expanded:
            self.collapse()
        else:
            self.expand()

    def on_filter(self, word):
        pass

    def collapse(self):
        for cb in self.entries:
            cb.hide()
        self.is_expanded = False
        self.filter_section.enlarge(-(len(self.entries * 150)))

    def expand(self):
        for cb in self.entries:
            cb.show()
        self.is_expanded = True
        self.filter_section.enlarge(len(self.entries * 150))




