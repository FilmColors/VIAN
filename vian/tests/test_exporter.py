import unittest
import os
import shutil
import difflib
import pandas as pd

from vian.tests.utils import *
from vian.core.data.exporters import SequenceProtocolExporter


class TestExporterMethods(unittest.TestCase):
    def setUp(self) -> None:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        self.test_temp_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
        self.unpacked_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "unpacked")
        shutil.unpack_archive("netflix_test_project.zip", self.unpacked_folder)

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)

    def tearDown(self) -> None:
        self.project.cleanup()
        shutil.rmtree(self.test_temp_folder)
        shutil.rmtree(self.unpacked_folder)

    def test_csv_sequence_export(self):
        # arrange
        self.ground_truth_csv = os.path.join(self.unpacked_folder, "ground_truth_csv_export1.csv")
        self.project = get_VIANProject1_exporter()
        self.path = os.path.join(self.test_temp_folder, "test_csv_export.csv")

        # act
        exporter = SequenceProtocolExporter()
        exporter.export(self.project, self.path)

        # assert
        ground_truth = open(self.ground_truth_csv, "r")
        csv_gt = ground_truth.readlines()
        exporter_result = open(self.path, "r")
        csv_er = exporter_result.readlines()

        is_same = True
        for line in difflib.unified_diff(csv_gt, csv_er):
            print(line)
            is_same = False

        ground_truth.close()
        exporter_result.close()

        self.assertTrue(is_same, "The generated CSV output does not match the expected output. See above.")

    def test_csv_netflix_project(self):
        # arrange
        self.ground_truth_csv = os.path.join(self.unpacked_folder, "ground_truth_csv_export_netflix.csv")
        self.project = VIANProject()
        self.project.load_project(path=os.path.join(self.unpacked_folder, "NETFLIX_VOCABULARY.eext"))

        self.path = os.path.join(self.test_temp_folder, "test_csv_export.csv")

        # act
        exporter = SequenceProtocolExporter()
        exporter.export(self.project, self.path)

        # assert
        ground_truth = open(self.ground_truth_csv, "r")
        csv_gt = ground_truth.readlines()
        exporter_result = open(self.path, "r")
        csv_er = exporter_result.readlines()

        is_same = True
        for line in difflib.unified_diff(csv_gt, csv_er):
            print(line)
            is_same = False

        ground_truth.close()
        exporter_result.close()

        self.assertTrue(is_same, "The generated CSV output does not match the expected output. See above.")

    def test_csv_excel_netflix_export(self):
        # arrange
        self.ground_truth_xlsx = os.path.join(self.unpacked_folder, "ground_truth_csv_excel_netflix.xlsx")
        self.project = VIANProject()
        self.project.load_project(path=os.path.join(self.unpacked_folder, "NETFLIX_VOCABULARY.eext"))

        self.path = os.path.join(self.test_temp_folder, "test_csv_export.xlsx")

        # act
        exporter = SequenceProtocolExporter(export_format=SequenceProtocolExporter.FORMAT_EXCEL)
        exporter.export(self.project, self.path)

        # assert
        df1 = pd.read_excel(self.ground_truth_xlsx, engine='openpyxl')
        df2 = pd.read_excel(self.path, engine='openpyxl')

        difference = df1[df1 != df2]
        for row in range(difference.shape[0]):
            for column in range(difference.shape[1]):
                if not pd.isnull(difference.values[row][column]):
                    print("Difference at [{},{}]. Ground truth is \"{}\", exported value is \"{}\"."
                          .format(row, column, df1.values[row][column], df2.values[row][column]))

        self.assertTrue(difference.isnull().all().all(),
                        "The generated Excel output does not match the expected output. See above.")
