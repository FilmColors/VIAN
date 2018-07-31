import csv
import pickle
from sys import stdout as console

from core.corpus.shared.entities import *
from core.data.headless import *
from core.data.computation import *
from extensions.plugins.fiwi_tools.vian_dev.fiwi_server_binding.python_binding import MovieAsset, ScreenshotAsset
from threading import Thread
import argparse

PRINT_PROGRESS = False

"""
A Mapping of Filmography Column Names to their respective attribute name in the DBFilmography Class
"""

import threading

ERROR_LIST = []
PROJECT_PATHS = []
PROJECT_FILE_PATH = "F:\\_projects\\all_projects.txt"

corpus_path = "F:/_input/CorpusDB.csv"
gloss_file = "F:/_input/GlossaryDB_WordCount.csv"
db_file = "F:/_input/MasterDB_WordCount.csv"
outfile = "../../results/counting.csv"
asset_path = "F:/fiwi_datenbank/PIPELINE_RESULTS/ASSETS/"
result_path = "F:/_output/"
project_dir = "F:/_projects/"
fiwi_root = "F:/fiwi_datenbank/"
cache_dir = "F:/_cache/"
template_path = "E:/Programming/Git/visual-movie-annotator/user/templates/ERC_FilmColors.viant"


CorpusDBMapping = dict(
    imdb_id = "IMDb ID",
    filemaker_id = "FileMaker ID",
    title = "Title",
    country = "Country",
    year = "Year",
    color_process = "Color Process",
    director = "Director",
    genre = "Genre",
    cinematography = "Cinematography",
    color_consultant = "Color Consultant",
    production_design = "Production Design",
    art_director = "Art Director",
    costum_design = "Costum Design",
    production_company = "Production Company",
    corpus_assignment = "Corpus Assignment",
    editors = "Editors"
)

MasterDBMapping = dict(
    start = "exp_Start",
    end = "exp_End",
    annotation = "exp_Annotation"
)

def progress(stage, movie, progress, sub_progress):
    if not PRINT_PROGRESS:
        return
    console.write("\r" + stage.rjust(15) + "\t" + "".join(["#"] * int(sub_progress * 100)).ljust(100) + "\t" + str(round(sub_progress, 2)))


def replace_network_path(old):
    return old.replace("\\", "/").replace("//130.60.131.134/", "F:/").replace("/Volumes/", "F:/").replace("_output//", "fiwi_datenbank/PIPELINE_RESULTS/")


def generate_project(entry, result_dir, glossary_words, glossary_ids2, glossary_categories, glossary_omit, replace_path = False):
    try:
        dbmovie = DBMovie().from_database(entry['dbmovie'])
        filmography = entry['filmography']
        assignment = entry['assignment']
        masset = entry['movie_asset']
        fm_id_str = "_".join([masset['fm_id'][0].zfill(3), masset['fm_id'][1], masset['fm_id'][2]])

        # Skip this movie if it is already in the projects
        project_name = fm_id_str + "_" + dbmovie.movie_name + "_" + dbmovie.year
        project_name = project_name.replace(":", "").replace("\'", "").replace("?", "")
        print("### ---", project_name, "--- ###")
        movie_path = masset['movie_path']
        if replace_path:
            movie_path = replace_network_path(movie_path)

        project_folder = result_dir + "/" + project_name + "/"
        print(project_folder)
        if os.path.isdir(project_folder):
            print("Skipped")
            return

        vian_project = create_project_headless(project_name, project_folder, movie_path, [], [],
                                               move_movie="None",
                                               template_path=template_path)

        vian_project.inhibit_dispatch = True
        vian_project.movie_descriptor.meta_data['ERC_FilmColorsFilmography'] = filmography
        vian_project.movie_descriptor.movie_id = masset['fm_id']
        vian_project.movie_descriptor.year = dbmovie.year

        # Create an Experiment and a Main Segmentation
        experiment = vian_project.experiments[0]
        main_segm = vian_project.segmentation[0]

        # Create a Lookup Table for the GlossaryIDs
        exp_keywords = experiment.get_unique_keywords()
        glossary_ids = [k.external_id for k in exp_keywords]

        # Apply the Classification
        progress("Classification:", dbmovie.movie_name + "_" + str(dbmovie.movie_id), 0.1, 0.0)
        Errors = []
        for idx, s in enumerate(entry['filemaker'][1]):
            segment = DBSegment().from_database(s[0])
            keywords = s[1]

            # Filemaker exports timestamp without zfill and without ":" thus 00:00:12:34 becomes 1234
            start = segment.segm_start
            end = segment.segm_end
            new_segm = main_segm.create_segment2(int(start), int(end), body=segment.segm_body,
                                                 mode=SegmentCreationMode.INTERVAL, inhibit_overlap=False)
            for k in keywords:
                try:
                    uk = exp_keywords[glossary_ids.index(int(k))]
                    experiment.toggle_tag(new_segm, uk)
                except Exception as e:
                    idx = glossary_ids2.index(k)
                    if (glossary_words[idx], glossary_categories[idx]) not in Errors:
                        Errors.append((glossary_words[idx], glossary_categories[idx]))

        # Create Screenshots:
        cap = cv2.VideoCapture(movie_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        scr_groups = [""]
        mask_files = dict()
        scr_masks = []
        shot_index = dict()
        for i, scr in enumerate(masset['scrs']):

            # Add it to the Shot Index for later lookup
            if scr['segm_id'] not in shot_index:
                shot_index[scr['segm_id']] = dict()

            if scr['scr_grp'] not in scr_groups:
                grp = vian_project.add_screenshot_group(scr['scr_grp'])
                scr_groups.append(scr['scr_grp'])
            else:
                grp = vian_project.screenshot_groups[scr_groups.index(scr['scr_grp'])]

            shot = vian_project.create_screenshot_headless("SCR_" + str(i), scr['frame_pos'], fps=fps)
            shot_index[scr['segm_id']][scr['segm_shot_id']] = shot
            grp.add_screenshots([shot])
            mask_files[shot.unique_id] = scr['mask_file']
            scr_masks.append((shot, scr['mask_file']))

        # Analyses
        #
        #region  Fg/Bg Segmentation
        #
        a_class = SemanticSegmentationAnalysis
        c = 0
        analyses = []
        for shot, mask_file in scr_masks:
            try:
                mask = cv2.imread(replace_network_path(mask_file), 0)

                analysis = IAnalysisJobAnalysis(
                    name="Fg/Bg Segmentation",
                    results=dict(mask=mask.astype(np.uint8),
                                 frame_sizes=(mask.shape[0], mask.shape[1]),
                                 dataset=DATASET_NAME_ADE20K),
                    analysis_job_class=SemanticSegmentationAnalysis,
                    parameters=dict(model=DATASET_NAME_ADE20K, resolution=50),
                    container=shot
                )
                progress("Masks:", dbmovie.movie_name + "_" + str(dbmovie.movie_id), 0.1, c / len(scr_masks))
                analyses.append(analysis)
                analysis.a_class = a_class
                c += 1
            except:
                continue
        vian_project.add_analyses(analyses)

        # Palettes:
        palette_params = dict(resolution=50)
        fg_c_object = experiment.get_classification_object_by_name("Foreground")
        bg_c_object = experiment.get_classification_object_by_name("Background")
        glob_c_object = experiment.get_classification_object_by_name("Global")

        with open(masset['palette_path'] + ".json", "r") as f:
            palette_assets = json.load(f)

        analyses = []
        c = 0
        for p in palette_assets.keys():
            progress("Palettes:", dbmovie.movie_name + "_" + str(dbmovie.movie_id), 0.1, c / len(palette_assets.keys()))

            ps = p.split("_")
            shot = shot_index[int(ps[0])][int(ps[1])]

            palette_fg = palette_assets[p]["palette_fg"]
            if palette_fg is not None:
                layers = [
                    np.array(palette_fg['layers']),
                    np.array(palette_fg['all_cols']),
                    np.array(palette_fg['ns'])
                ]
                palette_fg = dict(dist=palette_fg['dist'], tree=layers)
                fg_palette = IAnalysisJobAnalysis(
                    name="Color-Palette_" + shot.get_name() + "_FG",
                    results=dict(tree=palette_fg['tree'], dist=palette_fg['dist']),
                    analysis_job_class=ColorPaletteAnalysis,
                    parameters=palette_params,
                    container=shot,
                    target_classification_object=fg_c_object
                )
                analyses.append(fg_palette)

            palette_bg = palette_assets[p]["palette_bg"]
            if palette_bg is not None:
                layers = [
                    np.array(palette_bg['layers']),
                    np.array(palette_bg['all_cols']),
                    np.array(palette_bg['ns'])
                ]
                palette_bg = dict(dist=palette_bg['dist'], tree=layers)
                bg_palette = IAnalysisJobAnalysis(
                    name="Color-Palette_" + shot.get_name() + "_BG",
                    results=dict(tree=palette_bg['tree'], dist=palette_bg['dist']),
                    analysis_job_class=ColorPaletteAnalysis,
                    parameters=palette_params,
                    container=shot,
                    target_classification_object=bg_c_object
                )
                analyses.append(bg_palette)

            palette_glob = palette_assets[p]["palette_glob"]
            if palette_glob is not None:
                layers = [
                    np.array(palette_glob['layers']),
                    np.array(palette_glob['all_cols']),
                    np.array(palette_glob['ns'])
                ]
                palette_glob = dict(dist=palette_glob['dist'], tree=layers)
                glob_palette = IAnalysisJobAnalysis(
                    name="Color-Palette_" + shot.get_name() + "_GLOB",
                    results=dict(tree=palette_glob['tree'], dist=palette_glob['dist']),
                    analysis_job_class=ColorPaletteAnalysis,
                    parameters=palette_params,
                    container=shot,
                    target_classification_object=glob_c_object
                )
                analyses.append(glob_palette)

            c += 1

        vian_project.add_analyses(analyses)
        # endregion

        #region Features
        with open(masset['features_path'] + ".json", "r") as f:
            features_assets = json.load(f)
        c = 0
        feature_params = dict(resolution=50)
        analyses = []
        for p in features_assets.keys():
            progress("Features:", dbmovie.movie_name + "_" + str(dbmovie.movie_id), 0.1, c / len(features_assets.keys()))
            ps = p.split("_")
            shot = shot_index[int(ps[0])][int(ps[1])]

            features_fg = features_assets[p]["features_fg"]
            if features_fg is not None:
                features_fg =  IAnalysisJobAnalysis(
                    name="Color-Features" + shot.get_name() + "_FG",
                    results = dict(color_lab=np.array(features_fg["color_lab"]),
                                   color_bgr = np.array(features_fg["color_bgr"]),
                                   saturation_l=np.array(features_fg["saturation_l"]),
                                   saturation_p = np.array(features_fg["saturation_p"])
                                   ),
                    analysis_job_class=ColorFeatureAnalysis,
                    parameters=feature_params,
                    container=shot,
                    target_classification_object = fg_c_object

                )
                analyses.append(features_fg)

            features_bg = features_assets[p]["features_bg"]
            if features_bg is not None:
                features_bg = IAnalysisJobAnalysis(
                    name="Color-Features" + shot.get_name() + "_BG",
                    results=dict(color_lab=np.array(features_bg["color_lab"]),
                                 color_bgr=np.array(features_bg["color_bgr"]),
                                 saturation_l=np.array(features_bg["saturation_l"]),
                                 saturation_p=np.array(features_bg["saturation_p"])
                                 ),
                    analysis_job_class=ColorFeatureAnalysis,
                    parameters=feature_params,
                    container=shot,
                    target_classification_object = bg_c_object

                )
                analyses.append(features_bg)

            features_glob = features_assets[p]["features_glob"]
            if features_glob is not None:
                features_glob = IAnalysisJobAnalysis(
                    name="Color-Features" + shot.get_name() + "_GLOB",
                    results=dict(color_lab=np.array(features_glob["color_lab"]),
                                 color_bgr=np.array(features_glob["color_bgr"]),
                                 saturation_l=np.array(features_glob["saturation_l"]),
                                 saturation_p=np.array(features_glob["saturation_p"])
                                 ),
                    analysis_job_class=ColorFeatureAnalysis,
                    parameters=feature_params,
                    container=shot,
                    target_classification_object = glob_c_object

                )
                analyses.append(features_glob)

            c+= 1

        vian_project.add_analyses(analyses)
        #endregion

        vian_project.store_project(HeadlessUserSettings(), vian_project.path)
        PROJECT_PATHS.append(vian_project.path + "\t" + fm_id_str)

        return vian_project
        print("\n\n\n")
    except Exception as e:
        print(e)


def check_integrity(entry, project_dir):
    dbmovie = DBMovie().from_database(entry['dbmovie'])
    filmography = entry['filmography']
    assignment = entry['assignment']
    masset = entry['movie_asset']
    fm_id_str = "_".join([masset['fm_id'][0].zfill(3), masset['fm_id'][1], masset['fm_id'][2]])
    # Skip this movie if it is already in the projects
    project_name = fm_id_str + "_" + dbmovie.movie_name + "_" + dbmovie.year

    pdir = project_dir + "/" + project_name
    if not os.path.isdir(project_dir + "/" + project_name):
        return "Not Created"

    ppath  =project_dir + "/" + project_name + "/" + project_name + ".eext"
    project, mw = load_project_headless(ppath)

    if len(project.experiments) == 0:
        return "No Experiment"
    if len(project.analysis) == 0:
        return "No Analyses"

    return "OK"

def remove_project(entry, project_dir):
    dbmovie = DBMovie().from_database(entry['dbmovie'])
    filmography = entry['filmography']
    assignment = entry['assignment']
    masset = entry['movie_asset']
    fm_id_str = "_".join([masset['fm_id'][0].zfill(3), masset['fm_id'][1], masset['fm_id'][2]])
    # Skip this movie if it is already in the projects
    project_name = fm_id_str + "_" + dbmovie.movie_name + "_" + dbmovie.year

    pdir = project_dir + "/" + project_name
    if os.path.isdir(pdir):
        shutil.rmtree(pdir)

if __name__ == '__main__':
    with open("F:\\_result\\database.json") as f:
        data = json.load(f)

    glossary_words = data['glossary_words']
    glossary_ids = data['glossary_ids']
    glossary_categories = data['glossary_categories']
    glossary_omit = data['glossary_omit']

    c = 0
    n = 5
    threads = []
    # for k in data['assets'].keys():
    #     entry = data['assets'][k]
    #     dbmovie = DBMovie().from_database(entry['dbmovie'])
    #     masset = entry['movie_asset']
    #     fm_id_str = "_".join([masset['fm_id'][0].zfill(3), masset['fm_id'][1], masset['fm_id'][2]])
    #
    #     # Skip this movie if it is already in the projects
    #     project_name = fm_id_str + "_" + dbmovie.movie_name + "_" + dbmovie.year
    #     project_name = project_name.replace(":", "").replace("\'", "").replace("?", "")
    #
    #     project_folder = project_dir + "/" + project_name + "/"
    #     print(project_folder)
    #     if os.path.isdir(project_folder):
    #         print("Skipped")
    #         continue
    #
    #     c += 1
    #     if c % n == 0:
    #         for t in threads:
    #             t.join()
    #         threads = []
    #         print(c, "/", len(data['assets'].keys()))
    #     else:
    #         thread = Thread(target=generate_project, args=(data['assets'][k], project_dir, glossary_words,glossary_ids, glossary_categories,glossary_omit))
    #         thread.start()
    #         threads.append(thread)
    #
    # for t in threads:
    #     t.join()

    not_created = 0
    no_experiment = 0
    no_analyses = 0
    todo = []
    c = 0
    for k in data['assets'].keys():
        sys.stdout.write("\r" + str(c) + "/" + str(len(data['assets'].keys())))
        r = check_integrity(data['assets'][k], project_dir)
        print(r)
        if r == "Not Created":
            not_created += 1
            todo.append(k)
        elif r == "No Experiment":
            no_experiment += 1
            todo.append(k)
        elif r == "No Analyses":
            no_analyses += 1
            todo.append(k)
        c += 1

    print("Not Created:", not_created)
    print("No Experiment:", no_experiment)
    print("No Analyses:", no_analyses)

    with open(cache_dir + "/errors_pipeline2project.pickle", "wb") as f:
        pickle.dump(todo, f)

    # REMOVE error projects:
    with open(cache_dir + "/errors_pipeline2project.pickle", "rb") as f:
        todo = pickle.load(f)

    for t in todo:
        remove_project(data['assets'][t], project_dir)