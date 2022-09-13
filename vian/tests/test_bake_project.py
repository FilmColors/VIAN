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
- Vocabulary Library should be serialized and deserialized correctly 
- When opening an existing project which already has some of the vocabularies attached do the following: 
    - If 

"""

class TestProjectBaking(unittest.TestCase):
    def setUp(self) -> None:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        self.test_temp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        self.unpacked_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unpacked")
        shutil.unpack_archive("netflix_test_project.zip", self.unpacked_folder)

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_temp_folder)
        shutil.rmtree(self.unpacked_folder)


    def test_bake_project(self):
        """
        Here we simply check if CRUD operations remain consistent with the json file
        :return:
        """
        return #todo: fix this test. Permission error in project.zip_baked().

        values_to_compare = dict()
        with VIANProject().load_project(os.path.join(self.unpacked_folder, "NETFLIX_VOCABULARY.eext")) as project:
            for a in project.analysis:
                if a.__class__ ==  IAnalysisJobAnalysis:
                    values_to_compare[a.unique_id] = a.get_adata(raw=True)

            for a in project.analysis:
                if not isinstance(a, ColormetryAnalysis):
                    if a.__class__ == IAnalysisJobAnalysis:
                        assert np.all(np.equal(values_to_compare[a.unique_id], a.get_adata(raw=True)))

            for s in project.screenshots:
                assert s.get_img_movie_orig_size() is not None

        with VIANProject().load_project(os.path.join(self.unpacked_folder, "NETFLIX_VOCABULARY.eext")) as project:
            bake_path = project.store_project(bake=True)
            archive_name = project.zip_baked(bake_path)
            assert os.path.isfile(archive_name)

        archive_name2 = os.path.join(self.test_temp_folder, os.path.basename(archive_name))
        shutil.copy2(archive_name, archive_name2)
        shutil.unpack_archive(archive_name2, self.test_temp_folder + "/unpacked")

        with VIANProject().load_project(os.path.join(self.unpacked_folder, "NETFLIX_VOCABULARY_baked.eext")) as project:
            for a in project.analysis:
                if not isinstance(a, ColormetryAnalysis):
                    if a.__class__ == IAnalysisJobAnalysis:
                        assert np.all(np.equal(values_to_compare[a.unique_id], a.get_adata(raw=True)))

            for s in project.screenshots:
                assert s.get_img_movie_orig_size() is not None







