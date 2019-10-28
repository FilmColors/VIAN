import unittest

import os
import shutil
import json
import requests

from core.data.importers import ExperimentTemplateImporter
from core.container.project import VIANProject
from core.container.experiment import merge_experiment, merge_experiment_inspect
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
            self.assertTrue(project.active_pipeline_script is not None)
            for v in project.vocabularies:
                r = requests.get("http://ercwebapp.westeurope.cloudapp.azure.com/api/query/vocabulary_hash/" + v.unique_id)
                print(r.json())

                # v.export_vocabulary("../data/vocabularies/" + v.name + ".json")

    def test_2_merge_experiments(self):
        r = requests.get("http://ercwebapp.westeurope.cloudapp.azure.com/api/experiments/1")
        self.exchange_data = r.json()

        with open("data/test-template.json", "w") as f:
            json.dump(self.exchange_data, f)

        with VIANProject("TestProject") as project1:
            project1.import_(ExperimentTemplateImporter(), "data/test-template.json")
            with VIANProject("TestProject") as project2:
                project2.import_(ExperimentTemplateImporter(), "data/test-template.json")
                cl_obj_global = project2.experiments[0].get_classification_object_by_name("Global")
                project2.experiments[0].remove_classification_object(cl_obj_global)
                # for v in merge_experiment_inspect(project2.experiments[0], project1.experiments[0]):
                #     print(v)

                cl_new = project2.experiments[0].create_class_object("AnotherCL")
                v_new = project2.create_vocabulary("AnotherV")
                v_new.create_word("w1")
                v_new.create_word("w2")
                cl_new.add_vocabulary(v_new)

                # for v in merge_experiment_inspect(project2.experiments[0], project1.experiments[0]):
                #     print(v)

                merge_experiment(project2.experiments[0], project1.experiments[0])
                print(len(project1.experiments[0].get_unique_keywords()),
                      len(project2.experiments[0].get_unique_keywords()))
                self.assertFalse(len(project1.experiments[0].get_unique_keywords()) ==
                                len(project2.experiments[0].get_unique_keywords()))

                t1 = [(q.word_obj.unique_id, q.voc_obj.unique_id, q.class_obj.unique_id) for q in project1.experiments[0].get_unique_keywords()]
                t2 = [(q.word_obj.unique_id, q.voc_obj.unique_id, q.class_obj.unique_id) for q in
                      project2.experiments[0].get_unique_keywords()]

                self.assertFalse(set(t1) == set(t2))

                merge_experiment(project2.experiments[0], project1.experiments[0], drop=True)
                print(len(project1.experiments[0].get_unique_keywords()),
                      len(project2.experiments[0].get_unique_keywords()))

                self.assertTrue(len(project1.experiments[0].get_unique_keywords()) ==
                                 len(project2.experiments[0].get_unique_keywords()))

                t1 = [(q.word_obj.unique_id, q.voc_obj.unique_id, q.class_obj.unique_id) for q in
                      project1.experiments[0].get_unique_keywords()]
                t2 = [(q.word_obj.unique_id, q.voc_obj.unique_id, q.class_obj.unique_id) for q in
                      project2.experiments[0].get_unique_keywords()]

                self.assertTrue(set(t1) == set(t2))

    def test_3_merge_template(self):
        r = requests.get("http://ercwebapp.westeurope.cloudapp.azure.com/api/experiments/1")
        self.exchange_data = r.json()

        with open("data/test-template.json", "w") as f:
            json.dump(self.exchange_data, f)

        with VIANProject("TestProject") as project1:
            project1.import_(ExperimentTemplateImporter(), "data/test-template.json")


            with open("../extensions/pipelines/ercfilmcolors.py", "r") as f:
                script = f.read()
            pipeline = project1.create_pipeline_script(name="ERCFilmColors Pipeline", author="ERCFilmColors",
                                                       script=script)

            project1.experiments[0].pipeline_script = pipeline
            pipeline.experiment = project1.experiments[0]

            project1.active_pipeline_script = pipeline
            project1.compute_pipeline_settings = dict(segments=False,
                                                      screenshots=True,
                                                      annotations=False)
            tmpl = project1.get_template(True, True, True, True, True, True)

            with VIANProject("TestProject") as project2:
                project2.apply_template(template=tmpl,  script_export="data/")
                print(len(project1.experiments[0].get_unique_keywords()),
                      len(project2.experiments[0].get_unique_keywords()))

                cl_obj_global = project2.experiments[0].get_classification_object_by_name("Global")
                project2.experiments[0].remove_classification_object(cl_obj_global)

                cl_new = project1.experiments[0].create_class_object("AnotherCL")
                v_new = project1.create_vocabulary("AnotherV")
                v_new.create_word("w1")
                v_new.create_word("w2")
                cl_new.add_vocabulary(v_new)

                tmpl = project1.get_template(True, True, True, True, True, True)
                res = project2.apply_template(template=tmpl, merge=True, script_export="data/")

                print(res)
                for r in res:
                    print(r)
                print(len(project1.experiments[0].get_unique_keywords()),
                      len(project2.experiments[0].get_unique_keywords()))


if __name__ == '__main__':
    unittest.main()