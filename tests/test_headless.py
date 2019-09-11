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

if __name__ == '__main__':
    unittest.main()