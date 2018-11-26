from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


from core.container.project import VIANProject

from core.analysis.analysis_import import *
from core.corpus.shared.entities import *
from core.corpus.shared.corpusdb import *

import socket
import ftplib
import os
import sys
import requests

PAL_WIDTH = 720
PNG_COMPRESSION_RATE = 9

class CorpusInterface(QObject):
    onConnected = pyqtSignal(bool, object, object)
    onCommited = pyqtSignal(bool, object, object)
    onCheckedIn = pyqtSignal(bool, object)
    onCheckedOut = pyqtSignal(bool, object)
    onReceivedProjects = pyqtSignal(object)
    onReadyForExtraction = pyqtSignal(bool, object, str)
    onEmitProgress = pyqtSignal(float, str)
    onCheckOutStateRecieved = pyqtSignal(int)
    onQueryResult = pyqtSignal(object)

    def __init__(self):
        super(CorpusInterface, self).__init__()
        self.name = ""

    @pyqtSlot(object, object)
    def connect_user(self, user, options):
        pass

    @pyqtSlot(object)
    def disconnect_user(self, user):
        pass

    @pyqtSlot(object, object)
    def commit_project(self, user, project:VIANProject):
        pass

    @pyqtSlot(object, object)
    def checkout_project(self, user, project:DBProject):
        pass

    @pyqtSlot(object, object)
    def checkin_project(self, user, project:DBProject):
        pass

    @pyqtSlot(object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        pass

    @pyqtSlot(object, object)
    def check_checkout_state(self, user, dbproject):
        pass

    def prepare_project(self, project:VIANProject, create_project_archive = False):
        """
        Prepares a Project to be sent to the Server. 
        This includes: 
        - Export all Screenshots
        - Export all Masks
        :param project: A VIAN Project
        :param masks_to_export: A dict of mask info dict(<dataset> = (<Label-Name>, [List of Labels])
        :return: 
        """
        self.onEmitProgress.emit(0.0, "Preparing Project for Corpus")
        project_archive = None
        if create_project_archive:
            p = "/".join(project.folder.replace("\\", "/").split("/")[:-2]) + "/"
            project_archive = shutil.make_archive(p + project.name + "_project", 'zip', project.folder)
        export_root = project.folder + "/corpus_export/"
        scr_dir = export_root + "/scr/"
        mask_dir = export_root + "/masks/"

        # Create the temporary directories
        try:
            if os.path.isdir(export_root):
                shutil.rmtree(export_root, ignore_errors=True)
            if not os.path.isdir(export_root):
                os.mkdir(export_root)
            if not os.path.isdir(scr_dir):
                os.mkdir(scr_dir)
            if not os.path.isdir(mask_dir):
                os.mkdir(mask_dir)
        except Exception as e:
            QMessageBox.Error("Commit Error", "Could not modify \\corpus_export\\ directory."
                                              "\nPlease make sure the Folder is not open in the Explorer/Finder.")
            return False, None

        # Do the work
        # Connect to the SQLite Database
        db = ds.connect("sqlite:///" + project.data_dir + "/" + "database.sqlite")
        export_analyses = True

        shot_index = dict()
        masked_shot_index = dict()
        mask_index = dict()

        for i, scr in enumerate(project.screenshots):
            sys.stdout.write("\r" + str(round(i / len(project.screenshots), 2) * 100).rjust(3) + "%\t Baking Screenshots")
            self.onEmitProgress.emit(i / len(project.screenshots), "Baking Screenshots")
            # Export the Screenshot as extracted from the movie
            grp_name = scr.screenshot_group
            if grp_name in ["All Shots", ""]:
                grp_name = "glob"
            name = scr_dir + "Global_" + str(scr.scene_id) + "_" + str(scr.shot_id_segm) + "_" + grp_name + ".jpg"
            img = scr.get_img_movie(True)
            if img.shape[1] > PAL_WIDTH:
                fx = PAL_WIDTH / img.shape[1]
                img = cv2.resize(img, None, None, fx, fx, cv2.INTER_CUBIC)
            
            cv2.imwrite(name, img, [cv2.IMWRITE_JPEG_QUALITY, 90])
            shot_index[scr.unique_id] = dict(class_obj = "GLOBAL",
                                   scene_id = scr.scene_id,
                                   shot_id_segm = scr.shot_id_segm,
                                   group = grp_name,
                                   path = name.replace(project.folder, ""))

            # Export the Screenshots with all masks applied
            for e in project.experiments:
                masks_to_export = []
                for cobj in e.get_classification_objects_plain():
                    sem_labels = cobj.semantic_segmentation_labels[1]
                    ds_name =  cobj.semantic_segmentation_labels[0]
                    if ds_name != "":
                        masks_to_export.append(dict(obj_name=cobj.name, ds_name=ds_name, labels=sem_labels))
                masks_to_export_names = [m['ds_name'] for m in masks_to_export]

                for counter, entry in enumerate(masks_to_export):

                    mask = None
                    img = cv2.cvtColor(scr.get_img_movie(ignore), cv2.COLOR_BGR2BGRA)
                    # Find the correct Mask Analysis
                    for a in scr.connected_analyses:
                        if isinstance(a, IAnalysisJobAnalysis) and a.analysis_job_class == SemanticSegmentationAnalysis.__name__:
                            table = SQ_TABLE_MASKS
                            data = dict(db[table].find_one(key=a.unique_id))['json']
                            data = project.main_window.eval_class(a.analysis_job_class)().from_json(data)

                            if data['dataset'] in masks_to_export_names:
                                mask = cv2.resize(data['mask'].astype(np.uint8), (img.shape[1], img.shape[0]),
                                                  interpolation=cv2.INTER_NEAREST)

                                if img.shape[1] > PAL_WIDTH:
                                    fx = PAL_WIDTH / img.shape[1]
                                    img = cv2.resize(img, None, None, fx, fx, cv2.INTER_CUBIC)
                                cv2.imwrite(mask_dir + str(scr.scene_id) + "_" + str(scr.shot_id_segm) + ".png", mask, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_RATE])

                                if not scr.unique_id in mask_index:
                                    mask_index[scr.unique_id] = []

                                mask_index[scr.unique_id].append((dict(
                                    scene_id=scr.scene_id,
                                    shot_id_segm=scr.shot_id_segm,
                                    group=grp_name,
                                    path=(mask_dir + str(scr.scene_id) + "_" + str(scr.shot_id_segm) + ".png").replace(project.folder, "")
                                    )
                                ))
                                break
                    if mask is None:
                        print("None")
                        continue


                    mask_name = entry['obj_name']
                    mask_labels = entry['labels']
                    masked_img = np.copy(img)
                    mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
                    temp_mask = np.zeros_like(mask)
                    for lbl in mask_labels:
                        temp_mask[np.where(mask == lbl)] = 255
                    masked_img[np.where(temp_mask != 255)] = [0, 0, 0, 0]
                    name = scr_dir + mask_name + "_" \
                           + str(scr.scene_id) + "_" \
                           + str(scr.shot_id_segm) + "_" \
                           + grp_name + ".png"

                    if masked_img.shape[1] > PAL_WIDTH:
                        fx = PAL_WIDTH / img.shape[1]
                        masked_img = cv2.resize(img, None, None, fx, fx, cv2.INTER_CUBIC)
                    cv2.imwrite(name, masked_img, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_RATE])

                    if not scr.unique_id in masked_shot_index:
                        masked_shot_index[scr.unique_id] = []

                    masked_shot_index[scr.unique_id].append(dict(class_obj=mask_name,
                                           scene_id=scr.scene_id,
                                           shot_id_segm=scr.shot_id_segm,
                                           group=grp_name,
                                           path=name.replace(project.folder, ""))
                                  )

        with open(export_root + "image_linker.json", "w") as f:
            json.dump(dict(masks = mask_index, scrs = shot_index, masked_shots_index = masked_shot_index), f)

        self.onEmitProgress.emit(0.1, "Creating SQLite Database")
        shutil.copy2(project.data_dir + "/database.sqlite", export_root + "/database.sqlite")
        self.onEmitProgress.emit(0.5, "Saving Project")
        project.store_project(project.main_window.settings, export_root + project.name)
        self.onEmitProgress.emit(0.8, "Archive Zip")
        if project_archive is not None:
            shutil.move(project_archive, export_root)
        shutil.make_archive(project.folder + project.name + "_corpus", 'zip', export_root)
        self.onEmitProgress.emit(1.0, "Done")

        return True, project.folder + project.name + "_corpus.zip"

    @pyqtSlot(object)
    def submit_query(self, query_data:QueryRequestData):
        pass


class LocalCorpusInterface(CorpusInterface):
    def __init__(self):
        super(LocalCorpusInterface, self).__init__()
        self.local_corpus = DatasetCorpusDB()
        self.sql_path = None

    @pyqtSlot(object, object)
    def connect_user(self, user:DBContributor, options):
        try:
            user = DBContributor().from_vian_user(user)
            self.local_corpus = DatasetCorpusDB().load(options, self.sql_path)
            self.name = self.local_corpus.name
            user = self.local_corpus.connect_user(user)
            self.onConnected.emit(True, self.local_corpus.get_projects(), user)
        except Exception as e:
            print("Tried", options)
            print("Exception in LocalCorpusInterface.connect_user()", str(e))
            self.onConnected.emit(False, None, None)

    @pyqtSlot(object)
    def disconnect_user(self, user):
        user = DBContributor().from_vian_user(user)

    @pyqtSlot(object, object)
    def commit_project(self, user, project:VIANProject):
        user = DBContributor().from_vian_user(user)
        if project.main_window is not None:
            # This fails in the Headless Mode, which is exactly what we want
            try:
                pass
                # self.onEmitProgress.connect(project.main_window.on_progress_popup)
            except:
                pass

        res, path = self.prepare_project(project, True)
        if res is False:
            return

        success, dbproject = self.local_corpus.commit_project(path, user)

        if success:
            self.onCommited.emit(True, dbproject, project)
        else:
            self.onCommited.emit(False, None, project)

    @pyqtSlot(object, object)
    def checkout_project(self, user, project:DBProject):
        user = DBContributor().from_vian_user(user)
        success, archive = self.local_corpus.checkout_project(project.project_id, user)
        if success:
            self.onCheckedOut.emit(True, self.local_corpus.get_projects())
        else:
            self.onCheckedOut.emit(False, None)

    @pyqtSlot(object, object)
    def checkin_project(self, user, project:DBProject):
        user = DBContributor().from_vian_user(user)
        success = self.local_corpus.checkin_project(project.project_id, user)
        if success:
            self.onCheckedIn.emit(True, self.local_corpus.get_projects())
        else:
            self.onCheckedIn.emit(False, None)

    @pyqtSlot(object, object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        user = DBContributor().from_vian_user(user)
        archive = self.local_corpus.get_project_path(project)
        print("Download Project:", project.project_id, archive)
        if archive is not None:
            self.onReadyForExtraction.emit(True, project, archive)
        else:
            self.onReadyForExtraction.emit(False, None, None)

    @pyqtSlot(object, object)
    def check_checkout_state(self, user, dbproject):
        user = DBContributor().from_vian_user(user)
        result = self.local_corpus.get_project(dbproject.project_id)
        print(result.is_checked_out)
        if result is not None:
            if result.is_checked_out == True and result.checked_out_user != user.contributor_id:
                self.onCheckOutStateRecieved.emit(CHECK_OUT_OTHER)
            elif result.is_checked_out == True and result.checked_out_user == user.contributor_id:
                self.onCheckOutStateRecieved.emit(CHECK_OUT_SELF)
            else:
                self.onCheckOutStateRecieved.emit(CHECK_OUT_NO)
        else:
            self.onCheckOutStateRecieved.emit(CHECK_OUT_NOT_IN_DB)

    @pyqtSlot(object)
    def submit_query(self, query_data:QueryRequestData):
        result = self.local_corpus.parse_query(query_data)
        self.onQueryResult.emit(result)
        return result


class RemoteCorpusInterface(CorpusInterface):
    def __init__(self, corpora_dir):
        super(RemoteCorpusInterface, self).__init__()
        self.server_address = 'http://localhost'
        self.tcp_ip = "127.0.0.1"
        self.tcp_port = 5005
        self.socket = None
        self.corpora_dir = corpora_dir
        self.ftp_password = "Password"
        self.ftp_username = "Gaudenz"
        self.ftp_server_ip = "127.0.0.1"
        self.ftp_server_port = 12345

    @pyqtSlot(object, object)
    def connect_user(self, user:DBContributor, options):
        user = DBContributor().from_vian_user(user)
        try:
            answer_encoded = self.send_message(ServerCommands.Connect, dict(user=user.to_database(True)))
            answer = json.loads(answer_encoded.decode())

            success = answer['success']
            if success:
                self.name = answer['corpus_name']
                self.onConnected.emit(success, self.to_project_list(answer['projects']), DBContributor().from_database(answer['user']))
            else:
                self.onConnected.emit(False, None, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.connect_user(): ", str(e))
            self.onConnected.emit(False, None, None)

    def to_project_list(self, dlist):
        result = []
        for d in dlist:
            result.append(DBProject().from_database(d))
        return result

    def send_message(self, command: ServerCommands, message=None):
        try:
            if message is None:
                message = dict()
            msg = (str(command.value) + SPLIT_ITEM + json.dumps(message)).encode()
            msg = requests.post(self.server_address, data=msg, headers=dict(type="command")).text.encode()
            print(msg)
            return msg
        except Exception as e:
            raise e

    @pyqtSlot(object)
    def disconnect_user(self, user):
        pass

    @pyqtSlot(object, object)
    def commit_project(self, user, project: VIANProject):
        try:
            user = DBContributor().from_vian_user(user)
            ftp_path = json.loads(self.send_message(ServerCommands.Commit_Inquiry, dict(user=user.to_database(True))).decode())['path']

            # Export all Screenshots and Masks
            if project.main_window is not None:
                # This fails in the Headless Mode, which is exactly what we want
                try:
                    self.onEmitProgress.connect(project.main_window.on_progress_popup)
                except:
                    pass
            res, path = self.prepare_project(project)
            if res is False:
                return

            # Create a Zip File
            file_name = project.name + ".zip"
            archive_file = self.corpora_dir + "/" + project.name
            project_obj = DBProject().from_project(project)
            shutil.make_archive(archive_file, 'zip', project.folder)
            project_obj.archive = archive_file + ".zip"

            # Upload the Zip File
            # ftp_connection = ftplib.FTP()
            # ftp_connection.connect(self.ftp_server_ip, self.ftp_server_port)
            # ftp_connection.login(self.ftp_username, self.ftp_password)
            # ftp_connection.cwd(os.path.split("/ftp/")[1])
            # fh = open(archive_file + ".zip", 'rb')
            # ftp_connection.storbinary('STOR '+ file_name, fh)
            # fh.close()
            # os.remove(archive_file + ".zip")
            fin = open(archive_file + ".zip", 'rb')
            files = {'file': fin}
            try:
                r = requests.post(self.server_address, files=files, headers=dict(type="upload")).text
                print("Redceived", r)
                file_name = json.loads(r)['path']
                print(file_name)
            finally:
                fin.close()

            commit_result = json.loads(self.send_message(ServerCommands.Commit_Finished, dict(archive=file_name, user=user.to_database(True))).decode())

            if commit_result['success']:
                self.onCommited.emit(True, DBProject().from_database(commit_result['dbproject']), project)
            else:
                self.onCommited.emit(False, None, project)

        except Exception as e:
            raise e
            print("Exception in RemoteCorpusClient.commit_project(): ", str(e))
            self.onCommited.emit(False, None, project)

    @pyqtSlot(object, object)
    def checkout_project(self, user, project: DBProject):
        try:
            user = DBContributor().from_vian_user(user)
            result = json.loads(self.send_message(ServerCommands.Check_Out_Inquiry,
                                                  dict(
                                                      user=user.to_database(True),
                                                      dbproject=project.to_database(True)
                                                  )).decode())
            if result['success']:
                self.onCheckedOut.emit(True, self.to_project_list(result['dbprojects']))
            else:
                self.onCheckedOut.emit(False, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.checkout_project(): ", str(e))
            self.onCheckedOut.emit(False, None)

    @pyqtSlot(object, object)
    def checkin_project(self, user, project: DBProject):
        try:
            user = DBContributor().from_vian_user(user)
            result = json.loads(self.send_message(ServerCommands.Check_In_Project,
                                  dict(
                                      user=user.to_database(True),
                                      dbproject=project.to_database(True)
                                  )).decode())
            if result['success']:
                self.onCheckedIn.emit(True,  self.to_project_list(result['dbprojects']))
            else:
                self.onCheckedIn.emit(False, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.checkin_project(): ", str(e))
            self.onCheckedIn.emit(False, None)

    @pyqtSlot(object, object)
    def get_projects(self, user):
        user = DBContributor().from_vian_user(user)
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        try:
            user = DBContributor().from_vian_user(user)
            result = json.loads(self.send_message(ServerCommands.Download_Project,
                                                  dict(
                                                      user=user.to_database(True),
                                                      dbproject=project.to_database(True)
                                                  )).decode())

            if result['success']:
                ftp_connection = ftplib.FTP()
                ftp_connection.connect(self.ftp_server_ip, self.ftp_server_port)
                ftp_connection.login(self.ftp_username, self.ftp_password)
                ftp_connection.cwd(os.path.split("/ftp/")[1])

                archive = self.corpora_dir + result['path'] # replace with your file in the directory ('directory_name')
                print("Downloading File: ", archive)
                localfile = open(archive, 'wb')
                ftp_connection.retrbinary('RETR ' + result['path'], localfile.write, 1024)
                ftp_connection.quit()
                localfile.close()

                print("Downloaded Project:", project.project_id, archive)
                if archive is not None:
                    self.onReadyForExtraction.emit(True, project, archive)
                else:
                    self.onReadyForExtraction.emit(False, None, None)
            else:
                self.onReadyForExtraction.emit(False, None, None)
        except Exception as e:
            print("Exception in RemoteCorpusClient.download_project(): ", str(e))
            self.onReadyForExtraction.emit(False, None, None)

    @pyqtSlot(object, object)
    def check_checkout_state(self, user, dbproject):
        user = DBContributor().from_vian_user(user)
        result = json.loads(self.send_message(ServerCommands.Get_CheckOut_State,
                                              dict(
                                                  user=user.to_database(True),
                                                  dbproject=dbproject.to_database(True)
                                              )).decode())

        if result['success'] is not False:
            proj  = DBProject().from_database(result['dbproject'])
            if proj.is_checked_out == True and proj.checked_out_user != user.contributor_id:
                self.onCheckOutStateRecieved.emit(CHECK_OUT_OTHER)
            elif proj.is_checked_out == True and proj.checked_out_user == user.contributor_id:
                self.onCheckOutStateRecieved.emit(CHECK_OUT_SELF)
            else:
                self.onCheckOutStateRecieved.emit(CHECK_OUT_NO)
        else:
            self.onCheckOutStateRecieved.emit(CHECK_OUT_NOT_IN_DB)