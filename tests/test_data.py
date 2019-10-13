import unittest

import os
import shutil
import json
import requests

from core.data.importers import ExperimentTemplateImporter
from core.container.project import VIANProject

from core.data.creation_events import get_path_of_pipeline_script

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
            with open("../extensions/pipelines/ercfilmcolors.py", "r") as f:
                script = f.read()
            project.import_(ExperimentTemplateImporter(), "data/test-template.json")
            pipeline = project.create_pipeline_script(name="ERCFilmColors Pipeline",author="ERCFilmColors", script=script)

            project.experiments[0].pipeline_script = pipeline
            pipeline.experiment = project.experiments[0]

            # project.add_pipeline_script("../extensions/pipelines/ercfilmcolors.py")
            project.active_pipeline_script = pipeline
            project.compute_pipeline_settings = dict(segments=False,
                                                          screenshots=True,
                                                          annotations=False)
            with open("ERC-FilmColors-Template.viant", "w") as f:
                json.dump(project.get_template(segm=True, voc=True, experiment=True, pipeline=True), f)
            print("Exported")
        with VIANProject("TestProject", folder="data") as project:
            project.apply_template("ERC-FilmColors-Template.viant")
            print(project.pipeline_scripts)
            self.assertTrue(project.active_pipeline_script is not None)
            for v in project.vocabularies:
                v.export_vocabulary("../data/vocabularies/" + v.name + ".json")

if __name__ == '__main__':
    unittest.main()