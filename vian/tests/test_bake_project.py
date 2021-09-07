import unittest
import os
import shutil
import difflib
import pandas as pd

from vian.core.analysis.analysis_import import *

from vian.tests.utils import *
from vian.core.container.vocabulary_library import Vocabulary, VocabularyLibrary, VocabularyCollection
"""
Test cases: 
- Vocabulary Library should be serialized and desierualized correctly 
- When opening an existing project which already has some of the vocabularies attached do the following: 
    - If 

"""

class TestProjectBaking(unittest.TestCase):
    def setUp(self) -> None:
        self.test_temp_folder = os.path.join(os.getcwd(), "temp2")

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_temp_folder)


    def test_bake_project(self):
        """
        Here we simply check if CRUD operations remain consistent with the json file
        :return:
        """
        pass

        shutil.copytree(get_test_data_dir(), self.test_temp_folder + "/data")

        values_to_compare = dict()
        with VIANProject().load_project(self.test_temp_folder + "/data/NETFLIX_VOCABULARY.eext") as project:
            for a in project.analysis:
                if a.__class__ ==  IAnalysisJobAnalysis:
                    values_to_compare[a.unique_id] = a.get_adata(raw=True)
            project.store_project(bake=True)

        with VIANProject().load_project(self.test_temp_folder + "/data/NETFLIX_VOCABULARY_baked.eext") as project:
            for a in project.analysis:
                if not isinstance(a, ColormetryAnalysis):
                    if a.__class__ == IAnalysisJobAnalysis:
                        assert np.all(np.equal(values_to_compare[a.unique_id], a.get_adata(raw=True)))







