import unittest
import os
import shutil

import core.data.headless2 as vian
from core.container.project import VIANProject

class TestCreate(unittest.TestCase):
    def setUp(self) -> None:
        os.mkdir("data")

    def tearDown(self) -> None:
        shutil.rmtree("data")

    def test_create_no_dir(self):
        with VIANProject(name="NoDir") as project:
            self.assertIsInstance(project, VIANProject)

    def test_create_dir(self):
        with VIANProject(name="TestProject", path="data/test_project.eext") as project:
            project.store_project()
            self.assertTrue(os.path.isfile("data/test_project.eext"))

    def test_load(self):
        with VIANProject(name="TestProject", path="data/test_project.eext") as project:
            project.store_project()

        with VIANProject(name="TestProject", path="data/test_project.eext") as project:
            project = project.load_project(path="data/test_project.eext")
            self.assertNotEqual(project, None)

    def test_entities(self):
        with VIANProject(name="TestProject", path="data/test_project.eext") as project:
            segmentation = project.create_segmentation("SomeSegmentation")
            self.assertTrue(len(project.segmentation) > 0)
            segmentation.create_segment2(0, 1000, body="Some Annotation")
            self.assertTrue(len(segmentation.segments) > 0)
            segmentation.create_segment2(1000, 2000, body="Another Annotation")


if __name__ == '__main__':
    unittest.main()