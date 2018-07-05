"""

This file the frequency of a word per film 
using the exported GlossarDB and MasterDB from Filemaker

This script is included into VIAN. 

@author: Gaudenz Halter
"""

import csv
import pickle
from sys import stdout as console

from core.corpus.shared.entities import *
from core.data.headless import *
from core.data.computation import *
from extensions.plugins.fiwi_tools.vian_dev.fiwi_server_binding.python_binding import MovieAsset, ScreenshotAsset


"""
A Mapping of Filmography Column Names to their respective attribute name in the DBFilmography Class
"""

ERROR_LIST = []

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
def get_movie_asset_by_id(movie_assets:List[MovieAsset], fm_id):
    for m in movie_assets:
        if m.fm_id[0] == fm_id:
            return m
    raise Exception("Movie with id: " + str(fm_id) + " is not in MovieAssets")

def filemaker_timestamp2ms(a):
    a = a.zfill(8)
    a = [a[i:i + 2] for i in range(0, len(a), 2)]
    return ts_to_ms(a[0], a[1], a[2], a[3])


def load_stage(result_dir, stage = 0, movie_asset = None, n = 1000)->List[MovieAsset]:
    """
    Loads the Movie-Assets from a specific Stage of the Pipeline
    :param result_dir:
    :param stage:
    :param movie_asset:
    :return:
    """
    files = glob.glob(result_dir + "stage_" + str(stage).zfill(2) + "*")
    result = []
    c = 0
    for file in files:
        if n < c:
            break
        with open(file, "rb") as f:
            result.append(pickle.load(f))
        c += 1
    return result


def parse_glossary(glossary_path):
    """
    Parse the GlossaryDB CSV and create Unique Keywords from it.
    :param glossary_path: 
    :return: 
    """
    glossary_words, glossary_ids, glossary_categories, glossary_omit = [], [], [], []

    with open(glossary_path, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=';')
        counter = 0
        for r in reader:
            if counter == 0:
                print(r)
                idx_word = r.index("Term_EN")#TODO
                idx_id = r.index("Glossar ID")#TODO
                idx_column = r.index("exp Field")
                idx_omit = r.index("Disregard")
            else:
                word = r[idx_word]
                word = word.strip()
                word = word.replace("’", "")
                word = word.replace("/", "")
                word = word.replace(" ", "_")
                word = word.replace("-", "_")
                glossary_words.append(word)
                glossary_ids.append(r[idx_id])
                glossary_categories.append(r[idx_column])

                if "yes" in r[idx_omit]:
                    glossary_omit.append(True)
                else:
                    glossary_omit.append(False)

                if "mind" in word:
                    print(word)
            counter += 1
    return glossary_words, glossary_ids, glossary_categories, glossary_omit


def parse_corpus(corpus_path, movie_assets):
    """
    Parse the CorpusDB CSV file an create the FilmographyData aswell as the mapping them to DBMovie and MovieAssets
    :param corpus_path: 
    :param movie_assets: 
    :return: 
    """
    filmography_result = []
    movie_results = []
    assignments = []
    movie_assets_res = []

    with open(corpus_path, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=';')
        counter = 0
        for r in reader:
            try:
                if counter == 0:
                    # Movie IDXs
                    idx_filemaker_id = r.index(CorpusDBMapping['filemaker_id'])
                    idx_country = r.index(CorpusDBMapping['country'])
                    idx_title = r.index(CorpusDBMapping['title'])
                    idx_year = r.index(CorpusDBMapping['year'])

                    # Project IDXS
                    idx_corpus_assignment = r.index(CorpusDBMapping['corpus_assignment'])
                    idx_editors = r.index(CorpusDBMapping['editors'])

                    #Filmography IDXs
                    idx_imdb = r.index(CorpusDBMapping['imdb_id'])
                    idx_color_process = r.index(CorpusDBMapping['color_process'])
                    idx_director = r.index(CorpusDBMapping['director'])
                    idx_genre = r.index(CorpusDBMapping['genre'])
                    idx_cinematography = r.index(CorpusDBMapping['cinematography'])
                    idx_color_consultant = r.index(CorpusDBMapping['color_consultant'])
                    idx_production_design = r.index(CorpusDBMapping['production_design'])
                    idx_art_director = r.index(CorpusDBMapping['art_director'])
                    idx_costume_design = r.index(CorpusDBMapping['production_company'])
                    idx_production_company = r.index(CorpusDBMapping['art_director'])

                else:
                    row = r
                    fm_id = row[idx_filemaker_id]
                    masset = get_movie_asset_by_id(movie_assets, fm_id)

                    dbmovie = DBMovie()
                    dbmovie.movie_id = fm_id
                    dbmovie.year = row[idx_year]
                    dbmovie.movie_name = row[idx_title]

                    fg = DBFilmographicalData()
                    fg.imdb_id = row[idx_imdb]
                    fg.color_process = row[idx_color_process]
                    fg.director = row[idx_director]
                    fg.genre = row[idx_genre]
                    fg.cinematography = row[idx_cinematography]
                    fg.color_consultant = row[idx_color_consultant]
                    fg.production_design = row[idx_production_design]
                    fg.art_director = row[idx_art_director]
                    fg.costum_design = row[idx_costume_design]
                    fg.country = row[idx_country]
                    fg.production_company = row[idx_production_company]

                    movie_results.append(dbmovie)
                    filmography_result.append(fg)
                    assignments.append((row[idx_corpus_assignment], row[idx_editors]))
                    movie_assets_res.append(masset)

                counter += 1
            except Exception as e:
                handle_error(fm_id, e)
    return (movie_results, filmography_result, movie_assets_res, assignments)


def handle_error(item, e):
    ERROR_LIST.append((item, e))


def parse_masterdb(database_path, glossary_words, glossary_categories, glossary_ids, glossary_omit):
    all_projects = [] # List of Tuples (<FM_ID>_<ITEM_ID>, [DB_SEGMENT, LIST[KeywordIDs]])
    with open(database_path, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=';')
        counter, idx_id, n_yes = 0, 0, 0
        current_id, current_film, failed_words, failed_n, failed_column = [], [], [], [], []
        for row in reader:
            if counter == 0:
                idx_id = row.index("exp_ItemID")
                idx_start = row.index(MasterDBMapping['start'])
                idx_end = row.index(MasterDBMapping['end'])
                idx_annotation = row.index(MasterDBMapping['annotation'])
                idx_FMID = row.index("FileMaker ID")
                headers = row
            else:
                # Print Progress
                if counter % 100 == 0:
                    console.write("\r" + str(counter))

                # Get the Current FM-ID Item-ID
                new_id = row[idx_id].split("_")

                # If this id is not the same as the last
                # Store movie and create a new one
                if new_id != current_id:
                    all_projects.append(current_film)
                    current_id = new_id
                    current_film = [current_id, []]

                # Create a new Segment
                dbsegment = DBSegment()
                dbsegment.segm_start = row[idx_start]
                dbsegment.segm_end = row[idx_end]
                dbsegment.segm_body = row[idx_annotation]
                dbkeywords = []

                # Iterate over all Columns and parse the keywords
                column_counter = 0
                for c in row:
                    if column_counter in [idx_start, idx_end, idx_annotation, idx_id, idx_FMID]:
                        continue

                    ws = c.split("°")
                    words = []
                    for qw in ws:
                        words.extend(qw.split("\n"))

                    for w in words:
                        success = False
                        word = w.replace("\n", "")
                        word = word.replace("’", "")
                        word = word.replace("\'", "")
                        word = word.replace("/", "")
                        word = word.strip()
                        word = word.replace(" ", "_")
                        word = word.replace("-", "_")

                        if word == "" or word == " ":
                            continue

                        for idx, keyword in enumerate(glossary_words):
                            if keyword.lower() == word.lower() and headers[column_counter].lower() == glossary_categories[idx].lower():
                                if glossary_omit[idx] is False:
                                    dbkeywords.append(glossary_ids[idx])
                                    success = True
                                else:
                                    print(idx, " omitted")
                                break

                        if not success:
                            if word not in failed_words:
                                failed_words.append(word)
                                failed_column.append(headers[column_counter])
                                failed_n.append(1)
                                print("")
                                print("Failed \'" + word + "\'")
                            else:
                                failed_n[failed_words.index(word)] += 1
                    column_counter += 1

                # Finally combine the dbsegment and keywords to a tuple and add them to the current film
                current_film[1].append((dbsegment, dbkeywords))

            counter += 1
            #
            # if counter == 300:
            #     break
    return all_projects


def parse(corpus_path, glossary_path, database_path, outfile, movie_assets, result_path, template_path, cache_dir):
    """
    Parses the given CorpusDB and DatabaseDB file and returns them project sorted project_wise
    :param corpus_path: 
    :param glossary_path: 
    :param database_path: 
    :param outfile: 
    :param movie_list: 
    :return: 
    """

    # MOVIES only have the FM ID
    (movie_results, filmography_result, movie_assets, assignments) = parse_corpus(corpus_path, movie_assets)

    # If the MasterDB has not been cached, parse it
    if not os.path.isfile(cache_dir + "all_projects_cache.pickle"):
        # Parse the Glossary and all Keywords
        glossary_words, glossary_ids, glossary_categories, glossary_omit = parse_glossary(glossary_path)

        # PARSE ALL SEGMENTS, sort them by FM-ID and Item-ID
        # List of Tuples (<FM_ID>_<ITEM_ID>, [DB_SEGMENT, LIST[KeywordIDs]])
        all_projects = parse_masterdb(database_path, glossary_words, glossary_categories, glossary_ids, glossary_omit)
        with open(cache_dir + "all_projects_cache.pickle", "wb") as f:
            pickle.dump(all_projects, f)
    else:
        with open(cache_dir + "all_projects_cache.pickle", "rb") as f:
            all_projects = pickle.load(f)

    # Now, Combine the Projects with their Movie
    result = [] # A List of dicts
    for p in all_projects:
        # The First item is empty
        if len(p) == 0:
            continue
        # Generate the Result
        for idx, m in enumerate(movie_results):
            if (m.movie_id == p[0][0]):
                r = dict(
                    fm_id = p[0],
                    segments = p[1],
                    dbmovie = movie_results[idx],
                    dbfilmography = filmography_result[idx],
                    assignment = assignments[idx],
                    movie_asset = movie_assets[idx]
                )
                result.append(r)
                break

    for r in result:
        with open(result_path +str(r["fm_id"]) + ".pickle", "wb") as f:
            pickle.dump(r, f)


def generate_projects(input_dir, result_dir, replace_path = False):
    files = glob.glob(input_dir + "*")
    glossary_words, glossary_ids2, glossary_categories, glossary_omit = parse_glossary("E:/Programming/Datasets/FilmColors/PIPELINE/_input\\GlossaryDB_WordCount.csv")

    for file in files:
        data = None
        with open(file, "rb") as f:
            data = pickle.load(f)

        if data is not None:
            dbmovie = data['dbmovie']
            masset = data['movie_asset']
            fm_id_str = "_".join([data['fm_id'][0].zfill(3), data['fm_id'][1], data['fm_id'][2]])
            project_name = fm_id_str + "_" + dbmovie.movie_name + "_" +dbmovie.year


            movie_path = masset.movie_path_abs
            if replace_path:
                movie_path = replace_network_path(movie_path)


            project_folder = result_dir + "/" + project_name + "/"
            vian_project = create_project_headless(project_name, project_folder, movie_path, [], [], move_movie="None", template_path=template_path)

            #Create an Experiment and a Main Segmentation
            experiment = vian_project.experiments[0]
            main_segm = vian_project.segmentation[0]

            # Create a Lookup Table for the GlossaryIDs
            exp_keywords = experiment.get_unique_keywords()
            glossary_ids = [k.external_id for k in exp_keywords]

            # Apply the Classification
            Errors = []
            for idx, s in enumerate(data['segments']):
                segment = s[0]
                keywords = s[1]

                # Filemaker exports timestamp without zfill and without ":" thus 00:00:12:34 becomes 1234
                start = filemaker_timestamp2ms(segment.segm_start)
                end = filemaker_timestamp2ms(segment.segm_end)
                new_segm = main_segm.create_segment2(int(start), int(end), body = segment.segm_body, mode=SegmentCreationMode.INTERVAL, inhibit_overlap=False)
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
            for i, scr in enumerate(masset.shot_assets):
                if scr.scr_grp not in scr_groups:
                    grp = vian_project.add_screenshot_group(scr.scr_grp)
                    scr_groups.append(scr.scr_grp)
                else:
                    grp = vian_project.screenshot_groups[scr_groups.index(scr.scr_grp)]
                shot = vian_project.create_screenshot_headless("SCR_" + str(i), scr.frame_pos, fps = fps)
                grp.add_screenshots([shot])
                mask_files[shot.unique_id] = scr.mask_file
                scr_masks.append((shot, scr.mask_file))

            # Analyses
            # Fg/Bg Segmentation
            for shot, mask_file in scr_masks:
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
                vian_project.add_analysis(analysis)


            vian_project.unload_all()
            vian_project.store_project(HeadlessUserSettings(), vian_project.path)
            print(" --- ERRORS --- ")
            for r in sorted(Errors, key=lambda x: x[1]):
                print(r)


def replace_network_path(old):
    return old.replace("\\", "/").replace("//130.60.131.134/", "F:/").replace("/Volumes/", "F:/")

if __name__ == '__main__':
    # corpus_path = "../.."
    # gloss_file = "../../input/datasets/GlossaryDB_WordCount.csv"
    # db_file = "../../input/datasets/MasterDB_WordCount.csv"
    # outfile = "../../results/counting.csv"
    # asset_path = "/Volumes/fiwi_datenbank/PIPELINE_RESULTS/ASSETS/"
    # result_path = "/Volumes/fiwi_datenbank/PIPELINE_RESULTS/COMBINED/"
    # template_path = "../../user/templates/ERC_FilmColors.viant"

    corpus_path = "E:/Programming/Datasets/FilmColors/PIPELINE/_input\\CorpusDB.csv"
    gloss_file = "E:/Programming/Datasets/FilmColors/PIPELINE/_input\\GlossaryDB_WordCount.csv"
    db_file = "E:/Programming/Datasets/FilmColors/PIPELINE/_input\\MasterDB_WordCount.csv"
    outfile = "../../results/counting.csv"
    asset_path = "F:\\fiwi_datenbank\\PIPELINE_RESULTS\\ASSETS\\"
    result_path = "F:/_output/"
    project_dir = "F:/_projects/"
    cache_dir = "F:/_cache/"
    template_path = "E:/Programming/Git/visual-movie-annotator/user/templates/ERC_FilmColors.viant"
    # movie_assets = load_stage(asset_path, 2, n=10)
    # with open("F:\\_cache\\movie_assets_cache.pickle", "wb") as f:
    #     pickle.dump(movie_assets, f)

    print("Loading Movie Assets...")
    with open("F:\\_cache\\movie_assets_cache.pickle", "rb") as f:
        movie_assets = pickle.load(f)

    print("Parsing Corpus...")
    parse(corpus_path, gloss_file, db_file, outfile, movie_assets, result_path, template_path, cache_dir)

    print("Generating Projects....")
    generate_projects(result_path, project_dir, replace_path=True)