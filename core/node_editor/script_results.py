from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
# from PyQt5.QtWebKitWidgets import QWebView
from core.data.containers import *
from core.gui.ewidgetbase import EDockWidget

VIS_TYPE_IMAGE = 0
VIS_TYPE_WEB = 1
VIS_TYPE_NONE = 2

class NodeEditorResults(EDockWidget):
    def __init__(self, main_window):
        super(NodeEditorResults, self).__init__(main_window,limit_size=False)
        path = os.path.abspath("qt_ui/NodeEditorResults.ui")
        uic.loadUi(path, self)
        self.setWindowTitle("Node Editor Results")

        self.result_widgets = []
        self.tab_results.clear()
        # self.tab_results = QTabWidget(self)

    def visualize(self, operation):
        if operation.result_visualization_type == VIS_TYPE_IMAGE:
            self.create_image_result(operation.result[0])
        elif operation.result_visualization_type == VIS_TYPE_WEB:
            self.create_web_result(operation.result[0])

        else:
            return

    def add_result_widget(self, widget):
        self.result_widgets.append(widget)
        self.tab_results.addTab(widget, widget.name)

    def create_image_result(self, qpixmap):
        widget = ImageResultWidget(self.tab_results, qpixmap)
        self.add_result_widget(widget)

    def create_web_result(self, html):
        widget = WebResultWidget(self.tab_results, html)
        self.add_result_widget(widget)


class ResultWidget(QWidget):
    def __init__(self, parent, name):
        super(ResultWidget, self).__init__(parent)
        self.name = name


class ImageResultWidget(ResultWidget):
    def __init__(self, parent, qpixmap):
        super(ImageResultWidget, self).__init__(parent, "Image Result")

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.pixm = None
        try:
            self.pixm = self.scene.addPixmap(qpixmap)
            rect = self.pixm.sceneBoundingRect()
            self.view.fitInView(rect, Qt.KeepAspectRatio)
        except:
            print "No Pixmap in Image Result Widget"



        self.setLayout(QHBoxLayout(self))

        self.layout().addWidget(self.view)

        self.show()

    def resizeEvent(self, QResizeEvent):
        super(ImageResultWidget, self).resizeEvent(QResizeEvent)
        if self.pixm is not None:
            rect = self.pixm.sceneBoundingRect()
            self.view.fitInView(rect, Qt.KeepAspectRatio)


class WebResultWidget(ResultWidget):
    def __init__(self, parent, html):
        super(WebResultWidget, self).__init__(parent, "Image Result")

        # self.view = QWebView(self)
        self.view.setHtml(html)
        self.setLayout(QHBoxLayout(self))
        self.layout().addWidget(self.view)
        self.view.setZoomFactor(0.5)

        self.show()

    # def resizeEvent(self, QResizeEvent):
    #     super(WebResultWidget, self).resizeEvent(QResizeEvent)
    #     rect = self.pixm.sceneBoundingRect()
    #     self.view.fitInView(rect, Qt.KeepAspectRatio)

