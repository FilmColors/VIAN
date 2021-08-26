import unittest
import os
import cv2
import shutil
from vian.core.data.corpus_client import WebAppCorpusInterface
from vian.core.container.project import VIANProject
from vian.core.data.settings import UserSettings
from uuid import uuid4
uuid = "83646205-fcb7-4311-8bb7-2c5a3a7feaa4"
PROJECT = "C:\\Users\\gaude\\Documents\\VIAN\\projects\\TemplateProject22\\TemplateProject22.eext"
SETTINGS_PATH = "settings.json"

class TestCreate(unittest.TestCase):
    def setUp(self) -> None:
        os.mkdir("data")

    def tearDown(self) -> None:
        shutil.rmtree("data")

    def test_check_project_existence(self):
        with VIANProject().load_project(path=PROJECT) as project:
            interface = WebAppCorpusInterface()
            t = interface.check_project_exists(project)
            self.assertTrue(t)

            project.uuid = str(uuid4())
            t = interface.check_project_exists(project)
            self.assertFalse(t)

    def test_export(self):
        with VIANProject().load_project(path=PROJECT) as project:
            settings = UserSettings(path=SETTINGS_PATH).load()
            cap = cv2.VideoCapture(project.movie_descriptor.movie_path)
            ret, frame = cap.read()
            cv2.imshow("", frame)
            for s in project.screenshots:
                print(s, s.frame_pos)
                s.load_screenshots(cap)
                cv2.imshow("", s.get_img_movie())
                cv2.waitKey(10)
            interface = WebAppCorpusInterface()
            interface._export_project(project)

    def test_upload(self):
        with VIANProject().load_project(path=PROJECT) as project:
            settings = UserSettings(path=SETTINGS_PATH).load()
            cap = cv2.VideoCapture(project.movie_descriptor.movie_path)
            ret, frame = cap.read()
            cv2.imshow("",frame)
            for s in project.screenshots:
                print(s, s.frame_pos)
                s.load_screenshots(cap)
                cv2.imshow("", s.get_img_movie())
                cv2.waitKey(10)
            # load_screenshots(project)
            interface = WebAppCorpusInterface()
            print(settings.CONTRIBUTOR)

            interface.commit_project(project,settings.CONTRIBUTOR)



