import logging

from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QToolBar, QHBoxLayout, QSpacerItem, QSizePolicy, QWidgetAction, QMessageBox
from vian.core.paths import get_vian_data
from vian.core.data.settings import UserSettings, Contributor, CONFIG
from vian.core.container.project import VIANProject
from vian.core.container.analysis import SemanticSegmentationAnalysisContainer, FileAnalysis
from vian.core.container.experiment import Experiment, VocabularyWord, Vocabulary
from vian.core.analysis.analysis_import import SemanticSegmentationAnalysis, ColorPaletteAnalysis, ColorFeatureAnalysis
from vian.core.analysis.analysis_utils import run_analysis, progress_dummy
import os
import json
import numpy as np
import shutil
import sys
import cv2
import h5py
from random import sample
import requests


PAL_WIDTH = 720

if CONFIG["dev_mode"]:
    EP_ROOT = CONFIG['localhost']
else:
    EP_ROOT = CONFIG['webapp_root']


class VianNotLoggedInException(Exception):
    """
    Is raised when the user is not logged in.
    """


class CorpusInterfaceSignals(QObject):
    onConnected = pyqtSignal(object)
    onConnectionFailed = pyqtSignal(object)
    onCommitFinished = pyqtSignal(object)
    onCommitProgress = pyqtSignal(float, str)


class WebAppCorpusInterface(QObject):
    def __init__(self, ep_root = EP_ROOT):
        super(WebAppCorpusInterface, self).__init__()
        self.ep_root = ep_root
        self.ep_upload = self.ep_root + "upload/upload-project"
        self.ep_token = self.ep_root + "get_token"
        self.ep_ping = self.ep_root + "vian/ping"
        self.ep_version = self.ep_root + "vian/version"
        self.ep_query_movies = self.ep_root + "query/movies"
        self.ep_query_persons = self.ep_root + "query/persons"
        self.ep_query_companies = self.ep_root + "query/companies"
        self.ep_query_color_processes = self.ep_root + "query/colorprocess"
        self.ep_query_genres = self.ep_root + "query/genre"
        self.ep_query_countries = self.ep_root + "query/country"
        self.ep_project_hash = self.ep_root + "query/project_hash"
        self.ep_query_corpora = self.ep_root + "query/get_corpora"
        self.ep_get_user = self.ep_root + "user/login"

        self.signals = CorpusInterfaceSignals()
        self.token = None
        self.user_id = -1

    @pyqtSlot()
    def ping(self):
        """
        performs a simple ping to the WebApp server
        :return: returns true if there was a response
        """
        pass

    @pyqtSlot(object)
    def login(self, user:Contributor):
        """
        Checks if a user exists on the WebApp, if so, connects and returns true
        else returns False

        :raise VianNotLoggedInException: If the credentials are incorrect or the server is not reachable
        :param user: The user to login
        :return: If the login was successful returns True, else returns False
        """
        try:
            p = requests.post(self.ep_get_user, json=dict(email = user.email, password = user.password))
            if p.status_code != 200:
                raise VianNotLoggedInException

            self.token = p.json()['token']

            ret = dict(success = True, user=p.json()['user'], token=self.token)
            self.signals.onConnected.emit(dict(success = True, user=p.json()['user'], token=self.token))

        except Exception as e:
            ret = dict(success = False, user=None, token=None)
            print("Exception in RemoteCorpusClient.connect_user(): ", str(e))
            self.signals.onConnectionFailed.emit(ret)
        return ret

    @pyqtSlot()
    def logout(self):
        pass

    def verify_project(self):
        return True

    def _export_project(self, project: VIANProject) -> str:
        bake_path = project.store_project(bake=True)
        archive_path = project.zip_baked(bake_path)
        return archive_path

    def _preprocess(self, vian_proj, on_progress=progress_dummy):
        """
         Ensure all analyses which the webapp depends on are computed.
         :param file_path:
         :return:
         """
        global progress_bar
        global gl_progress


        segments = []
        for s in vian_proj.segmentation:
            segments.extend(s.segments)

        run_analysis(vian_proj, ColorPaletteAnalysis(coverage=.01), segments,
                     vian_proj.get_classification_object_global("Global"), progress_callback=on_progress)

        run_analysis(vian_proj, ColorFeatureAnalysis(coverage=.01), segments,
                     vian_proj.get_classification_object_global("Global"), progress_callback=on_progress)

        run_analysis(vian_proj, SemanticSegmentationAnalysis(),
                     vian_proj.screenshots,
                     vian_proj.get_classification_object_global("Global"), progress_callback=on_progress)
        clobjs = [
            vian_proj.get_classification_object_global("Global"),
            vian_proj.get_classification_object_global("Foreground"),
            vian_proj.get_classification_object_global("Background")
        ]

        print("Color Palettes")
        run_analysis(vian_proj, ColorPaletteAnalysis(), vian_proj.screenshots, clobjs, progress_callback=on_progress)

        print("Color Features")
        run_analysis(vian_proj, ColorFeatureAnalysis(), vian_proj.screenshots, clobjs, progress_callback=on_progress)

        vian_proj.store_project()

    @pyqtSlot(object, object)
    def commit_project(self, project:VIANProject, user:Contributor):
        if self.token is None:
            self.login(user)
            if self.token is None:
                raise VianNotLoggedInException("User is not logged in.")

        self._preprocess(project)
        archive_path = self._export_project(project)
        # --- Sending the File --
        try:
            fin = open(archive_path, 'rb')
            files = {'file': fin,
                     'json': json.dumps(dict(library="Aleksander", allow_new_keywords = True))}
            print(files, self.ep_upload, dict(type="upload", Authorization=self.token))
            r = requests.post(self.ep_upload, files=files, headers=dict(Authorization = self.token)).text
            print("Redceived", r)
        except Exception as e:
            raise e
            pass

        finally:
            fin.close()
        pass

    def check_project_exists(self, p:VIANProject):
        try:
            r = requests.get(self.ep_project_hash + "/" + p.uuid)
            exchange_data = r.json()
            if len(exchange_data) > 0:
                return True
            else:
                return False
        except Exception as e:
            print(e)
            return False

    @pyqtSlot(object)
    def download_project(self, desc):
        pass

    @pyqtSlot()
    def get_corpora(self):
        return requests.get(self.ep_query_corpora + "/" + str(self.user_id)).json()

    @pyqtSlot()
    def get_movies(self):
        return requests.get(self.ep_query_movies).json()

    @pyqtSlot()
    def get_color_processes(self):
        return requests.get(self.ep_query_color_processes).json()

    @pyqtSlot()
    def get_persons(self):
        return requests.get(self.ep_query_persons).json()

    @pyqtSlot()
    def get_genres(self):
        return requests.get(self.ep_query_genres).json()

    @pyqtSlot()
    def get_countries(self):
        return requests.get(self.ep_query_countries).json()

    @pyqtSlot()
    def get_companies(self):
        return requests.get(self.ep_query_companies).json()

    def push_vocabulary(self, vocabulary:Vocabulary):
        """ Pushes a Vocabulary to the WebApp """
        pass

    def pull_vocabulary(self, vocabulary:Vocabulary):
        """ Tries to Pull a Vocabulary from the WebApp """
        pass

