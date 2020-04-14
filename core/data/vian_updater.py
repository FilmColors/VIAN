import os
import glob
from random import randint
import sys
import subprocess

from shutil import copytree, move
import shutil
from core.data.interfaces import IConcurrentJob
from core.data.log import log_error, log_info, log_warning, log_debug
from PyQt5.QtWidgets import QMessageBox, QApplication

from core.corpus.client.corpus_client import get_vian_version, download_vian_update
import requests, zipfile, io
import os

class VianUpdater(IConcurrentJob):
    def __init__(self, main_window, current_version):
        v = current_version.split(".")
        self.main_window = main_window
        self.current_version = [int(v[0]), int(v[1]), int(v[2])]
        self.source_dir = main_window.settings.UPDATE_SOURCE
        self.temp_dir = ""
        self.app_root = os.path.abspath("../" + os.curdir)
        self.url_source = "http://zauberklang.ch/vian_update.zip"
        self.url_version = "http://zauberklang.ch/vian_version.txt"
        self.to_exclude = ["user"]
        self.box = None

    def update(self, force = False, include_beta = False):
        try:
            do_update, version_id = self.get_server_version(include_beta)
            if do_update or force:
                job = VianUpdaterJob([self.app_root, self.source_dir, self.url_source, version_id])
                self.main_window.run_job_concurrent(job)
        except Exception as e:
            self.main_window.print_message("Update Failed, see Console for more Information", "Red")
            log_error(e)

    def get_server_version(self, include_beta = False):
        version = None
        version_id = None
        build = None
        try:
            version, version_id = get_vian_version()
            log_info("Server Version:", version, version_id)
        except Exception as e:
            log_error("Could not fetch update version:", str(e))
            pass
        if version is None:
            return False

        if (self.current_version[0] < version[0]
            or (self.current_version[0] == version[0] and self.current_version[1] < version[1])
            or (self.current_version[0] == version[0] and self.current_version[1] == version[1] and self.current_version[2] < version[2])):
            if build == "beta":
                log_info("Beta update available")
                return include_beta, version_id
            else:
                log_info("Update available")
                return True, version_id
        else:
            log_info("No update available")
            return False, version_id

    def fetch_folder(self, version_id):
        if os.path.exists(self.app_root + "/update/"):
            shutil.rmtree(self.app_root + "/update/")

        os.mkdir(self.app_root + "/update/")
        self.temp_dir = self.app_root + "/update/"

        r = download_vian_update(version_id)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(self.temp_dir)

    def replace_files(self):
        if sys.platform == "darwin":
            t = "/src/"
        else:
            t = "VIAN"
        to_remove = self.app_root + t

        root_src_dir = (self.temp_dir + t).replace("\\", "/")
        root_dst_dir = (self.app_root + t).replace("\\", "/")

        for src_dir, dirs, files in os.walk(root_src_dir):
            src_dir = src_dir.replace("\\", "/")
            dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
            for file_ in files:
                src_file = os.path.join(src_dir, file_)
                dst_file = os.path.join(dst_dir, file_)
                if os.path.exists(dst_file):
                    os.remove(dst_file)
                    move(src_file, dst_dir)


class VianUpdaterJob(IConcurrentJob):

    def run_concurrent(self, args, sign_progress):
        try:
            self.app_root = args[0]
            self.source_dir = args[1]
            self.url_source = args[2]
            version_id = args[3]

            sign_progress(0.1)
            if os.path.exists(self.app_root + "/update/"):
                shutil.rmtree(self.app_root + "/update/")

            os.mkdir(self.app_root + "/update/")
            self.temp_dir = self.app_root + "/update/"

            r = download_vian_update(version_id)
            z = zipfile.ZipFile(io.BytesIO(r.content))
            z.extractall(self.temp_dir)

            sign_progress(0.5)
            if sys.platform == "darwin":
                t = "/src/"
            else:
                t = "/VIAN/"

            root_src_dir = (self.temp_dir).replace("\\", "/")
            root_dst_dir = (self.app_root + t).replace("\\", "/")

            total = sum([len(files) for r, d, files in os.walk(root_src_dir)])
            counter = 1.0

            for src_dir, dirs, files in os.walk(root_src_dir):
                    counter += 1
                    sign_progress(0.5 + ((counter / total) / 2))

                    src_dir = src_dir.replace("\\", "/")
                    dst_dir = src_dir.replace(root_src_dir, root_dst_dir, 1)
                    if not os.path.exists(dst_dir):
                        os.makedirs(dst_dir)
                    for file_ in files:
                        try:
                            src_file = os.path.join(src_dir, file_)
                            dst_file = os.path.join(dst_dir, file_)
                            if os.path.exists(dst_file):
                                os.remove(dst_file)
                            move(src_file, dst_dir)
                        except Exception as e:
                            log_error("Could not Copy File:", str(src_file), str(e))
                            continue
            self.run_python_update(self.app_root)

            try:
                shutil.rmtree(self.app_root + "/update/", ignore_errors=True)
            except Exception as e:
                log_error(e)
            return [True]
        except Exception as e:
            log_error(e)
            return [False]

    def run_python_update(self, app_root):
        if sys.platform == "win32":
            script_path = os.path.join(app_root, "python-update-win.bat")
            cmd = script_path
        else:
            script_path = os.path.join(app_root, "python-update-osx.sh")
            cmd = "sh " + script_path

        if os.path.isfile(script_path):
            subprocess.call(cmd, shell=True)

    def modify_project(self, project, result, sign_progress = None, main_window = None):
        QMessageBox.information(main_window, "Update Finished", "Update Finished\n\n VIAN will quit now.\nPlease restart the Application after it has closed.")
        main_window.settings.SHOW_WELCOME = True
        main_window.settings.store(main_window.dock_widgets)
        QApplication.quit()
