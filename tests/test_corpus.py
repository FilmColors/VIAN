import unittest
import os
import shutil
import time

from core.container.corpus import Corpus
from core.container.project import VIANProject

p0 = "C:\\Users\\gaude\\Documents\\VIAN\\projects\\trailer.mp4"
p1 = "C:\\Users\\gaude\\Documents\\VIAN\\projects\\Blade_Runner_2049.mkv"
p2 = "E:\\Video\\New Girl Season 1  Paramount Comedy\\new.girl.s01e01.web-dlrip.rus.eng.paramount.comedy.avi"
p3 = "E:\\Video\\Ratatouille (2007) [1080p]\\Ratatouille.2007.1080p.BrRip.x264.YIFY.mp4"
p4 = "E:\\Video\\The Matrix 1999 1080p BDRip Ita Eng Ac3 Sub Ita Eng x265-NAHOM\\The Matrix 1999 1080p BDRip Ita Eng Ac3 Sub Ita Eng x265-NAHOM.mkv"
p5 = "E:\\Video\\Brave (2012) [1080p]\\Brave.2012.1080p.BRrip.x264.YIFY.mp4"

videos = [p0, p1, p2, p3, p4, p5]

class TestCreate(unittest.TestCase):
    def setUp(self) -> None:
        os.mkdir("data")

    def tearDown(self) -> None:
        shutil.rmtree("data")

    def test_serialization(self):
        corpus = Corpus("TestCorpus", directory="data/")
        corpus.save("data/corpus.vian_corpus")
        corpus2 = Corpus("TestCorpus", directory="data/")
        corpus2.load("data/corpus.vian_corpus")

    def test_project_management(self):
        os.mkdir("data/projects/")

        corpus = Corpus("TestCorpus", directory="data/")

        proj1 = VIANProject("P1", folder="data/projects/p1", movie_path=p1)
        proj1.store_project()
        proj2 = VIANProject("P2", folder="data/projects/p2", movie_path=p2)
        proj2.store_project()
        proj3 = VIANProject("P3", folder="data/projects/p3", movie_path=p3)
        proj3.store_project()
        proj4 = VIANProject("P4", folder="data/projects/p4", movie_path=p4)
        proj4.store_project()

        corpus.add_project(proj1)
        corpus.add_project(proj2)
        corpus.add_project(file=proj3.path)
        corpus.add_project(file=proj4.path)

        self.assertTrue(len(corpus.project_paths) == 4)
        self.assertTrue(len(corpus.projects_loaded) == 4)

        corpus.remove_project(proj1)
        corpus.remove_project(file=proj4.path)

        self.assertTrue(len(corpus.project_paths) == 2)
        self.assertTrue(len(corpus.projects_loaded) == 2)

        corpus.remove_project(file=proj3.path, delete_from_disk=True)
        self.assertTrue(not os.path.isdir(proj3.folder))



if __name__ == '__main__':
    unittest.main()