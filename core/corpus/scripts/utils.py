from core.corpus.shared.entities import *

CorpusContributorShortCuts = dict(
    OS = ("Olivia Stutz", 2),
    MB = ("Michelle Beutler", 3),
    JD = ("Josephine Diecke", 6),
    BL = ("Bregt Lameris", 7),
    ND = ("Noemi Daugaard", 5),
    JK = ("Joelle Kost", 4),
    BF = ("Barbara Fluckiger", 8)

)

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

def parse_field_with_split(row, idx):
    t = row[idx].split("°")
    t = [a.strip() for a in t]
    if "" in t:
        t.remove("")
    if " " in t:
        t.remove(" ")
    return t

def parse_assignment(entry):
    t = entry.replace("\n", ",").split(",")
    result = []
    for r in t:
        if r in CorpusContributorShortCuts:
            result.append(CorpusContributorShortCuts[r])
    return result

def parse_corpus(corpus_path):
    """
    Parse the CorpusDB CSV file an create the FilmographyData aswell as the mapping them to DBMovie and MovieAssets
    :param corpus_path: 
    :param movie_assets: 
    :return: 
    """
    filmography_result = []
    movie_results = []
    assignments = []

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

                    dbmovie = DBMovie()
                    dbmovie.movie_id = fm_id
                    dbmovie.year = row[idx_year]
                    dbmovie.movie_name = row[idx_title]

                    fg = DBFilmographicalData()
                    # fg.imdb_id = row[idx_imdb]
                    # fg.color_process = row[idx_color_process].split("°").replace(" ", "")
                    # fg.director = row[idx_director].split("°").replace(" ", "")
                    # fg.genre = row[idx_genre].split("°").replace(" ", "")
                    # fg.cinematography = row[idx_cinematography].split("°").replace(" ", "")
                    # fg.color_consultant = row[idx_color_consultant].split("°").replace(" ", "")
                    # fg.production_design = row[idx_production_design].split("°").replace(" ", "")
                    # fg.art_director = row[idx_art_director].split("°").replace(" ", "")
                    # fg.costum_design = row[idx_costume_design].split("°").replace(" ", "")
                    # fg.country = row[idx_country].split("°").replace(" ", "")
                    # fg.production_company = row[idx_production_company].split("°").replace(" ", "")
                    fg.imdb_id = parse_field_with_split(row, idx_imdb)
                    fg.color_process = parse_field_with_split(row, idx_color_process)
                    fg.director = parse_field_with_split(row, idx_director)
                    fg.genre = parse_field_with_split(row, idx_genre)
                    fg.cinematography = parse_field_with_split(row, idx_cinematography)
                    fg.color_consultant = parse_field_with_split(row, idx_color_consultant)
                    fg.production_design = parse_field_with_split(row, idx_production_design)
                    fg.art_director = parse_field_with_split(row, idx_art_director)
                    fg.costum_design = parse_field_with_split(row, idx_costume_design)
                    fg.country = parse_field_with_split(row, idx_country)
                    fg.production_company = parse_field_with_split(row, idx_production_company)

                    movie_results.append(dbmovie)
                    filmography_result.append(fg)
                    assignments.append((fm_id, parse_assignment(row[idx_corpus_assignment]), parse_assignment(row[idx_editors])))

                counter += 1
            except Exception as e:
                print(e)
    return (movie_results, filmography_result, assignments)


