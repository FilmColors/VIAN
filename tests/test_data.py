import unittest

import os
import shutil
import json
import requests

from core.data.importers import ExperimentTemplateImporter
from core.container.project import VIANProject

class TestImportMethods(unittest.TestCase):
    def setUp(self) -> None:
        os.mkdir("data")

    def tearDown(self) -> None:
        shutil.rmtree("data")

    def test_1_api_experiments(self):
        r = requests.get("http://ercwebapp.westeurope.cloudapp.azure.com/api/experiments/")
        experiments = r.json()
        self.assertIsInstance(experiments, list)

        r = requests.get("http://ercwebapp.westeurope.cloudapp.azure.com/api/experiments/" + str(experiments[0]['id']))
        self.exchange_data = r.json()

        with open("data/test-template.json", "w") as f:
            json.dump(self.exchange_data, f)
        with open("test-template.json", "w") as f:
            json.dump(self.exchange_data, f)
        with VIANProject("TestProject") as project:
            project.import_(ExperimentTemplateImporter(), "data/test-template.json")
            with open("ERC-FilmColors-Template.viant", "w") as f:
                json.dump(project.get_template(segm=True, voc=True, experiment=True, pipeline=True), f)

if __name__ == '__main__':
    unittest.main()