import os
import cv2
from functools import partial
import json

import numpy as np

from PyQt5.QtCore import QThread, QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt5 import QtGui
from flask import Flask, render_template, send_file, url_for, jsonify

from core.data.log import log_error, log_info
from core.gui.ewidgetbase import EDockWidget
from core.container.project import VIANProject, Screenshot, Segment
from core.analysis.analysis_import import ColorFeatureAnalysis, ColorPaletteAnalysis, get_palette_at_merge_depth
from core.data.computation import lab_to_lch, lab_to_sat, ms2datetime

app = Flask(__name__)
app.root_path = os.path.split(__file__)[0]
log_info("FLASK ROOT", app.root_path)
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# import logging
# log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)

import mimetypes
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/json', '.json')


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

        self.palettes = []


class ServerData:
    def __init__(self):
        self.project = None #type: VIANProject
        self._screenshot_cache = dict(uuids = set(), has_changed = False, data=ScreenshotData())

        self._needs_update = False
        self._project_closed = False

    def set_project(self, project:VIANProject):
        self._screenshot_cache = dict(uuids = set(), has_changed = False, data=ScreenshotData())

        self.project = project
        # self.project.onProjectChanged.connect(partial(self.update_screenshot_data))
        self.project.onScreenshotAdded.connect(self.on_screenshot_added)
        self.project.onAnalysisAdded.connect(partial(self.queue_update))
        self.project.onAnalysisAdded.connect(partial(self.queue_update))
        for s in self.project.screenshots:
            s.onScreenshotChanged.connect(partial(self.queue_update))

        self._needs_update = True
        self.update_screenshot_data()


    def update(self):
        if self._project_closed:
            self._clear()
            return

        if self._needs_update:
            self.update_screenshot_data()
        self._needs_update = False

    def on_screenshot_added(self, s:Screenshot):

        s.onScreenshotChanged.connect(partial(self.update_screenshot_data))
        # self.update_screenshot_data()
        self._needs_update = True

    def queue_update(self):
        self._needs_update = True

    def update_screenshot_data(self):
        a = []
        b = []
        chroma = []
        luminance = []
        saturation = []
        time = []
        hue = []

        palettes = []

        uuids = []
        for i, s in enumerate(self.project.screenshots):
            t = s.get_connected_analysis(ColorFeatureAnalysis)
            if len(t) > 0:
                try:
                    arr = t[0].get_adata()['color_lab']
                except Exception as e:
                    log_error(e)
                    continue
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


            t2 = s.get_connected_analysis(ColorPaletteAnalysis)
            if len(t2) > 0:
                try:
                    arr = t2[0].get_adata()
                except Exception as e:
                    log_error(e)
                    continue
                pal = get_palette_at_merge_depth(arr, depth = 15)
                if pal is not None:
                    palettes.extend(pal)

        data = ScreenshotData()

        data.a = np.nan_to_num(a).tolist()
        data.b =  np.nan_to_num(b).tolist()
        data.chroma =  np.nan_to_num(chroma).tolist()
        data.luminance =  np.nan_to_num(luminance).tolist()
        data.saturation =  np.nan_to_num(saturation).tolist()
        data.hue = np.nan_to_num( hue).tolist()
        data.time =  np.nan_to_num(time).tolist()

        data.uuids = uuids

        data.palettes = palettes

        self._screenshot_cache['has_changed'] = True
        self._screenshot_cache['data'] = data
        self.export_screenshots()
        print("Screenshots Updated")


    def screenshot_url(self, s:Screenshot = None, uuid = None):
        if self.project is None:
            return
        if uuid is None:
            return os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), str(s.unique_id) + ".jpg")
        return os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), str(uuid) + ".jpg")


    def export_screenshots(self):
        ps = []
        rdir = os.path.join(self.project.export_dir, "screenshot_thumbnails")
        if not os.path.isdir(rdir):
            os.mkdir(rdir)

        for s in self.project.screenshots:
            if s.img_movie.shape[0] > 100:
                p = os.path.join(rdir, str(s.unique_id) + ".jpg")
                if not os.path.isfile(p):
                    cv2.imwrite(p, s.img_movie)
                ps.append(p)
        return ps

    def clear(self):
        self._project_closed = True

    def _clear(self):
        self.project = None  # type: VIANProject
        self._screenshot_cache = dict(uuids=set(), has_changed=False, data=ScreenshotData())

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
        self.view.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
        self.view.setPage(WebPage())
        self.view.reload()
        self.view.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)

        self.setWidget(self.view)


    def set_url(self, url):
        QWebEngineProfile.defaultProfile().clearAllVisitedLinks()
        QWebEngineProfile.defaultProfile().clearHttpCache()

        self.view.setUrl(QUrl(url))
        self.view.reload()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.reload()
        super(FlaskWebWidget, self).showEvent(a0)

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
        _server_data.update()
        if _server_data._screenshot_cache['has_changed']:
            _server_data._screenshot_cache['data'].urls = [url_for("screenshot", uuid=u) for u in _server_data._screenshot_cache['data'].uuids]
            _server_data._screenshot_cache['has_changed'] = False
            return json.dumps(dict(changes=True, data=_server_data._screenshot_cache['data'].__dict__))
        else:
            return dict(changes=False, data=_server_data._screenshot_cache['data'].__dict__)


if __name__ == '__main__':
    app.debug = True
    app.run()