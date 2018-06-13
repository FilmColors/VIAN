"""

This file the frequency of a word per film 
using the exported GlossarDB and MasterDB from Filemaker

This script is included into VIAN. 

@author: Gaudenz Halter
"""

import numpy as np
import csv
from typing import Tuple
from sys import stdout as console
from core.corpus.shared.entities import *

"""
A Mapping of Filmography Column Names to their respective attribute name in the DBFilmography Class
"""
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
def get_movie_asset_by_id(movie_assets, fm_id):
    return MovieAsset()

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


def parse_corpus(corpus_path, movie_assets) -> (List[DBFilmographicalData], List[DBMovie], List[MovieAsset] ,Tuple(List, List)):
    """
    Parse the CorpusDB CSV file an create the FilmographyData aswell as the mapping them to DBMovie and MovieAssets
    :param corpus_path: 
    :param movie_assets: 
    :return: 
    """
    filmography_result = []
    movie_results = []
    assignments = []
    movie_assets = []

    with open(corpus_path, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=';')
        counter = 0
        for r in reader:
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
                dbmovie.movie_id_db = fm_id
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
                movie_assets.append(masset)

            counter += 1
    return (movie_results, filmography_result, movie_assets, assignments)


def parse(corpus_path, glossary_path, database_path, outfile, movie_assets):
    """
    Parses the given CorpusDB and DatabaseDB file and returns them project sorted project_wise
    :param corpus_path: 
    :param glossary_path: 
    :param database_path: 
    :param outfile: 
    :param movie_list: 
    :return: 
    """
    result_movies = []
    result_projects = []
    glossary_words, glossary_ids, glossary_categories, glossary_omit = parse_glossary(glossary_path)
    (movie_results, filmography_result, movie_assets, assignments) = parse_corpus(corpus_path, movie_assets)



    # PARSE ALL SEGMENTS, sort them by FM-ID and Item ID (i.e. 000_1_1)
    all_projects = []
    # List of Tuples (FM_ID, [DB_SEGMENT, LIST[KeywordIDs]])
    project_segments = []
    with open(database_path, 'r') as input_file:

        reader = csv.reader(input_file, delimiter=';')
        counter, idx_id, n_yes = 0, 0, 0
        current_id, current_film, failed_words, failed_n, failed_column = [], [], [], [], []
        for row in reader:
            if counter == 0:
                idx_id = row.index("FileMaker ID")
                idx_start = row.index(MasterDBMapping['start'])
                idx_end = row.index(MasterDBMapping['end'])
                idx_annotation = row.index(MasterDBMapping['annotation'])
                headers = row
            else:
                if counter % 100 == 0:
                    console.write("\r" + str(counter))
                new_id = row[idx_id]

                # Store movie and create a new one
                if new_id != current_id:
                    all_projects.append(current_film)
                    current_id = new_id
                    current_film = []

                row_counter = 0
                for c in row:
                    dbsegment = DBSegment()
                    dbsegment.segm_start = row[idx_start]
                    dbsegment.segm_end = row[idx_end]
                    dbsegment.segm_body = row[idx_annotation]

                    if row_counter == len(row) - 1:
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

                        for i, keyword in enumerate(glossary_words):
                            if keyword.lower() == word.lower() and headers[row_counter].lower() == glossary_categories[i].lower():
                                idx = i
                                current_film[idx] += 1
                                success = True
                                break

                        if not success:
                            if word not in failed_words:
                                failed_words.append(word)
                                failed_column.append(headers[row_counter])
                                failed_n.append(1)
                                print("")
                                print("Failed \'" + word + "\'")
                            else:
                                failed_n[failed_words.index(word)] += 1
                    row_counter += 1

            counter += 1
            #
            # if counter == 300:
            #     break



    result.append(current_film)
    with open(outfile, "w", newline='') as out_file:
        writer = csv.writer(out_file, delimiter=";")
        writer.writerow(["FM-ID", "Glossary-ID", "WordName", "EXP Field", "Frequency"])
        for r in result:
            for i, entry in enumerate(r):
                if i == len(r) - 1:
                    break
                if glossary_ids[i] == "1288" and glossary_omit[i] is False:
                    writer.writerow([r[len(r) - 1], glossary_ids[i], glossary_words[i], glossary_categories[i], entry])


    with open(outfile.replace("counting", "counting_failed"), "w", newline='') as out_file:
        writer = csv.writer(out_file, delimiter=";")
        for i, r in enumerate(failed_words):
            writer.writerow([r, failed_n[i], failed_column[i]])

if __name__ == '__main__':
    gloss_file = "../../input/datasets/GlossaryDB_WordCount.csv"
    db_file = "../../input/datasets/MasterDB_WordCount.csv"
    outfile = "../../results/counting.csv"
    parse(gloss_file, db_file, outfile=outfile)