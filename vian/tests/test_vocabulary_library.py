import unittest
import os
import shutil
import difflib
import pandas as pd

from vian.tests.utils import *
from vian.core.container.vocabulary_library import Vocabulary, VocabularyLibrary, VocabularyCollection
"""
Test cases: 
- Vocabulary Library should be serialized and desierualized correctly 
- When opening an existing project which already has some of the vocabularies attached do the following: 
    - If 

"""

class TestVocabularyLibraryMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.test_temp_folder = os.path.join(os.getcwd(), "temp2")

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_temp_folder)


    def test_crud_vocabulary(self):
        """
        Here we simply check if CRUD operations remain consistent with the json file
        :return:
        """

        lib_path = os.path.join(self.test_temp_folder, "library.json")

        # Get a new Vocabulary Library, and ensure it is stored to the disk after every change
        voc_library = VocabularyLibrary()
        voc_library.save(lib_path)
        voc_library.file_path = lib_path

        # CRUD Collections
        col = voc_library.create_collection("Sample Collection 1")
        assert "Sample Collection 1" in [v.name for v in VocabularyLibrary().load(lib_path).collections.values()]

        col.set_name("Sample Collection 1\'")
        assert "Sample Collection 1\'" in [v.name for v in VocabularyLibrary().load(lib_path).collections.values()]

        voc_library.remove_collection(col)
        assert "Sample Collection 1\'" not in [v.name for v in VocabularyLibrary().load(lib_path).collections.values()]

        # CRUD Vocabularies
        col = voc_library.create_collection("Sample Collection 1")
        voc = col.create_vocabulary("Vocabulary 1")
        w1 = voc.create_word("Word 1")
        w2 = voc.create_word("Word 2")
        w3 = voc.create_word("Word 3")

        assert "Vocabulary 1" in [v.name for v in VocabularyLibrary().load(lib_path).collections[col.unique_id].vocabularies.values()]
        _voc = VocabularyLibrary().load(lib_path).collections[col.unique_id].vocabularies[voc.unique_id]
        assert {"Word 1", "Word 2", "Word 3"} == set([w.name for w in _voc.words_plain])

        voc.remove_word(w1)
        _voc = VocabularyLibrary().load(lib_path).collections[col.unique_id].vocabularies[voc.unique_id]
        assert { "Word 2", "Word 3"} == set([w.name for w in _voc.words_plain])

        w2.set_name("Word 4")
        _voc = VocabularyLibrary().load(lib_path).collections[col.unique_id].vocabularies[voc.unique_id]
        assert { "Word 4", "Word 3"} == set([w.name for w in _voc.words_plain])

        col.remove_vocabulary(voc)
        assert "Vocabulary 1" not in [v.name for v in VocabularyLibrary().load(lib_path).collections[col.unique_id].vocabularies.values()]

    def test_merge(self):
        """
        Here three cases are checked all based on the following scenario.
        1. A User creates an initial project and vocabularies using the VocabularyLibrary.
        2. Creates a second project based on the same vocabularies
        3. Edits the vocabularies in the first project
        4. Opens the second vocabularies again


        :return:
        """

        lib_path = os.path.join(self.test_temp_folder, "library.json")
        p1_path = os.path.join(self.test_temp_folder, "project1/project1.eext")
        p2_path = os.path.join(self.test_temp_folder, "project2/project2.eext")

        # Get a new Vocabulary Library, and ensure it is stored to the disk after every change
        voc_library = VocabularyLibrary()
        voc_library.save(lib_path)
        voc_library.file_path = lib_path

        # Create a vocabulary
        col = voc_library.create_collection("Sample Collection 1")
        voc = col.create_vocabulary("Vocabulary 1")
        w1 = voc.create_word("Word 1")
        w2 = voc.create_word("Word 2")
        w3 = voc.create_word("Word 3")

        # First Project
        with VIANProject("Project 1", path=p1_path) as p1:
            cl_obj = p1.get_default_experiment().create_class_object("Global")
            (kwd1, kwd2, kwd3) = cl_obj.add_vocabulary(voc)

            assert {w1, w2, w3} == set([w.word_obj for w in cl_obj.unique_keywords])

            segmentation = p1.create_segmentation("Segmentation 1")
            segment = segmentation.create_segment2(0, 100)
            segment.add_tag(kwd1)
            segment.add_tag(kwd2)

            p1.store_project()

        print("Loading second")
        with VIANProject().load_project(p1_path, library=voc_library) as p2:
            p2.name = "Project 2"

            # Ensure the loaded vocabulary is the same
            assert set([w.unique_id for w in p2.vocabularies[0].words_plain]) == {w1.unique_id, w2.unique_id, w3.unique_id}
            segment = p2.segmentation[0].segments[0]
            assert len(segment.tag_keywords) == 2

            (kwd1, kwd2, kwd3) = p2.get_default_experiment().get_unique_keywords()

            for kwd in p2.get_default_experiment().get_unique_keywords():
                segment.add_tag(kwd)
            assert len(segment.tag_keywords) == 3

            p2.store_project(p2_path)

        word = voc.create_word("Another Word")
        with VIANProject().load_project(p2_path, library=voc_library) as p2:
            assert len(p2.get_default_experiment().get_unique_keywords()) == 4
            p2.store_project(p2_path)
        voc.remove_word(word)

        # Ensure that without delete mode the word is kept
        with VIANProject().load_project(p2_path, library=voc_library, vocabulary_update_scheme="cu") as p2:
            assert len(p2.get_default_experiment().get_unique_keywords()) == 4
            assert len(p2.segmentation[0].segments[0].tag_keywords) == 3


        # Use the d flag
        with VIANProject().load_project(p2_path, library=voc_library, vocabulary_update_scheme="cud") as p2:
            assert len(p2.get_default_experiment().get_unique_keywords()) == 3
            assert len(p2.segmentation[0].segments[0].tag_keywords) == 3


        # Remove another word
        voc.remove_word(voc.words_plain[0])
        with VIANProject().load_project(p2_path, library=voc_library, vocabulary_update_scheme="cud") as p2:
            assert len(p2.get_default_experiment().get_unique_keywords()) == 2
            assert len(p2.segmentation[0].segments[0].tag_keywords) == 2


