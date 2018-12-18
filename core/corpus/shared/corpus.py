import glob
from core.corpus.shared.sqlalchemy_entities import *
from core.data.headless import *
import cv2
import numpy as np
import csv
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker
from core.data.computation import ms_to_frames
from core.corpus.shared.hdf5_database import HDF5ManagerDatabase
import datetime
import time

class VIANCorpus(QObject):
    def __init__(self, path):
        super(VIANCorpus, self).__init__()
        self.sql_path = "sqlite:///" + path
        self.hdf5_path = path.replace(".db", ".hdf5").replace("database", "analyses")
        self.hdf5_manager = HDF5ManagerDatabase(self.hdf5_path)
        self.engine = create_engine(self.sql_path, echo=True, connect_args={"check_same_thread":False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

    def commit_project(self, zip_path):
        pass

    def get_project(self, project_id):
        pass

    def get_template(self, location):
        root = location + "/gen_template/"
        segmentations = self.db.query(DBSegmentation).all()     #type:List[DBSegmentation]
        layers = self.db.query(DBAnnotationLayer).all()         #type:List[DBAnnotationLayer]
        experiments = self.db.query(DBExperiment).all()         #type:List[DBExperiment]
        vocabularies = self.db.query(DBVocabulary).all()        #type:List[DBVocabulary]

        voc_idx = dict()
        word_idx = dict()
        clobj_idx = dict()

        if not os.path.isdir(root):
            os.mkdir(root)

        project = create_project_headless("Template", root, "E:\Programming\Git\\visual-movie-annotator\data\dummy.mp4")
        for s in segmentations:
            project.create_segmentation(s.name)

        for l in layers:
            project.create_annotation_layer(l.name)

        for v in vocabularies:
            voc = project.create_vocabulary(v.name)
            voc.category = v.vocabulary_category.name
            voc_idx[v.id] = voc
            for w in v.vocabulary_words:
                word = voc.create_word(w.name)
                word_idx[w.id] = word


        for e in experiments:
            exp = project.create_experiment()
            exp.name = e.name
            all_ids = []
            for obj in e.classification_objects: #type:DBClassificationObject
                added_vocabularies = dict()
                clobj = exp.create_class_object(obj.name, exp)
                clobj_idx[obj.id] = clobj
                for ukw in obj.unique_keywords: #type:DBUniqueKeyword
                    if not ukw.word.vocabulary_id in added_vocabularies:
                        clobj.classification_vocabularies.append(voc_idx[ukw.word.vocabulary_id])
                    voc = voc_idx[ukw.word.vocabulary_id]
                    keyword = UniqueKeyword(exp, voc, word_idx[ukw.word.id], clobj)
                    keyword.external_id = ukw.id
                    all_ids.append(ukw.id)
                    keyword.set_project(project)
                    clobj.unique_keywords.append(keyword)
                ds_name = ""
                ds_labels = []
                for lbl in obj.semantic_segmentation_labels: #type:DBSemanticSegmentationLabel
                    if ds_name == "":
                        ds_name = lbl.dataset.name
                    ds_labels.append(lbl.mask_idx - 1)

                clobj.semantic_segmentation_labels = (ds_name, list(set(ds_labels)))
        # project.store_project(HeadlessUserSettings())
        template = project.get_template(True, True, True, True, True)
        try:
            project.hdf5_manager.on_close()
            project.main_window.close()
            print("Closed")
            shutil.rmtree(root)
        except Exception as e:
            print(e)
        return template

if __name__ == '__main__':
    corpus = VIANCorpus("F:/_corpus/ERCFilmColors_V2/database.db")
    template = corpus.get_template("C:\\Users\\Gaudenz Halter\\Documents\\VIAN\\corpora\\")
    with open("ERC_FilmColors.viant", "w") as f:
        json.dump(template, f)