from PyQt5.QtCore import QObject, QThread, pyqtSlot, pyqtSignal
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QToolBar, QHBoxLayout, QSpacerItem, QSizePolicy, QWidgetAction, QMessageBox
from core.data.settings import UserSettings, Contributor
from core.container.project import VIANProject
from core.container.analysis import SemanticSegmentationAnalysisContainer
from core.analysis.semantic_segmentation import SemanticSegmentationAnalysis


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
        elif isinstance(self.corpus_interface, LocalCorpusInterface):
            return "local"
        else:
            return None

    def connect_signals(self):
        if self.corpus_interface is not None:
            self.corpus_interface = LocalCorpusInterface

    @pyqtSlot(object, str)
    def connect_local(self, user: Contributor, filepath):
        """
        Connects the user to a local Database of VIAN Projects at given database.db file
        :param user: the user object
        :param filepath: the file path to the sqlite file
        :return:
        """
        self.corpus_interface = LocalCorpusInterface()
        self.execution_thread = QThread()
        self.corpus_interface.moveToThread(self.execution_thread)
        self.execution_thread.start()
        pass

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
            print(e)
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
            self.onCommitFailed.emit()


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
    def __init__(self, ep_root = "http://127.0.0.1:5000/api/"):
        super(WebAppCorpusInterface, self).__init__()
        self.ep_root = ep_root
        self.ep_upload = self.ep_root + "upload"
        self.ep_token = self.ep_root + "get_token"
        self.ep_ping = self.ep_root + "vian/ping"
        self.ep_version = self.ep_root + "vian/version"
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
            print("Server Responded:", a.headers, a.text)
            success = not "failed" in a.text

            if success:
                # We don't want VIAN to see all Projects on the WebAppCorpus, thus returning an empty list
                all_projects = []
                user.token = a.text
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
        pass

    @pyqtSlot()
    def logout(self):
        pass

    def verify_project(self):
        return True

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
        try:
            # region -- PREPARE --
            if self.verify_project() == False:
                return

            export_root = project.folder + "/corpus_export/"
            export_project_dir = export_root + "project/"
            scr_dir = export_project_dir + "/scr/"
            mask_dir = export_project_dir + "/masks/"
            export_hdf5_path = os.path.join(export_project_dir, os.path.split(project.hdf5_path)[1])
            # Create the temporary directories
            try:
                if os.path.isdir(export_root):
                    shutil.rmtree(export_root, ignore_errors=True)
                if not os.path.isdir(export_root):
                    os.mkdir(export_root)
                if not os.path.isdir(export_project_dir):
                    os.mkdir(export_project_dir)
                    # if not os.path.isdir(scr_dir):
                    #     os.mkdir(scr_dir)
                    # if not os.path.isdir(mask_dir):
                    #     os.mkdir(mask_dir)
            except Exception as e:
                QMessageBox.Information("Commit Error", "Could not modify \\corpus_export\\ directory."
                                                        "\nPlease make sure the Folder is not open in the Explorer/Finder.")
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

            for i, scr in enumerate(project.screenshots):
                sys.stdout.write(
                    "\r" + str(round(i / len(project.screenshots), 2) * 100).rjust(3) + "%\t Baking Screenshots")
                self.signals.onCommitProgress.emit(i / len(project.screenshots), "Baking Screenshots")

                img = cv2.cvtColor(scr.get_img_movie(True), cv2.COLOR_BGR2BGRA)
                # # Export the Screenshot as extracted from the movie
                grp_name = scr.screenshot_group
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

                shots_index[scr.unique_id] = dict(
                    scene_id=scr.scene_id,
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

                    for counter, entry in enumerate(masks_to_export):
                        # Find the correct Mask Analysis
                        for a in scr.connected_analyses:
                            if isinstance(a, SemanticSegmentationAnalysisContainer) \
                                    and a.analysis_job_class == SemanticSegmentationAnalysis.__name__:
                                # table = SQ_TABLE_MASKS
                                data = a.get_adata()
                                dataset = a.dataset
                                mask_idx = project.hdf5_manager._uid_index[a.unique_id]
                                # data = dict(db[table].find_one(key=a.unique_id))['json']
                                # data = project.main_window.eval_class(a.analysis_job_class)().from_json(data)

                                if dataset in masks_to_export_names:
                                    # mask = cv2.resize(data.astype(np.uint8), (img.shape[1], img.shape[0]),
                                    #                   interpolation=cv2.INTER_NEAREST)

                                    mask_path = mask_dir + dataset + "_" + str(scr.scene_id) + "_" + str(
                                        scr.shot_id_segm) + ".png"
                                    # cv2.imwrite(mask_path, mask, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_RATE])

                                    if scr.unique_id not in mask_index:
                                        mask_index[int(scr.unique_id)] = []

                                    mask_index[scr.unique_id].append((dict(
                                        scene_id=scr.scene_id,
                                        dataset=dataset,
                                        shot_id_segm=scr.shot_id_segm,
                                        group=grp_name,
                                        path=mask_path.replace(project.folder, ""),
                                        hdf5_index=mask_idx,
                                        scr_region=a.entry_shape)
                                    ))

            with open(export_project_dir + "image_linker.json", "w") as f:
                json.dump(dict(masks=mask_index, shots=shots_index), f)

            h5_file.close()

            # -- Creating the Archive --
            print("Export to:", export_project_dir)
            project.store_project(UserSettings(), os.path.join(export_project_dir, project.name + ".eext"))
            archive_file = os.path.join(export_root, project.name)
            shutil.make_archive(archive_file, 'zip', export_project_dir)

            # endregion

            if contributor is None:
                self.onCommited.emit(False, None, project)
                return

            # --- Sending the File --
            fin = open(archive_file + ".zip", 'rb')
            files = {'file': fin}
            try:
                print(files, self.ep_upload, dict(type="upload", authorization=contributor.token.encode()))
                r = requests.post(self.ep_upload, files=files,
                                  headers=dict(type="upload", authorization=contributor.token.encode())).text
                print("Redceived", r)
            except Exception as e:
                raise e
                print(e)
            finally:
                fin.close()

            commit_result = dict(success=True, dbproject=DBProject().to_database(True))
            if commit_result['success']:
                self.onCommited.emit(True, DBProject().from_database(commit_result['dbproject']), project)
            else:
                self.onCommited.emit(False, None, project)

        except Exception as e:
            print("Exception in RemoteCorpusClient.commit_project(): ", str(e))

    @pyqtSlot(object)
    def download_project(self, desc):
        pass

class LocalCorpusInterface():
    def __init__(self):
        pass

