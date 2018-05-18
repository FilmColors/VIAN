import dataset as ds

db = ds.connect("mysql://zauberkl_ghalte:ghalte_991@zauberkl.mysql.db.hostpoint.ch:3306/zauberkl_VIANCorpusTest")
print(db.tables)