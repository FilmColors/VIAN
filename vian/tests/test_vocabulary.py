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
        self.test_temp_folder = os.path.join(os.getcwd(), "temp")

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)

    def tearDown(self) -> None:
        shutil.rmtree(self.test_temp_folder)


    def test_vocabulary_updating(self):
        """
        Here we simply check if CRUD operations remain consistent with the json file
        :return:
        """

        lib_path = os.path.join(self.test_temp_folder, "library.json")
        with VIANProject() as p:
            voc1 = p.create_vocabulary("Some Voc")
            voc1.create_word("Word 11")
            voc1.create_word("Word 12")

            voc2 =p.create_vocabulary("Some Voc")
            voc2.create_word("Word 21")
            voc2.create_word("Word 22")
            voc2.update_vocabulary2(voc1, join_field="name", update_scheme="cud")
            assert set([w.name for w in voc2.words_plain]) == {"Word 11", "Word 12"}

            voc3 = p.create_vocabulary("Some Voc")
            voc3.create_word("Word 21")
            voc3.create_word("Word 22")
            voc3.update_vocabulary2(voc1, join_field="name", update_scheme="cu")
            assert set([w.name for w in voc3.words_plain]) == {"Word 11", "Word 12", "Word 22", "Word 21"}

            voc2 =p.create_vocabulary("Some Voc")
            voc2.create_word("Word 21")
            voc2.create_word("Word 22")

            voc3 = p.create_vocabulary("SweetVoc")
            voc3.create_word("Word 21")
            voc3.create_word("Word 22")
            voc3.update_vocabulary2(voc2, join_field="unique_id", update_scheme="cu")
            print(voc3.words_plain)
            assert set([w.name for w in voc3.words_plain]) == {"Word 21", "Word 22", "Word 22", "Word 21"}


