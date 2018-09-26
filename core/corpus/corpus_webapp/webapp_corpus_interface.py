from core.corpus.client.corpus_interfaces import *

class WebAppCorpusInterface(CorpusInterface):
    def __init__(self, corpora_dir):
        super(WebAppCorpusInterface, self).__init__()
        self.endpoint_adress = 'http://127.0.0.1:5000/vian_upload'

    @pyqtSlot(object, object)
    def connect_user(self, user:DBContributor, options):
        try:
            answer = dict(success = True,
                          projects = [DBProject().to_database(True), DBProject().to_database(True), DBProject().to_database(True)],
                          user = DBContributor().to_database(True),
                          corpus_name = "ERC_FilmColors")

            if answer['success']:
                self.name = answer['corpus_name']
                self.onConnected.emit(answer['success'], self.to_project_list(answer['projects']), DBContributor().from_database(answer['user']))
            else:
                self.onConnected.emit(False, None, None)
        except Exception as e:
            raise e
            print("Exception in RemoteCorpusClient.connect_user(): ", str(e))
            self.onConnected.emit(False, None, None)

    def to_project_list(self, dlist):
        result = []
        for d in dlist:
            result.append(DBProject().from_database(d))
        return result

    def send_message(self, command:str, message:dict):
        try:
            if message is None:
                message = dict()
            msg = requests.post(self.server_address, data=message, headers=dict(type=command)).text.encode()
            return msg
        except Exception as e:
            raise e

    def verify_project(self):
        return True
    @pyqtSlot(object)
    def disconnect_user(self, user):
        pass

    @pyqtSlot(object, object)
    def commit_project(self, user, project: VIANProject):
        try:
            #OLD CODE
            # # Export all Screenshots and Masks
            # if project.main_window is not None:
            #     # This fails in the Headless Mode, which is exactly what we want
            #     try:
            #         self.onEmitProgress.connect(project.main_window.on_progress_popup)
            #     except:
            #         pass
            # res, path = self.prepare_project(project)
            # if res is False:
            #     return
            #
            # # Create a Zip File
            # file_name = project.name + ".zip"
            # archive_file = self.corpora_dir + "/" + project.name
            # project_obj = DBProject().from_project(project)
            # shutil.make_archive(archive_file, 'zip', project.folder)
            # project_obj.archive = archive_file + ".zip"
            #
            # fin = open(archive_file + ".zip", 'rb')
            # files = {'file': fin}
            # try:
            #     r = requests.post(self.server_address, files=files, headers=dict(type="upload")).text
            #     print("Redceived", r)
            #     file_name = json.loads(r)['path']
            #     print(file_name)
            # finally:
            #     fin.close()
            #
            # commit_result = json.loads(self.send_message(ServerCommands.Commit_Finished, dict(archive=file_name, user=user.to_database(True))).decode())
            if self.verify_project() == False:
                return

            print(project.folder)
            export_root = project.folder + "/corpus_export/"
            export_project_dir = export_root + "project/"
            scr_dir = export_root + "/scr/"
            mask_dir = export_root + "/masks/"

            # Create the temporary directories
            try:
                if os.path.isdir(export_root):
                    shutil.rmtree(export_root, ignore_errors=True)
                if not os.path.isdir(export_root):
                    os.mkdir(export_root)
                if not os.path.isdir(export_project_dir):
                    os.mkdir(export_project_dir)
            except Exception as e:
                QMessageBox.Error("Commit Error", "Could not modify \\corpus_export\\ directory."
                                                  "\nPlease make sure the Folder is not open in the Explorer/Finder.")
                return False, None

            project.store_project(UserSettings(), os.path.join(export_project_dir, project.name + ".eext"))

            print("Export to:", export_project_dir)
            archive_file = os.path.join(export_root, project.name)
            shutil.make_archive(archive_file, 'zip', export_project_dir)
            fin = open(archive_file + ".zip", 'rb')
            files = {'file': fin}
            try:
                r = requests.post(self.endpoint_adress, files=files, headers=dict(type="upload")).text
                print("Redceived", r)
                # file_name = json.loads(r)['path']
                # print(file_name)
            finally:
                fin.close()

            commit_result = dict(success=True, dbproject=DBProject().to_database(True))
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
        pass
        # try:
        #     if False:#TODO
        #         self.onCheckedOut.emit(True, self.to_project_list(result['dbprojects']))
        #     else:
        #         self.onCheckedOut.emit(False, None)
        # except Exception as e:
        #     print("Exception in RemoteCorpusClient.checkout_project(): ", str(e))
        #     self.onCheckedOut.emit(False, None)


    @pyqtSlot(object, object)
    def checkin_project(self, user, project: DBProject):
        pass
        # try:
        #     if result['success']:
        #         self.onCheckedIn.emit(True,  self.to_project_list(result['dbprojects']))
        #     else:
        #         self.onCheckedIn.emit(False, None)
        # except Exception as e:
        #     print("Exception in RemoteCorpusClient.checkin_project(): ", str(e))
        #     self.onCheckedIn.emit(False, None)

    @pyqtSlot(object, object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        pass
        # try:
        #
        #         if archive is not None:
        #             self.onReadyForExtraction.emit(True, project, archive)
        #         self.onReadyForExtraction.emit(False, None, None)
        # except Exception as e:
        #     print("Exception in RemoteCorpusClient.download_project(): ", str(e))
        #     self.onReadyForExtraction.emit(False, None, None)

    @pyqtSlot(object, object)
    def check_checkout_state(self, user, dbproject):
        pass
        # result = json.loads(self.send_message(ServerCommands.Get_CheckOut_State,
        #                                       dict(
        #                                           user=user.to_database(True),
        #                                           dbproject=dbproject.to_database(True)
        #                                       )).decode())
        #
        # if result['success'] is not False:
        #     proj  = DBProject().from_database(result['dbproject'])
        #     if proj.is_checked_out == True and proj.checked_out_user != user.contributor_id:
        #         self.onCheckOutStateRecieved.emit(CHECK_OUT_OTHER)
        #     elif proj.is_checked_out == True and proj.checked_out_user == user.contributor_id:
        #         self.onCheckOutStateRecieved.emit(CHECK_OUT_SELF)
        #     else:
        #         self.onCheckOutStateRecieved.emit(CHECK_OUT_NO)
        # else:
        #     self.onCheckOutStateRecieved.emit(CHECK_OUT_NOT_IN_DB)