import pyodbc


def get_all_fields_by_name(cursor, name):
    result = []
    for row in cursor.execute("select \"" + name + "\" from " + tables[0]):
        print row
        result.append(row[0])
    return result

# connection_string = "DSN=test_fm;UID=Admin;PWD="
# connection = pyodbc.connect(connection_string)
# cursor = connection.cursor()
#
#
# name = "62_1_1_HenryV_1944_DVD_FMAD_MJ_ReduxMerger_23012017_0136_BF_Clone"
#
#
# tables = []
# for row in cursor.tables():
#     tables.append(row.table_name)
#
# print tables[1]
#
# columns = []
# for column in cursor.columns(table=tables[0]):
#     columns.append(column.column_name)
#
#
#
# # for column in columns:
# #     res = get_all_fields_by_name(cursor, str(column))
# #     print column.ljust(25), res
#
#
# res = get_all_fields_by_name(cursor, "Still_02")
# print "Lightning Notes".ljust(25), res

# for row in cursor.execute("select Location from " + tables[0]):
#     print row[0]
# for field in row:
    #     print field
#
# for row in cursor.columns(table=tables[1]):
#     if "Still" in row.column_name:
#         for field in row:
#             print field
# connection.close()