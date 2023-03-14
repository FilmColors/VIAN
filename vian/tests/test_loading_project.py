import unittest
import os
import shutil
import difflib
import pandas as pd

from vian.core.analysis.analysis_import import *
from vian.core.container.project import VIANProject
from vian.tests.utils import *
from vian.core.container.vocabulary_library import Vocabulary, VocabularyLibrary, VocabularyCollection
"""
Test cases: 
- Vocabulary Library should be serialized and desierualized correctly 
- When opening an existing project which already has some of the vocabularies attached do the following: 
    - If 

"""

class TestProjectLoading(unittest.TestCase):
    def setUp(self) -> None:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        self.test_temp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        self.unpacked_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unpacked")
        shutil.unpack_archive("netflix_test_project.zip", self.unpacked_folder)

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)
        self.project_path = os.path.join(self.unpacked_folder, "NETFLIX_VOCABULARY.eext")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_temp_folder)
        shutil.rmtree(self.unpacked_folder)


    def test_loading_screenshots(self):
        import  json
        with open(self.project_path, "r") as f:
            raw_data = json.load(f)

        screenshots = raw_data['screenshots']

        with VIANProject().load_project(self.project_path) as vian_project:
            for s in screenshots:
                elem = vian_project.get_by_id(s['unique_id'])
                assert elem is not None

        with open(self.project_path, "r") as f:
            raw_data_tampered = json.load(f)

        out_of_bound_screenshot = screenshots[0]
        out_of_bound_screenshot['frame_pos'] = 10**10
        raw_data_tampered['screenshots'].append(out_of_bound_screenshot)

        path2 = self.project_path.replace(".eext", "tampered.eext")
        with open(path2, "w") as f:
            json.dump(raw_data_tampered, f)

        self.assertRaises(ValueError, VIANProject().load_project, path2)











