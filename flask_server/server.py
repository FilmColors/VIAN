import os
import cv2
from functools import partial

from PyQt5.QtCore import QThread, QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile, QWebEnginePage

from flask import Flask, render_template, send_file, url_for

from core.gui.ewidgetbase import EDockWidget
from core.container.project import VIANProject, Screenshot, Segment
from core.analysis.analysis_import import ColorFeatureAnalysis, ColorPaletteAnalysis
from core.data.computation import lab_to_lch, lab_to_sat, ms2datetime

app = Flask(__name__)
app.root_path = os.path.split(__file__)[0]

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class ScreenshotData:
    def __init__(self):
        self.a = []
        self.b = []
        self.urls = []
        self.saturation = []
        self.luminance = []
        self.chroma = []
        self.hue = []
        self.time = []
        self.uuids = []

        # self.palettes = []


class ServerData:
    def __init__(self):
        self.project = None #type: VIANProject
        self._screenshot_cache = dict(uuids = set(), has_changed = False, data=ScreenshotData())

    def set_project(self, project:VIANProject):
        self._screenshot_cache = dict(uuids = set(), has_changed = False, data=ScreenshotData())

        self.project = project
        # self.project.onProjectChanged.connect(partial(self.update_screenshot_data))
        self.project.onScreenshotAdded.connect(self.on_screenshot_added)
        self.project.onAnalysisAdded.connect(partial(self.update_screenshot_data))

        self.project.onAnalysisAdded.connect(partial(self.update_screenshot_data))
        for s in self.project.screenshots:
            s.onScreenshotChanged.connect(partial(self.update_screenshot_data))
        self.update_screenshot_data()


    def on_screenshot_added(self, s:Screenshot):
        s.onScreenshotChanged.connect(partial(self.update_screenshot_data))
        self.update_screenshot_data()


    def update_screenshot_data(self):
        a = []
        b = []
        chroma = []
        luminance = []
        saturation = []
        time = []
        hue = []

        # palettes = []

        uuids = []
        for i, s in enumerate(self.project.screenshots):
            t = s.get_connected_analysis(ColorFeatureAnalysis)
            if len(t) > 0:
                arr = t[0].get_adata()['color_lab']
                d = arr.tolist()
                a.append(d[1])
                b.append(d[2])
                uuids.append(s.unique_id)
                time.append(ms2datetime(s.get_start()))
                lch = lab_to_lch(arr)
                luminance.append(float(arr[0]))
                chroma.append(float(lch[1]))
                hue.append(float(lch[2]))
                saturation.append(float(lab_to_sat(arr)))

            # t2 = s.get_connected_analysis(ColorPaletteAnalysis)
            # if len(t2) > 0:
            #     arr = t[0].get_adata()

        data = ScreenshotData()

        data.a = a
        data.b = b
        data.chroma = chroma
        data.luminance = luminance
        data.saturation = saturation
        data.hue = hue
        data.time = time

        data.uuids = uuids

        self._screenshot_cache['has_changed'] = True
        self._screenshot_cache['data'] = data
        self.export_screenshots()


    def screenshot_url(self, s:Screenshot = None, uuid = None):
        if self.project is None:
            return
        if uuid is None:
            return os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), s.unique_id + ".jpg")
        return os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), uuid + ".jpg")


    def export_screenshots(self):
        ps = []
        rdir = os.path.join(self.project.export_dir, "screenshot_thumbnails")
        if not os.path.isdir(rdir):
            os.mkdir(rdir)

        for s in self.project.screenshots:
            if s.img_movie.shape[0] > 100:
                p = os.path.join(rdir, s.unique_id + ".jpg")
                if not os.path.isfile(p):
                    cv2.imwrite(p, s.img_movie)
                ps.append(p)
        return ps

    def clear(self):
        self.project = None #type: VIANProject
        self._screenshot_cache = dict(uuids = set(), has_changed = False, data=ScreenshotData())



_server_data = ServerData()


class FlaskServer(QObject):
    def __init__(self, parent):
        super(FlaskServer, self).__init__(parent)
        self.app = app

    @pyqtSlot()
    def run_server(self):
        self.app.run()

    def on_loaded(self, project):
        global _server_data
        _server_data.set_project(project)

    def on_closed(self):
        global _server_data
        _server_data.clear()

    def on_changed(self, project, item):
        pass

    def get_project(self):
        return None

    def on_selected(self, sender, selected):
        pass



class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: 'QWebEnginePage.JavaScriptConsoleMessageLevel', message: str, lineNumber: int, sourceID: str) -> None:
        print(message)

class FlaskWebWidget(EDockWidget):
    def __init__(self, main_window):
        super(FlaskWebWidget, self).__init__(main_window, False)
        self.setWindowTitle("WebView Debug")
        self.view = QWebEngineView(self)
        self.view.setPage(WebPage())
        self.view.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.view.settings().setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        self.setWidget(self.view)


    def set_url(self, url):
        QWebEngineProfile.defaultProfile().clearAllVisitedLinks()
        QWebEngineProfile.defaultProfile().clearHttpCache()

        self.view.setUrl(QUrl(url))
        self.view.reload()

    def reload(self):
        print("Reload")
        self.view.reload()


@app.route("/")
def index():
    return render_template("color_dt.tmpl.html")


@app.route("/screenshot_vis/")
def screenshot_vis():
    return render_template("screenshot_vis.tmpl.html")


@app.route("/screenshot/<string:uuid>")
def screenshot(uuid):
    return send_file(_server_data.screenshot_url(uuid=uuid))


@app.route("/screenshot-data/")
def screenshot_data():
    if _server_data.project is None:
        return dict(changes=False, data = ScreenshotData().__dict__)
    else:
        if _server_data._screenshot_cache['has_changed']:
            _server_data._screenshot_cache['data'].urls = [url_for("screenshot", uuid=u) for u in _server_data._screenshot_cache['data'].uuids]
            _server_data._screenshot_cache['has_changed'] = False
            return dict(changes=True, data=_server_data._screenshot_cache['data'].__dict__)
        else:
            return dict(changes=False, data=_server_data._screenshot_cache['data'].__dict__)

if __name__ == '__main__':
    app.debug = True
    app.run()