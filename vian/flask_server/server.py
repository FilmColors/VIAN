import os
import sys
import cv2
from functools import partial
import json
import platform

import numpy as np

from PyQt5.QtCore import QThread, QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt5 import QtGui
from flask import Flask, render_template, send_file, url_for, jsonify, request, make_response

from vian.core.data.log import log_error, log_info
from vian.core.gui.ewidgetbase import EDockWidget
from vian.core.container.project import VIANProject, Screenshot, Segment
from vian.core.analysis.analysis_import import ColorFeatureAnalysis, ColorPaletteAnalysis, get_palette_at_merge_depth
from vian.core.data.computation import lab_to_lch, lab_to_sat, ms2datetime

app = Flask(__name__)


if getattr(sys, 'frozen', False):
    app.root_path = os.path.dirname(sys.executable)
elif __file__:
    app.root_path = os.path.dirname(__file__)

# app.root_path = os.path.split(__file__)[0]
log_info("FLASK ROOT", app.root_path)
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

VIAN_PORT = 5352

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

import mimetypes
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('application/json', '.json')

from threading import Lock
UPDATE_LOCK = Lock()


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

        self.selected_but_not_analyzed_uuids_ColorFeatureAnalysis = []
        self.selected_but_not_analyzed_uuids_ColorPaletteAnalysis = []


class ServerData:
    def __init__(self):
        self.project = None #type: VIANProject

        self._recompute_screenshot_cache = False
        self._screenshot_cache = dict(revision = 0, data=ScreenshotData())

        self._project_closed = False
        self.selected_uuids = None

    def get_screenshot_data(self, revision = 0):
        if self._recompute_screenshot_cache:
            self._recompute_screenshot_cache = False
            self.update_screenshot_data()
            self._screenshot_cache['revision'] += 1

        if revision != self._screenshot_cache['revision']:
            return dict(update=True,
                        revision = self._screenshot_cache['revision'],
                        data=self._screenshot_cache['data'].__dict__)
        else:
            return dict(update=False,
                        revision = self._screenshot_cache['revision'],
                        data=dict())

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

        selected_but_not_analyzed_uuids_ColorFeatureAnalysis = []
        selected_but_not_analyzed_uuids_ColorPaletteAnalysis = []
        #print("selected screenshots", self.selected_uuids)

        for i, s in enumerate(self.project.screenshots):
            if self.selected_uuids is not None and s.unique_id not in self.selected_uuids:
                continue

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
                lch = lab_to_lch(arr, human_readable=True)
                luminance.append(float(arr[0]))
                chroma.append(float(lch[1]))
                hue.append(float(lch[2]))
                saturation.append(float(lab_to_sat(arr)))
            else:
                selected_but_not_analyzed_uuids_ColorFeatureAnalysis.append(s.unique_id)

            t2 = s.get_connected_analysis(ColorPaletteAnalysis)
            if len(t2) > 0:
                try:
                    arr = t2[0].get_adata()
                except Exception as e:
                    log_error(e)
                    continue
                pal = get_palette_at_merge_depth(arr, depth=15)
                if pal is not None:
                    palettes.extend(pal)
            else:
                selected_but_not_analyzed_uuids_ColorPaletteAnalysis.append(s.unique_id)

        data = ScreenshotData()
        data.a = np.nan_to_num(a).tolist()
        data.b = np.nan_to_num(b).tolist()
        data.chroma = np.nan_to_num(chroma).tolist()
        data.luminance = np.nan_to_num(luminance).tolist()
        data.saturation = np.nan_to_num(saturation).tolist()
        data.hue = np.nan_to_num(hue).tolist()
        data.time = np.nan_to_num(time).tolist()

        data.uuids = uuids
        data.palettes = palettes

        data.selected_but_not_analyzed_uuids_ColorFeatureAnalysis = selected_but_not_analyzed_uuids_ColorFeatureAnalysis
        data.selected_but_not_analyzed_uuids_ColorPaletteAnalysis = selected_but_not_analyzed_uuids_ColorPaletteAnalysis

        self._screenshot_cache['has_changed'] = True
        self._screenshot_cache['data'] = data
        self.export_screenshots()

    def set_project(self, project:VIANProject, onAnalyseSignal):
        self.project = project
        self.onAnalyseSignal = onAnalyseSignal

        self._screenshot_cache = dict(revision = 0, data=ScreenshotData())

        self.project.onScreenshotAdded.connect(self.on_screenshot_added)
        self.project.onAnalysisAdded.connect(partial(self.queue_update))
        self.project.onAnalysisAdded.connect(partial(self.queue_update))

        for s in self.project.screenshots:
            s.onScreenshotChanged.connect(partial(self.queue_update))

        self._screenshot_cache['revision'] += 1
        self.update_screenshot_data()

    def queue_update(self):
        self._recompute_screenshot_cache = True

    def update(self):
        if self._project_closed:
            self._clear()
            return False

        if self.project is not None:
            self.update_screenshot_data()
            return True
        else:
            return False

    def on_screenshot_added(self, s:Screenshot):
        s.onScreenshotChanged.connect(partial(self.update_screenshot_data))

    def screenshot_url(self, s:Screenshot = None, uuid = None):
        if self.project is None:
            return None

        if uuid is None:
            file = os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), str(s.unique_id) + ".jpg")
        else:
            file = os.path.join(os.path.join(self.project.export_dir, "screenshot_thumbnails"), str(uuid) + ".jpg")
        if os.path.isfile(file):
            return file
        else:
            return None

    def export_screenshots(self):
        ps = []
        rdir = os.path.join(self.project.export_dir, "screenshot_thumbnails")
        if not os.path.isdir(rdir):
            os.mkdir(rdir)

        for s in self.project.screenshots:
            if s.img_movie is None:
                continue

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
        self._screenshot_cache = dict(revision = 0, data=ScreenshotData())


_server_data = ServerData()


class FlaskServer(QObject):
    onAnalyse = pyqtSignal(list)
    def __init__(self, parent):
        super(FlaskServer, self).__init__(parent)
        self.app = app

    @pyqtSlot()
    def run_server(self):
        self.app.run(port=VIAN_PORT)

    def on_loaded(self, project):
        global _server_data
        _server_data.set_project(project, self.onAnalyse)

    def on_closed(self):
        global _server_data
        _server_data.clear()

    def on_changed(self, project, item):
        pass

    def get_project(self):
        return None

    def on_selected(self, sender, selected):
        selected = list(selected)
        if sender is _server_data:
            return

        q = None
        for t in selected:
            if isinstance(t, VIANProject):
                q = t
        if q is not None:
            selected.remove(q)

        if _server_data.project is not None:
            # TODO this fails with corpus selection
            if len(selected) > 0:
                for s in selected:
                    if isinstance(s, Segment):
                        selected.extend(_server_data.project.get_screenshots_of_segment(s))
                selected = list(set(selected))
                _server_data.selected_uuids = [s.unique_id for s in selected]
            else:
                _server_data.selected_uuids = None
            _server_data.queue_update()
        pass


class WebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level: 'QWebEnginePage.JavaScriptConsoleMessageLevel', message: str, lineNumber: int, sourceID: str) -> None:
        print(message)


class FlaskWebWidget(EDockWidget):
    def __init__(self, main_window):
        super(FlaskWebWidget, self).__init__(main_window, False)
        self.setWindowTitle("Bokeh Visualizations")

        # On High Sierra and earlier QWebEngine crashes on load,
        # it's a miracle, apple sucks, for f**** sake
        # maybe I'm wrong and coded this shitty, no idea really,
        # there is a resolved issue on QT tracker
        # In a year or two, High sierra is gone anyway...
        self.mac_disable_web = False
        try:
            if int(platform.mac_ver()[0].split(".")[1])<=13:
                self.mac_disable_web = True
        except Exception as e:
            print(e)
        if not self.mac_disable_web:
            self.view = QWebEngineView(self)
            self.view.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
            self.view.setPage(WebPage())
            self.view.reload()
            self.view.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
            self.setWidget(self.view)
        else:
            self.setWidget(QLabel("Sorry, VIAN on OSX High Sierra and below does not support the visualization. \n "
                                  "Please watch them in your browser by clicking 'Open in Browser' on top"))
        self.a_open_browser = self.inner.menuBar().addAction("Open in Browser")
        self.a_open_browser.triggered.connect(self.on_browser)

        self.url = None


    def on_browser(self):
        import webbrowser

        webbrowser.open(self.url)

    def set_url(self, url):
        self.url = url
        if not self.mac_disable_web:
            QWebEngineProfile.defaultProfile().clearAllVisitedLinks()
            QWebEngineProfile.defaultProfile().clearHttpCache()
            self.view.setUrl(QUrl(url))
            self.view.reload()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        self.reload()
        super(FlaskWebWidget, self).showEvent(a0)

    def reload(self):
        if not self.mac_disable_web:
            self.view.reload()


@app.route("/")
def index():
    return render_template("color_dt.tmpl.html")


@app.route("/screenshot_vis/")
def screenshot_vis():
    return render_template("screenshot_vis.tmpl.html")


@app.route("/screenshot/<string:uuid>")
def screenshot(uuid):
    file = _server_data.screenshot_url(uuid=uuid)
    if file is None:
        print("Not Found", file)
        return make_response("Not found", 404)
    else:
        return send_file(file)


@app.route("/screenshot-data/<int:revision>")
def screenshot_data(revision):
    if _server_data.project is None:
        return json.dumps(_server_data.get_screenshot_data(revision))
    else:
        ret = _server_data.get_screenshot_data(revision)
        if 'uuids' in ret['data']:
            ret['data']['urls'] = [url_for("screenshot", uuid=u) for u in ret['data']['uuids']]
        return json.dumps(_server_data.get_screenshot_data(revision))


@app.route("/set-selection/", methods=['POST'])
def set_selection():
    if _server_data.project is None:
        return make_response(dict(screenshots_changed=False, uuids=[]))
    d = request.json
    selected_uuids = d['uuids']
    selected = [_server_data.project.get_by_id(uuids) for uuids in selected_uuids]

    selected = list(set(selected))
    if None in selected:
        selected.remove(None)

    _server_data.project.set_selected(_server_data, selected)
    return make_response("OK")

@app.route("/run-ColorFeatureAnalysis/", methods=['POST'])
def run_colorFeatureAnalysis():
    if _server_data.project is None:
        return make_response("Project is not set.")
    d = request.json
    uuid_submitted = d['uuids']
    if len(uuid_submitted) == 0: # means: analyse all
        for s in _server_data.project.screenshots:
            analyses = s.get_connected_analysis(ColorFeatureAnalysis)
            if len(analyses) == 0:
                uuid_submitted.append(s.unique_id)
    _server_data.onAnalyseSignal.emit(uuid_submitted)
    return make_response("OK")


@app.route("/summary/")
def summary():
    from vian.core.visualization.bokeh_timeline import generate_plot
    html, script = generate_plot(_server_data.project, return_mode="components")
    return render_template("template_inject.tmpl.html",script=html + script)
    # return render_template("summary.tmpl.html")


if __name__ == '__main__':
    app.debug = True
    app.run()
