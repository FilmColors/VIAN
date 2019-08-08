from core.visualization.basic_vis import IVIANVisualization
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import numpy as np
from core.data.computation import rotate
from collections import namedtuple

DotPlotRawData = namedtuple("DotPlotRawData", ["x", "y", "z", "col", "mime_data", "curr_grid"])

class DotPlot(QGraphicsView, IVIANVisualization):
    def __init__(self, parent, title ="", naming_fields = None):
        QGraphicsView.__init__(self, parent)
        IVIANVisualization.__init__(self, naming_fields)
        self.naming_fields['plot_name'] = "dot_plot"
        self.setRenderHint(QPainter.Antialiasing)
        self.setMouseTracking(True)
        self.setStyleSheet("QWidget:focus{border: rgb(30,30,30); } QWidget:{border: rgb(30,30,30);}")
        self.setBackgroundBrush(QColor(30, 30, 30))
        self.setScene(QGraphicsScene(self))
        self.curr_scale = 1.0
        self.ctrl_is_pressed = False
        self.magnification = 1.0

        self.grid_color = QColor(200, 200, 200, 150)

        self.pos_scale = 1.0

        self.curr_angle = 0

        self.curr_grid = "Default"
        self.n_grid = 12
        self.font_size = 4
        self.index_uid = dict()
        self.dot_size = 20
        self.grid = []
        self.lbl_max = None
        self.grid_line_width = 1.0

        self.raw_data = []
        self.points = []
        self.compass = QGraphicsPathItem()

    def clear_view(self):
        self.scene().clear()
        self.raw_data = []
        self.points = []
        self.grid = []
        self.index_uid = dict()

    def add_grid(self, grid_type = "Default"):
        self.curr_grid = grid_type
        for g in self.grid:
            self.scene().removeItem(g)
        self.grid = []
        if grid_type == "LA":
            pen = QPen()
            pen.setWidthF(self.grid_line_width)
            pen.setColor(self.grid_color)

            font = QFont()
            font.setPointSize(self.font_size)

            x0 = -128
            x1 = 128
            y0 = -128
            y1 = 128

            for x in range(-128, 128, 1):
                if x % 20 == 0:
                    self.scene().addLine(x, y0, x, y1, pen)
                    text = self.scene().addText(str(round(x, 0)), font)
                    text.setPos(x, 130)
                    text.setDefaultTextColor(self.grid_color)
                    self.grid.append(text)

            for x in range(-128, 128, 1):
                if x % 20 == 0:
                    self.scene().addLine(x0, x, x1, x, pen)
                    text = self.scene().addText(str(round(x, 0)), font)
                    text.setPos(x, 130)
                    text.setDefaultTextColor(self.grid_color)
                    self.grid.append(text)

            self.draw_compass()

        elif grid_type == "AB":
            pen = QPen()
            pen.setWidthF(self.grid_line_width / 10)
            pen.setColor(self.grid_color)

            font = QFont()
            font.setPointSize(self.font_size * self.magnification * 2)

            for i in range(7):
                self.circle0 = self.scene().addEllipse(QRectF(0,
                                                              0,
                                                              (255 / 6 * i),
                                                              (255 / 6 * i)),
                                                       pen)
                q = -(128 / 6 * i)
                self.circle0.setPos(q, q)
                self.grid.append(self.circle0)

            for i in range(self.n_grid):
                x = 128 * np.cos(i * (2 * np.pi / self.n_grid))
                y = 128 * np.sin(i * (2 * np.pi / self.n_grid))
                l = self.scene().addLine(0, 0, x, y, pen)
                self.grid.append(l)
            lbla = self.scene().addText("-B", font)
            lbla.setDefaultTextColor(self.grid_color)
            lbla.setPos(- lbla.boundingRect().width() / 2, 130 * self.magnification)
            self.grid.append(lbla)

            lblb = self.scene().addText("A", font)
            lblb.setDefaultTextColor(self.grid_color)
            lblb.setPos(130 * self.magnification, - lblb.boundingRect().height() / 2)
            self.grid.append(lblb)

            self.lbl_max = self.scene().addText(str(round(128 / self.pos_scale, 0)), font)
            self.lbl_max.setDefaultTextColor(self.grid_color)
            self.lbl_max.setPos(130 * self.magnification, + (self.lbl_max.boundingRect().height()))

            lbla = self.scene().addText("B", font)
            lbla.setDefaultTextColor(self.grid_color)
            lbla.setPos(- lbla.boundingRect().width() / 2, -130 * self.magnification - lbla.boundingRect().height())
            self.grid.append(lbla)

            lblb = self.scene().addText("-A", font)
            lblb.setDefaultTextColor(self.grid_color)
            lblb.setPos(-130 * self.magnification - 2 * lbla.boundingRect().width(), - lblb.boundingRect().height() / 2)
            self.grid.append(lblb)

            self.circle0.show()

        for g in self.grid:
            g.setZValue(-100)

        self.setSceneRect(self.scene().itemsBoundingRect())

    def add_point(self, x, y, z = 0, col = QColor(255,255,255,30), uid = None):
        s = self.dot_size / 10
        hs = s / 2

        p = QPen()
        p.setColor(col)
        p.setWidth(0.1)

        if self.curr_grid == "LA":
            yt = 128 - y
            point = self.scene().addEllipse(x * self.pos_scale - hs, yt * self.pos_scale - hs, s, s, p, QBrush(col))
        else:
            point = self.scene().addEllipse(x* self.pos_scale - hs, y * self.pos_scale - hs, s, s,p,QBrush(col))

        point.setZValue(z)
        self.points.append(point)
        if uid is not None:
            self.index_uid[uid] = (point, len(self.raw_data))

        self.raw_data.append(DotPlotRawData(x=x, y = y, z = z, col=col, mime_data=None, curr_grid=self.curr_grid))

    def draw_compass(self):
        p = QPen()
        p.setColor(self.grid_color)
        p.setWidth(0.1)
        f = QFont()
        f.setPointSize(5)

        path = QPainterPath(QPointF(0,0))
        path.addEllipse(QRectF(95,95,30,30))
        path.moveTo(110, 95)
        path.lineTo(110, 125)
        path.addText(105, 93, f, "-A")
        path.addText(105, 133, f, "+A")
        path.addText(85, 112, f, "-B")
        path.addText(127, 112, f, "+B")

        t = QTransform()
        t.rotate(self.curr_angle)

        pitem = self.scene().addPath(path, p)
        pitem.setTransform(t)
        self.compass = pitem

    def frame_default(self):
        rect = self.scene().itemsBoundingRect()
        rect.adjust(-10, -10, 20, 20)
        self.scene().setSceneRect(rect)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def create_title(self):
        if self.title == "":
            return
        font = QFont()
        font.setPointSize(self.font_size * self.magnification)
        t = self.scene().addText(self.title, font)
        t.setPos((self.range_x[0] + self.range_x[1]) / 2 * self.magnification, -20 * self.magnification)
        t.setDefaultTextColor(QColor(200, 200, 200, 200))

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = True
            event.ignore()
        elif event.key() == Qt.Key_F:
            self.frame_default()
        else:
            event.ignore()

    def keyReleaseEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Control:
            self.ctrl_is_pressed = False
        else:
            event.ignore()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            menu = QMenu(self)
            a_export = menu.addAction("Export")
            a_export.triggered.connect(self.export)
            menu.popup(self.mapToGlobal(event.pos()))
        else:
            event.ignore()

    def wheelEvent(self, event: QWheelEvent):
        if self.ctrl_is_pressed:
            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)

            old_pos = self.mapToScene(event.pos())

            h_factor = 1.1
            l_factor = 0.9

            viewport_size = self.mapToScene(QPoint(self.width(), self.height())) - self.mapToScene(QPoint(0, 0))

            if event.angleDelta().y() > 0.0 and self.curr_scale < 100:
                self.scale(h_factor, h_factor)
                self.curr_scale *= h_factor

            elif event.angleDelta().y() < 0.0 and self.curr_scale > 0.001:
                self.curr_scale *= l_factor
                self.scale(l_factor, l_factor)

            cursor_pos = self.mapToScene(event.pos()) - old_pos

            self.translate(cursor_pos.x(), cursor_pos.y())

        else:
            super(QGraphicsView, self).wheelEvent(event)

    def rotate_view(self, angle_deg):
        self.curr_angle = angle_deg
        angle = (angle_deg / 360 * np.pi) * 2
        s = self.dot_size / 10
        hs = s / 2
        for idx, itm in enumerate(self.raw_data):
            x, z = rotate((0, 0), (itm.x, itm.z), angle)
            try:
                if self.curr_grid == "LA":
                    yt = 128 - itm.y
                else:
                    yt = itm.y
                self.points[idx].setRect(x-hs, yt-hs, s, s)
                self.points[idx].setZValue(z)
            except:
                continue

        t = QTransform()
        x, y = -110, -110
        t.translate(-x, -y)
        t.rotate(self.curr_angle)
        t.translate(x, y)
        self.compass.setTransform(t)

    def set_alpha(self, a):
        for itm in self.points:
            itm.setOpacity(a / 255)

    def set_size(self, s):
        os = self.dot_size / 10
        hos = os / 2

        self.dot_size = s
        ns = self.dot_size / 10
        hns = ns / 2

        for p in self.points:
            x = p.rect().x()
            y = p.rect().y()
            p.setRect(x + hos - hns, y + hos - hns, ns, ns)

    def update_item(self, uid, x, y, z, col = None):
        if uid in self.index_uid:
            itm = self.index_uid[uid]
            q = self.raw_data.pop(itm[1])
            self.raw_data.insert(itm[1], DotPlotRawData(x=x, y=y, z=z, col=col, mime_data=q.mime_data,
                                                        curr_grid=self.curr_grid))
            if col is None:
                col = q.col

            s = self.dot_size / 10
            hs = s / 2

            p = QPen()
            p.setColor(col)
            p.setWidth(0.1)

            if self.curr_grid == "LA":
                yt = 128 - y
                itm[0].setPos(x - hs, yt - hs)
                itm[0].setZValue(z)
            else:
                itm[0].setPos(x - hs, y - hs)
                itm[0].setZValue(z)

    def set_range_scale(self, value = None):
        if value is not None:
            self.pos_scale = value / 100

        # font = QFont()
        # font.setPointSize(10 * self.magnification)
        #
        # if self.lbl_max is not None:
        #     self.scene().removeItem(self.lbl_max)
        #     self.lbl_max = None
        # self.lbl_max = self.scene().addText(str(round(128 / self.pos_scale, 0)), font)
        # self.lbl_max.setDefaultTextColor(self.grid_color)
        # self.lbl_max.setPos(130 * self.magnification, + (self.lbl_max.boundingRect().height()))

        s = self.dot_size / 10
        hs = s / 2

        for i, p in enumerate(self.points):
            x = self.raw_data[i].x * self.pos_scale
            y = self.raw_data[i].y * self.pos_scale
            z = self.raw_data[i].z * self.pos_scale
            if self.curr_grid == "LA":
                yt = - y
                p.setPos(x - hs, yt - hs)
                p.setZValue(z)
            else:
                p.setPos(x - hs, y)
                p.setZValue(z)

    def get_raw_data(self):
        return self.raw_data

    def apply_raw_data(self, raw_data):
        for i, r in enumerate(raw_data):
            if i == 0:
                self.add_grid(r.curr_grid)
            self.add_point(r.x, r.y, r.z, r.col)

    def render_to_image(self, background: QColor, size: QSize):
        """
        Renders the scene content to an image, alternatively if return iamge is set to True, 
        the QImage is returned and not stored to disc
        :param return_image: 
        :return: 
        """

        raw = self.raw_data.copy()
        self.clear_view()
        self.apply_raw_data(raw)

        self.scene().setSceneRect(self.scene().itemsBoundingRect())

        t_size = self.sceneRect().size().toSize()
        image = QImage(size, QImage.Format_ARGB32)
        image.fill(background)

        painter = QPainter()
        painter.begin(image)
        self.scene().render(painter)
        painter.end()

        return image

    def get_param_widget(self, w=None):
        if w is None:
            w = DotPlotControls(self)

        w.slider_xscale.valueChanged.connect(self.set_range_scale)
        w.slider_angle.valueChanged.connect(self.rotate_view)
        w.slider_alpha.valueChanged.connect(self.set_alpha)
        w.slider_size.valueChanged.connect(self.set_size)

        self.set_range_scale(w.slider_xscale.value())
        self.rotate_view(w.slider_angle.value())
        self.set_alpha(w.slider_alpha.value())
        self.set_size(w.slider_size.value())

        return w

    def get_scene(self):
        return self.scene()


class DotPlotControls(QWidget):
    def __init__(self, plot):
        super(DotPlotControls, self).__init__()
        self.setLayout(QVBoxLayout())

        hl1 = QHBoxLayout(self)
        hl1.addWidget(QLabel("Range Scale:", self))

        self.slider_xscale = QSlider(Qt.Horizontal, self)
        self.slider_xscale.setRange(1, 1000)
        self.slider_xscale.setValue(100)

        hl1.addWidget(self.slider_xscale)

        hl3 = QHBoxLayout(self)
        hl3.addWidget(QLabel("View Angle:", self))

        self.slider_angle = QSlider(Qt.Horizontal, self)
        self.slider_angle.setRange(0, 360)


        hl3.addWidget(self.slider_angle)

        self.angle_sp = QSpinBox(self)
        self.angle_sp.setRange(1, 360)
        self.angle_sp.setValue(0)

        hl3.addWidget(self.angle_sp)

        hl4 = QHBoxLayout(self)
        hl4.addWidget(QLabel("Dot Alpha:", self))

        self.slider_alpha = QSlider(Qt.Horizontal, self)
        self.slider_alpha.setRange(0, 255)
        self.slider_alpha.setValue(100)

        hl4.addWidget(self.slider_alpha)

        self.angle_a = QSpinBox(self)
        self.angle_a.setRange(1, 255)
        self.angle_a.setValue(100)

        hl4.addWidget(self.angle_a)

        hl5 = QHBoxLayout(self)
        hl5.addWidget(QLabel("Dot Size:", self))

        self.slider_size = QSlider(Qt.Horizontal, self)
        self.slider_size.setRange(1, 50)
        self.slider_size.setValue(plot.dot_size)

        hl5.addWidget(self.slider_size)

        self.sp_size = QSpinBox(self)
        self.sp_size.setRange(1, 50)
        self.sp_size.setValue(plot.dot_size)

        hl5.addWidget(self.sp_size)

        self.angle_sp.valueChanged.connect(self.slider_angle.setValue)
        self.slider_angle.valueChanged.connect(self.angle_sp.setValue)
        self.angle_a.valueChanged.connect(self.slider_alpha.setValue)
        self.slider_alpha.valueChanged.connect(self.angle_a.setValue)
        self.sp_size.valueChanged.connect(self.slider_size.setValue)
        self.slider_size.valueChanged.connect(self.sp_size.setValue)

        self.layout().addItem(hl1)
        self.layout().addItem(hl3)
        self.layout().addItem(hl4)
        self.layout().addItem(hl5)

