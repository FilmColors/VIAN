import unittest
import os
import shutil
import difflib

from utils import *
from core.data.exporters import SequenceProtocolExporter


class TestExporterMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.test_temp_folder = os.path.join(os.getcwd(), "temp")

        if not os.path.exists(self.test_temp_folder):
            os.mkdir(self.test_temp_folder)


    def tearDown(self) -> None:

    def test_csv_sequence_export(self):

        self.ground_truth_csv = os.path.join(os.getcwd(), os.path.join("data", "ground_truth_csv_export1.csv"))
        self.project = get_VIANProject1_exporter()
        self.path = os.path.join(self.test_temp_folder, "test_csv_export.csv")

        exporter = SequenceProtocolExporter()
        exporter.export(self.project, self.path)

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

        self.ground_truth_csv = os.path.join(os.getcwd(), os.path.join("data", "ground_truth_csv_export1.csv"))
        self.project = VIANProject()
        self.project.load_project(path = os.path.join(os.getcwd(), os.path.join("data", "NETFLIX_VOCABULARY.eext")))
        self.path = os.path.join(self.test_temp_folder, "test_csv_export.csv")

        exporter = SequenceProtocolExporter()
        exporter.export(self.project, self.path)

    def test_csv_excel_export(self):
        self.ground_truth_csv = os.path.join(os.getcwd(), os.path.join("data", "ground_truth_csv_export1.csv"))
        self.project = VIANProject()
        self.project.load_project(path=os.path.join(os.getcwd(), os.path.join("data", "NETFLIX_VOCABULARY.eext")))
        self.path = os.path.join(self.test_temp_folder, "test_csv_export.xlsx")

        exporter = SequenceProtocolExporter(export_format=SequenceProtocolExporter.FORMAT_EXCEL)
        exporter.export(self.project, self.path)


