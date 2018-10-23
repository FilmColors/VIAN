from core.corpus.client.corpus_interfaces import *
import threading

class WebAppCorpusInterface(CorpusInterface):
    def __init__(self, corpora_dir):
        super(WebAppCorpusInterface, self).__init__()
        self.endpoint_upload = 'http://127.0.0.1:5000/api/upload'
        self.endpoint_token = "http://127.0.0.1:5000/api/get_token"
        self.name = "VIAN-WebApp"

    @pyqtSlot(object, object)
    def connect_user(self, user:Contributor, options):
        try:
            a = requests.post(self.endpoint_token, json=dict(email = user.email, password = user.password))
            print("Server Responded:", a.headers, a.text)
            success = not "failed" in a.text
            if success:
                # We don't want VIAN to see all Projects on the WebAppCorpus, thus returning an empty list
                all_projects = []
                user.token = a.text
                self.onConnected.emit(success, all_projects, user)
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
        """
        Here we actually commit the project, 
        this includes to prepare the project, baking screenshots and masks into image files 
        and upload them to the Server
        :param user: 
        :param project: 
        :return: 
        """
        try:
            #region -- PREPARE --
            if self.verify_project() == False:
                return

            export_root = project.folder + "/corpus_export/"
            export_project_dir = export_root + "project/"
            scr_dir = export_project_dir + "/scr/"
            mask_dir = export_project_dir + "/masks/"

            # Create the temporary directories
            try:
                if os.path.isdir(export_root):
                    shutil.rmtree(export_root, ignore_errors=True)
                if not os.path.isdir(export_root):
                    os.mkdir(export_root)
                if not os.path.isdir(export_project_dir):
                    os.mkdir(export_project_dir)
                if not os.path.isdir(scr_dir):
                    os.mkdir(scr_dir)
                if not os.path.isdir(mask_dir):
                    os.mkdir(mask_dir)
            except Exception as e:
                QMessageBox.Information("Commit Error", "Could not modify \\corpus_export\\ directory."
                                                  "\nPlease make sure the Folder is not open in the Explorer/Finder.")
                return False, None

            # -- Thumbnail --
            if len(project.screenshots) > 0:
                thumb = sample(project.screenshots, 1)[0].img_movie
                cv2.imwrite(export_project_dir + "thumbnail.jpg", thumb)

            # -- Export all Screenshots --

            # Maps the unique ID of the screenshot to it's mask path -> dict(key:unique_id, val:dict(scene_id, segm_shot_id, group, path))
            mask_index = dict()
            shots_index = dict()
            for i, scr in enumerate(project.screenshots):
                sys.stdout.write("\r" + str(round(i / len(project.screenshots), 2) * 100).rjust(3) + "%\t Baking Screenshots")
                self.onEmitProgress.emit(i / len(project.screenshots), "Baking Screenshots")

                img = cv2.cvtColor(scr.img_movie, cv2.COLOR_BGR2BGRA)
                # # Export the Screenshot as extracted from the movie
                grp_name = scr.screenshot_group
                name = scr_dir + grp_name + "_" \
                       + str(scr.scene_id) + "_" \
                       + str(scr.shot_id_segm) + ".png"
                if img.shape[1] > PAL_WIDTH:
                    fx = PAL_WIDTH / img.shape[1]
                    img = cv2.resize(img, None, None, fx, fx, cv2.INTER_CUBIC)

                cv2.imwrite(name, img, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_RATE])

                shots_index[scr.unique_id] = dict(
                    scene_id=scr.scene_id,
                    shot_id_segm=scr.shot_id_segm,
                    group=grp_name,
                    path=name.replace(project.folder, "")
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
                            if isinstance(a, IAnalysisJobAnalysis) and a.analysis_job_class == SemanticSegmentationAnalysis.__name__:
                                # table = SQ_TABLE_MASKS
                                data = a.get_adata()
                                dataset = a.dataset
                                print(dataset, masks_to_export)
                                # data = dict(db[table].find_one(key=a.unique_id))['json']
                                # data = project.main_window.eval_class(a.analysis_job_class)().from_json(data)

                                if dataset in masks_to_export_names:
                                    mask = cv2.resize(data.astype(np.uint8), (img.shape[1], img.shape[0]),
                                                      interpolation=cv2.INTER_NEAREST)

                                    mask_path = mask_dir + dataset + "_" +str(scr.scene_id) + "_" + str(scr.shot_id_segm) + ".png"
                                    cv2.imwrite(mask_path, mask, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION_RATE])

                                    if scr.unique_id not in mask_index:
                                        mask_index[int(scr.unique_id)] = []

                                    mask_index[scr.unique_id].append((dict(
                                        scene_id=scr.scene_id,
                                        dataset=dataset,
                                        shot_id_segm=scr.shot_id_segm,
                                        group=grp_name,
                                        path=mask_path.replace(project.folder, "") )
                                    ))

            with open(export_project_dir + "image_linker.json", "w") as f:
                json.dump(dict(masks=mask_index, shots=shots_index), f)

            for scr in project.screenshots:
                print(scr.unique_id in mask_index.keys(), scr.unique_id in shots_index.keys())

            # -- Creating the Archive --
            print("Export to:", export_project_dir)
            project.store_project(UserSettings(), os.path.join(export_project_dir, project.name + ".eext"))
            archive_file = os.path.join(export_root, project.name)
            shutil.make_archive(archive_file, 'zip', export_project_dir)

            #endregion

            # --- Sending the File --
            # TODO SILAS, this should already work quite well
            fin = open(archive_file + ".zip", 'rb')
            files = {'file': fin}
            try:
                print(files, self.endpoint_upload, dict(type="upload", authorization=user.token.encode()))
                r = requests.post(self.endpoint_upload, files=files, headers=dict(type="upload", authorization=user.token.encode())).text
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
            raise e ## TODO DEBUG
            print("Exception in RemoteCorpusClient.commit_project(): ", str(e))
            self.onCommited.emit(False, None, project)

    @pyqtSlot(object, object)
    def checkout_project(self, user, project: DBProject):
        pass

    @pyqtSlot(object, object)
    def checkin_project(self, user, project: DBProject):
        pass

    @pyqtSlot(object, object)
    def get_projects(self, user):
        pass

    @pyqtSlot(object, object)
    def download_project(self, user, project):
        pass

    @pyqtSlot(object, object)
    def check_checkout_state(self, user, dbproject):
        pass
