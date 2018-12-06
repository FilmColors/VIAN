import glob
from core.corpus.shared.sqlalchemy_entities import *
from core.data.headless import *
import cv2
import numpy as np
import csv
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker
from core.data.computation import ms_to_frames
from core.corpus.shared.corpus import VIANCorpus
import datetime

if __name__ == '__main__':
    for f in glob.glob("F:\\_projects\\*\\*.eext"):
        p, mw = load_project_headless(f)
        segm = None
        exp = None
        if len(p.segmentation) > 0:
            segm = p.segmentation[0]
        if len(p.experiments) > 0:
            exp = p.experiments[0]

        if segm is not None and exp is not None:
            for clobj in exp.classification_objects:
                if len(clobj.target_container) == 0:
                    clobj.target_container.append(segm)

        p.store_project(HeadlessUserSettings())
