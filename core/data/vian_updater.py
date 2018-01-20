import os
import glob
from random import randint
import sys
import tempfile as tmp
from shutil import copytree, move
import shutil
from core.data.interfaces import IConcurrentJob
from PyQt5.QtWidgets import QMessageBox, QApplication


import requests, zipfile, io
import os

import urllib.request, urllib.error, urllib.parse

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

    def update(self):
        try:
            do_update = self.get_server_version()
            if do_update:
                job = VianUpdaterJob([self.app_root, self.source_dir, self.url_source])
                self.main_window.run_job_concurrent(job)
        except Exception as e:
            self.main_window.print_message("Update Failed, see Console for more Information", "Red")
            print(e)

    def get_server_version(self):
        version = None
        for line in urllib.request.urlopen(self.url_version):
            if "__version__" in str(line):
                line = line.decode()
                version = line.replace("__version__: ", "")
                version = version.split(".")
                version = [int(version[0]), int(version[1]), int(version[2])]


        if version == None:
            return False

        if (self.current_version[0] < version[0]
            or (self.current_version[0] == version[0] and self.current_version[1] < version[1])
            or (self.current_version[0] == version[0] and self.current_version[1] == version[1] and self.current_version[2] < version[2])):
            return True
        else:
            return False

    def fetch_folder(self):
        if os.path.exists(self.app_root + "/update/"):
            shutil.rmtree(self.app_root + "/update/")

        os.mkdir(self.app_root + "/update/")
        self.temp_dir = self.app_root + "/update/"

        r = requests.get(self.url_source, stream=True)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(self.temp_dir)

    def replace_files(self):
        to_remove = self.app_root + "/VIAN/"

        root_src_dir = (self.temp_dir + "VIAN/").replace("\\", "/")
        root_dst_dir = (self.app_root + "/VIAN/").replace("\\", "/")

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
        self.app_root = args[0]
        self.source_dir = args[1]
        self.url_source = args[2]


        sign_progress(0.1)
        if os.path.exists(self.app_root + "/update/"):
            shutil.rmtree(self.app_root + "/update/")

        os.mkdir(self.app_root + "/update/")
        self.temp_dir = self.app_root + "/update/"

        r = requests.get(self.url_source, stream=True)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(self.temp_dir)

        sign_progress(0.5)
        root_src_dir = (self.temp_dir).replace("\\", "/")
        root_dst_dir = (self.app_root + "/VIAN/").replace("\\", "/")

        total = sum([len(files) for r, d, files in os.walk(root_src_dir)])
        counter = 1.0

        for src_dir, dirs, files in os.walk(root_src_dir):
            counter += 1
            sign_progress(0.5 + (counter / total) / 2)

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

        shutil.rmtree(self.app_root + "/update/")
        return [True]

    def modify_project(self, project, result, sign_progress = None):
        QMessageBox.information(project.main_window, "Update Finished", "Update Finished\n\n VIAN will quit now.\nPlease restart the Application after it has closed.")
        project.main_window.settings.SHOW_WELCOME = True
        project.main_window.settings.store()
        QApplication.quit()