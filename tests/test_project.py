import unittest
import os
import shutil

import core.data.headless2 as vian
from core.container.project import VIANProject
from core.data.creation_events import ALL_REGISTERED_PIPELINES

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


    def test_pipelines(self):
        with VIANProject(name="TestProject", path="data/test_project.eext") as project:
            pipeline = project.create_pipeline_script("TestPipeline", author="UnitTest")
            self.assertTrue(pipeline is not None)
            pipeline.save_script()
            self.assertTrue(os.path.isfile(pipeline.path))
            pipeline.import_pipeline()
            self.assertTrue(pipeline.name in ALL_REGISTERED_PIPELINES)

            project.store_project("data/test_project.eext")
            project = project.load_project("data/test_project.eext")

            self.assertTrue(len(project.pipeline_scripts) > 0)

            project.remove_pipeline_script(pipeline)
            self.assertTrue(pipeline not in project.pipeline_scripts)


if __name__ == '__main__':
    unittest.main()