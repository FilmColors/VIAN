from core.corpus.shared.entities import FilmographyQuery
#region SQL QUERIES
Q_ALL_PROJECTS_KEYWORD =    ("select * from KEYWORD_MAPPING_SEGMENTS " \
                            "inner join PROJECTS on PROJECTS.id = KEYWORD_MAPPING_SEGMENTS.project_id " \
                            "WHERE KEYWORD_MAPPING_SEGMENTS.keyword_id in ",
                             " and KEYWORD_MAPPING_SEGMENTS.keyword_id not in ")

Q_ALL_PROJECTS_KEYWORD_DISTINCT =    ("select distinct PROJECTS.id from KEYWORD_MAPPING_SEGMENTS " \
                            "inner join PROJECTS on PROJECTS.id = KEYWORD_MAPPING_SEGMENTS.project_id " \
                            "WHERE KEYWORD_MAPPING_SEGMENTS.keyword_id in ",
                            " and KEYWORD_MAPPING_SEGMENTS.keyword_id not in ")

Q_ALL_SEGMENTS_KEYWORD = ("select *, SHOTS.id as \"screenshot_id\", SEGMENTS.id as \"segment_id\" from KEYWORD_MAPPING_SEGMENTS " \
                         "inner join SEGMENTS on SEGMENTS.id = KEYWORD_MAPPING_SEGMENTS.segment_id " \
                         "inner join SCREENSHOT_SEGM_MAPPING on SCREENSHOT_SEGM_MAPPING.segment_id = SEGMENTS.id " \
                         "inner join SHOTS on SHOTS.id = SCREENSHOT_SEGM_MAPPING.screenshot_id " \
                         "WHERE KEYWORD_MAPPING_SEGMENTS.keyword_id in ",
                         " and KEYWORD_MAPPING_SEGMENTS.keyword_id not in ")

Q_FEATURES_OF_SHOTS = ("select *, SHOTS.id as \"shot_id\", ANALYSES.id as \"analysis_id\" from ANALYSES "
                       "inner join SHOTS on SHOTS.id = ANALYSES.target_container_id " 
                       "where ANALYSES.analysis_name = \"ColorFeatureAnalysis\" and SHOTS.id in ")

Q_SCREENSHOT_MAPPING_OF_PROJECT = "select * from SHOTS " \
                                  "inner join SCREENSHOT_SEGM_MAPPING on SCREENSHOT_SEGM_MAPPING.screenshot_id = SHOTS.id " \
                                  "inner join SEGMENTS on SEGMENTS.id = SCREENSHOT_SEGM_MAPPING.segment_id " \
                                  "where SHOTS.project_id = "

Q_FILMOGRAPHY = ("select * from FILMOGRAPHY "
                 "inner join PROJECTS on PROJECTS.id = FILMOGRAPHY.id " 
                 "inner join MOVIES on MOVIES.id = FILMOGRAPHY.id ",
                 "where FILMOGRAPHY.", " in ",
                 " and FILMOGRAPHY.", " in ")

Q_SCREENSHOT_PALETTE = "select * from SHOTS " \
                       "inner join ANALYSES on ANALYSES.target_container_id = SHOTS.id " \
                       "where ANALYSES.target_container_type = \"Screenshot\" " \
                       "and ANALYSES.analysis_name = \"ColorPaletteAnalysis\" " \
                       "and SHOTS.id = "

Q_SCREENSHOT_PALETTE_ALL_COBJ = "select MAIN_SHOTS.*, ANALYSES.* from SHOTS as MAIN_SHOTS " \
                                "inner join SHOTS on SHOTS.time_ms = MAIN_SHOTS.time_ms and SHOTS.project_id = MAIN_SHOTS.project_id " \
                                "inner join ANALYSES on ANALYSES.target_container_id = MAIN_SHOTS.id " \
                                "where ANALYSES.target_container_type = \"Screenshot\" " \
                                "and ANALYSES.analysis_name = \"ColorPaletteAnalysis\" " \
                                "and SHOTS.id = "

def create_filmography_query(query:FilmographyQuery):
    q = Q_FILMOGRAPHY[0]
    c = 0
    isQuery = False
    if query is None:
        return None

    for key, val in query.__dict__.items():
        if val is not None and "year" not in key:
            if not isinstance(val, list):
                val = [val]
            if c == 0:
                q += Q_FILMOGRAPHY[1] + key + Q_FILMOGRAPHY[2] + '(' + ','.join(map(str, val)) + ')'
                c += 1
            else:
                q += Q_FILMOGRAPHY[3] + key + Q_FILMOGRAPHY[2] + '(' + ','.join(map(str, val)) + ')'
            isQuery = True

    if query.year_start is not None:
        q += " and MOVIES.year >= " + str(query.year_start)
        isQuery = True
    if query.year_end is not None:
        q += " and MOVIES.year <= " + str(query.year_end)
        isQuery = True

    if isQuery:
        print("Query: ", q)
        return q
    else:
        return None

if __name__ == '__main__':
    print(create_filmography_query(FilmographyQuery(1234, color_process="Color Process 2", color_consultant="Henry Ford", year_end=1950, year_start=1930)))
#endregion