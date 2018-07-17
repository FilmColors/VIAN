from core.corpus.shared.entities import *
from core.corpus.shared.corpusdb import *
from core.data.headless import *
from sys import stdout as console
from extensions.plugins.fiwi_tools.filemaker2projects import CorpusDBMapping, MasterDBMapping

def handle_error(fm_id, e):
    pass


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


def step_1_filemaker():
    """
    Generates VIAN Projects from Filemaker Data
    :return: 
    """
    pass


def step_2_screenshots():
    """
    Attaches Screenshots to VIAN Projects created in step 1
    :return: 
    """
    pass


def step_3_masks():
    """
    Attaches Masks to Screenshots Created in step 2
    :return: 
    """
    pass


def step_4_palettes():
    """
    Attaches Palettes to mask analyses created in step 2
    :return: 
    """


def step_5_color_features():
    """
    Attaches Color Features to masks applied in step 2
    :return: 
    """
    pass