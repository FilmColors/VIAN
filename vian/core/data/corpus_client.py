from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QToolBar, QHBoxLayout, QSpacerItem, QSizePolicy, QWidgetAction, QMessageBox
from vian.core.paths import get_vian_data
from vian.core.data.settings import UserSettings, Contributor, CONFIG, IS_DEV
from vian.core.container.project import VIANProject
from vian.core.container.analysis import SemanticSegmentationAnalysisContainer, FileAnalysis
from vian.core.container.experiment import Experiment, VocabularyWord, Vocabulary
from vian.core.analysis.analysis_import import SemanticSegmentationAnalysis
from vian.core.data.log import log_info
from vian.core.data.importers import ExperimentTemplateUpdater

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

if IS_DEV:
    EP_ROOT = CONFIG['localhost']
else:
    EP_ROOT = CONFIG['webapp_root']


def get_vian_version():
    try:
        q = requests.get(EP_ROOT + "vian/version").json()
        version = q['version'].split("_")
        version = [int(i) for i in version]
        version_id = q['id']
        return version, version_id
    except Exception as e:
        raise e
        return None


def download_vian_update(version_id):
    return requests.get(EP_ROOT + "vian/download_vian/" + str(version_id), stream=True)


def check_erc_template(project:VIANProject):
    return
    uuid = CONFIG['erc_template_uuid']
    exp = project.get_by_id(uuid)
    if exp is None:
        log_info("No ERC Template detected")
        return
    log_info("ERC Template detected, updating")
    r = requests.get("http://ercwebapp.westeurope.cloudapp.azure.com/api/experiments/1")
    exchange_data = r.json()
    temporary = get_vian_data("temp.json")
    with open(temporary, "w") as f:
        json.dump(exchange_data, f)
    project.import_(ExperimentTemplateUpdater(), temporary)
    log_info("ERC Template detected, Done")


class CorpusClient(QObject):
    onConnectionEstablished = pyqtSignal(object)
    onConnectionFailed = pyqtSignal(object)
    onCommitStarted = pyqtSignal(object, object)
    onCommitProgress = pyqtSignal(float, str)
    onCommitFinished = pyqtSignal(object)
    onCommitFailed = pyqtSignal(object)
    onDisconnect = pyqtSignal(object)

    def __init__(self):
        super(CorpusClient, self).__init__()
        self.corpus_interface = None
        self.execution_thread = None
        self.is_connected = False

    def mode(self):
        if isinstance(self.corpus_interface, WebAppCorpusInterface):
            return "webapp"
        else:
            return None

    @pyqtSlot(object)
    def connect_webapp(self, user: Contributor):
        try:
            if self.execution_thread is not None:
                self.execution_thread.exit()
            self.corpus_interface = WebAppCorpusInterface()
            self.execution_thread = QThread()
            self.corpus_interface.moveToThread(self.execution_thread)
            self.execution_thread.start()
            ret = self.corpus_interface.login(user)
            if ret['success'] == True:
                self.onCommitStarted.connect(self.corpus_interface.commit_project)
                self.is_connected = True
            return ret
        except Exception as e:
            print("Exception in connect webapp", e)
            return False

    @pyqtSlot(object)
    def on_connect_finished(self, result):
        if result is not None:
            r = dict(
                corpus_name = result['corpus_name']
            )
            self.onConnectionEstablished.emit(r)
        else:
            self.onConnectionFailed.emit(result)

        pass

    @pyqtSlot(object, object)
    def commit(self, project:VIANProject, contributor:Contributor):
        if self.mode() is not None:
            self.onCommitStarted.emit(project, contributor)
        else:
            self.onCommitFailed.emit(None)

    def check_project_exists(self, project:VIANProject):
        return self.corpus_interface.check_project_exists(project)

    @pyqtSlot(object)
    def on_commit_finished(self):
        pass

    @pyqtSlot(object)
    def download(self, desc):
        pass

    @pyqtSlot(object)
    def on_download_finished(self):
        pass

    def disconnect_corpus(self):
        if self.corpus_interface is not None:
            self.corpus_interface.logout()
            self.is_connected = False
            self.onDisconnect.emit(dict())
        pass


class CorpusInterfaceSignals(QObject):
    onConnected = pyqtSignal(object)
    onConnectionFailed = pyqtSignal(object)
    onCommitFinished = pyqtSignal(object)
    onCommitProgress = pyqtSignal(float, str)


class WebAppCorpusInterface(QObject):
    def __init__(self, ep_root = EP_ROOT):
        super(WebAppCorpusInterface, self).__init__()
        self.ep_root = ep_root
        self.ep_upload = self.ep_root + "upload"
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
        self.ep_get_user = self.ep_root + "get_user_for_login"

        self.signals = CorpusInterfaceSignals()
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
        :param user: The user to login
        :return: If the login was successful returns True, else returns False
        """
        try:
            print(self.ep_token)
            # We need to get the identification token
            a = requests.post(self.ep_token, json=dict(email = user.email, password = user.password))
            p = json.loads(requests.post(self.ep_get_user, json=dict(email = user.email, password = user.password)).text)
            print("Server Responded:", a.text, p)
            success = not "failed" in a.text

            if success:
                # We don't want VIAN to see all Projects on the WebAppCorpus, thus returning an empty list
                all_projects = []
                user.token = a.text
                self.user_id = p['id']
                ret = dict(success = True)
                #Todo return a good success description object
                self.signals.onConnected.emit(ret)
            else:
                ret = dict(success = False)
                #Todo return a good faile descirption object
                self.signals.onConnectionFailed.emit(ret)
        except Exception as e:
            ret = dict(success = False)
            print("Exception in RemoteCorpusClient.connect_user(): ", str(e))
            self.signals.onConnectionFailed.emit(ret)
        return ret

    @pyqtSlot()
    def logout(self):
        pass

    def verify_project(self):
        return True

    def _export_project(self, project):
        try:
            # region -- PREPARE --
            if not self.verify_project():
                return

            export_root = project.folder + "/corpus_export/"
            export_project_dir = export_root + "project/"
            scr_dir = export_project_dir + "/scr/"
            mask_dir = export_project_dir + "/masks/"
            export_hdf5_path = os.path.join(export_project_dir, os.path.split(project.hdf5_path)[1])

            archive_file = os.path.join(export_root, project.name)

            if os.path.isfile(archive_file + ".zip"):
                os.remove(archive_file + ".zip")
            # Create the temporary directories
            try:
                if os.path.isdir(export_root):
                    shutil.rmtree(export_root, ignore_errors=True)
                if not os.path.isdir(export_root):
                    os.mkdir(export_root)
                if not os.path.isdir(export_project_dir):
                    os.mkdir(export_project_dir)
            except Exception as e:
                raise e
                # QMessageBox.information("Commit Error", "Could not modify \\corpus_export\\ directory."
                                                        #"\nPlease make sure the Folder is not open in the Explorer/Finder.")
                return False, None

            # -- Create a HDF5 File for the Export -- #
            shutil.copy2(project.hdf5_path, export_hdf5_path)
            h5_file = h5py.File(export_hdf5_path, "r+")

            # -- Thumbnail --
            if len(project.screenshots) > 0:
                thumb = sample(project.screenshots, 1)[0].get_img_movie(True)
                cv2.imwrite(export_project_dir + "thumbnail.jpg", thumb)

            # -- Export all Screenshots --

            # Maps the unique ID of the screenshot to it's mask path -> dict(key:unique_id, val:dict(scene_id, segm_shot_id, group, path))
            mask_index = dict()
            shots_index = dict()
            file_analyses_index = dict()

            for i, scr in enumerate(project.screenshots):
                sys.stdout.write(
                    "\r" + str(round(i / len(project.screenshots), 2) * 100).rjust(3) + "%\t Baking Screenshots")
                self.signals.onCommitProgress.emit(i / len(project.screenshots), "Baking Screenshots")

                img = cv2.cvtColor(scr.get_img_movie(True), cv2.COLOR_BGR2BGRA)

                # Export the Screenshot as extracted from the movie
                grp_name = scr.screenshot_group.name
                name = scr_dir + grp_name + "_" \
                       + str(scr.scene_id) + "_" \
                       + str(scr.shot_id_segm) + ".jpg"
                if img.shape[1] > PAL_WIDTH:
                    fx = PAL_WIDTH / img.shape[1]
                    img = cv2.resize(img, None, None, fx, fx, cv2.INTER_CUBIC)

                if i == 0:
                    h5_file.create_dataset("screenshots", shape=(len(project.screenshots),) + img.shape, dtype=np.uint8)
                # cv2.imwrite(name, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                h5_file['screenshots'][i] = img
                segment = project.get_main_segmentation().get_segment_of_time(scr.movie_timestamp)
                if segment is None:continue

                shots_index[str(scr.unique_id)] = dict(
                    scene_id=scr.scene_id,
                    segment_id = str(segment.unique_id),
                    shot_id_segm=scr.shot_id_segm,
                    group=grp_name,
                    hdf5_idx=i,
                    path=name
                )

                # Export the Screenshots with all masks applied
                for e in project.experiments:
                    # First we have to find all experiments that have Classification Objects with Mask Labels
                    masks_to_export = []
                    for cobj in e.get_classification_objects_plain():
                        sem_labels = cobj.semantic_segmentation_labels[1]
                        ds_name = cobj.semantic_segmentation_labels[0]
                        if ds_name != "":
                            masks_to_export.append(dict(obj_name=cobj.name, ds_name=ds_name, labels=sem_labels))
                    masks_to_export_names = [m['ds_name'] for m in masks_to_export]

                    print(masks_to_export)
                    print(masks_to_export_names)
                    for counter, entry in enumerate(masks_to_export):
                        # Find the correct Mask Analysis
                        for a in scr.connected_analyses:
                            if isinstance(a, SemanticSegmentationAnalysisContainer) \
                                    and a.analysis_job_class == SemanticSegmentationAnalysis.__name__:
                                # table = SQ_TABLE_MASKS
                                data = a.get_adata()
                                dataset = a.dataset
                                mask_idx = project.hdf5_manager._uid_index[str(a.unique_id)]
                                print("Mask Index", mask_idx)
                                if dataset in masks_to_export_names:
                                    mask_path = mask_dir + dataset + "_" + str(scr.scene_id) + "_" + str(
                                        scr.shot_id_segm) + ".png"

                                    if str(scr.unique_id) not in mask_index:
                                        mask_index[str(scr.unique_id)] = []

                                    mask_index[str(scr.unique_id)].append((dict(
                                        scene_id=scr.scene_id,
                                        dataset=dataset,
                                        shot_id_segm=scr.shot_id_segm,
                                        group=grp_name,
                                        path=mask_path.replace(project.folder, ""),
                                        hdf5_index=mask_idx,
                                        scr_region=a.entry_shape)
                                    ))

            for i, a in enumerate(project.analysis):
                if isinstance(a, FileAnalysis):
                    file_path = a.save(os.path.join(export_project_dir, str(a.unique_id)))
                    file_analyses_index[str(a.unique_id)] = dict(
                        target = a.target_container,
                        analysis = a.analysis_job_class,
                        file_path =file_path
                    )

            with open(export_project_dir + "image_linker.json", "w") as f:
                json.dump(dict(masks=mask_index, shots=shots_index), f)

            h5_file.close()

            # -- Creating the Archive --
            print("Export to:", export_project_dir)
            project.store_project(os.path.join(export_project_dir, project.name + ".eext"))
            shutil.make_archive(archive_file, 'zip', export_project_dir)

        except Exception as e:
            raise e
            print("Exception in RemoteCorpusClient.commit_project(): ", str(e))
        return archive_file

    @pyqtSlot(object, object)
    def commit_project(self, project:VIANProject, contributor:Contributor):
        """
           Here we actually commit the project, 
           this includes to prepare the project, baking screenshots and masks into image files 
           and upload them to the Server
           :param user: 
           :param project: 
           :return: 
           """
        archive_file = self._export_project(project)

        if contributor is None:
            self.signals.onCommitFinished.emit(project)
            return

        # --- Sending the File --
        try:
            fin = open(archive_file + ".zip", 'rb')
            files = {'file': fin}
            print(files, self.ep_upload, dict(type="upload", authorization=contributor.token.encode()))
            r = requests.post(self.ep_upload, files=files, headers=dict(type="upload", authorization=contributor.token.encode())).text
            print("Redceived", r)
        except Exception as e:
            raise e
            pass

        finally:
            fin.close()

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
        print("OK")
        return requests.get(self.ep_query_corpora + "/" + str(self.user_id)).json()

    @pyqtSlot()
    def get_movies(self):
        print("OK")
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

