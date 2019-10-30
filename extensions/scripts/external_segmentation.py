import glob
import cv2
from core.data.headless import *
from threading import Thread

IMPORT = False
if __name__ == '__main__':
    root = "C:\\Users\\Gaudenz Halter\\Desktop\\1684_Les_demoiselles_de_Rochefort_1967\\shots\\"
    file = "C:\\Users\\Gaudenz Halter\\Desktop\\1684_Les_demoiselles_de_Rochefort_1967\\1684_1_1_LesDemoisellesDeRochefort_1967_DVD_VIAN.eext"

    project, mw = load_project_headless(file)
    #project.movie_descriptor.set_movie_path("C:\\Users\\Gaudenz Halter\\Desktop\\1684_Les_demoiselles_de_Rochefort_1967\\1684_1_1_LesDemoisellesDeRochefort_1967_DVD.mov")

    if IMPORT:
        mw.load_screenshots()
        for scr in project.screenshots:
            cv2.imwrite(root + str(scr.unique_id) + ".png", scr.img_movie)
    else:
        project.apply_template("..\..\data\\templates\ERC_FilmColors.viant")
        mroot = "C:\\Users\\Gaudenz Halter\\Desktop\\1684_Les_demoiselles_de_Rochefort_1967\\masks\\"
        for scr in project.screenshots:
            mask = cv2.imread(mroot + str(scr.unique_id) + ".png")
            mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            analyis = SemanticSegmentationAnalysisContainer(
                analysis_job_class=SemanticSegmentationAnalysis,
                parameters=None,
                container=scr,
                dataset=DATASET_NAME_ADE20K)
            project.add_analysis(analyis)
            analyis.set_adata(mask)

    project.store_project()