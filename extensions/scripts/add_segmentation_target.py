"""
This script has been used to fix the missing target_container in the experiments of the FilmColors Corpus.
"""

import glob

from core.data.headless import *

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
