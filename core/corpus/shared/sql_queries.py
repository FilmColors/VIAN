#region SQL QUERIES
Q_ALL_PROJECTS_KEYWORD =    ("select * from KEYWORD_MAPPING_SEGMENTS " \
                            "inner join PROJECTS on PROJECTS.id = KEYWORD_MAPPING_SEGMENTS.project_id " \
                            "WHERE KEYWORD_MAPPING_SEGMENTS.keyword_id in ",
                             " and KEYWORD_MAPPING_SEGMENTS.keyword_id not in ")

Q_ALL_PROJECTS_KEYWORD_DISTINCT =    ("select distinct PROJECTS.id from KEYWORD_MAPPING_SEGMENTS " \
                            "inner join PROJECTS on PROJECTS.id = KEYWORD_MAPPING_SEGMENTS.project_id " \
                            "WHERE KEYWORD_MAPPING_SEGMENTS.keyword_id in ",
                            " and KEYWORD_MAPPING_SEGMENTS.keyword_id not in ")

Q_ALL_SEGMENTS_KEYWORD = ("select * from KEYWORD_MAPPING_SEGMENTS " \
                         "inner join SEGMENTS on SEGMENTS.id = KEYWORD_MAPPING_SEGMENTS.segment_id " \
                         "inner join SCREENSHOT_SEGM_MAPPING on SCREENSHOT_SEGM_MAPPING.segment_id = SEGMENTS.id " \
                         "inner join SHOTS on SHOTS.id = SCREENSHOT_SEGM_MAPPING.screenshot_id " \
                         "WHERE KEYWORD_MAPPING_SEGMENTS.keyword_id in ",
                         " and KEYWORD_MAPPING_SEGMENTS.keyword_id not in ")
#endregion