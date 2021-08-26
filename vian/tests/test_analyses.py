import unittest
import os
import shutil
import time

from vian.core.analysis.shot_segmentation import ShotSegmentationAnalysis
from vian.core.container.project import VIANProject
p0 = "C:\\Users\\gaude\\Documents\\VIAN\\projects\\trailer.mp4"
p1 = "C:\\Users\\gaude\\Documents\\VIAN\\projects\\Blade_Runner_2049.mkv"
p2 = "E:\\Video\\New Girl Season 1  Paramount Comedy\\new.girl.s01e01.web-dlrip.rus.eng.paramount.comedy.avi"
p3 = "E:\\Video\\Ratatouille (2007) [1080p]\\Ratatouille.2007.1080p.BrRip.x264.YIFY.mp4"
p4 = "E:\\Video\\The Matrix 1999 1080p BDRip Ita Eng Ac3 Sub Ita Eng x265-NAHOM\\The Matrix 1999 1080p BDRip Ita Eng Ac3 Sub Ita Eng x265-NAHOM.mkv"
p5 = "E:\\Video\\Brave (2012) [1080p]\\Brave.2012.1080p.BRrip.x264.YIFY.mp4"


class TestCreate(unittest.TestCase):
    def setUp(self) -> None:
        os.mkdir("data")

    def tearDown(self) -> None:
        shutil.rmtree("data")

    def test_shot_segmentation(self):
        with VIANProject(name="TestProject",
                         path="data/test_project.eext",
                         movie_path=p0) as project:
            t = time.time()
            model = ShotSegmentationAnalysis()
            X = model.fit(project.movie_descriptor)

            model = ShotSegmentationAnalysis(return_hdf5_compatible=True)
            X = model.fit(project.movie_descriptor)

if __name__ == '__main__':
    unittest.main()