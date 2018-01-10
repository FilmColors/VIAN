import sqlite3
import pickledb
import simplejson as json
import numpy as np
import pandas as pd


class daTestObj():
    def __init__(self, id, name, value):
        self.name = name
        self.value = value
        self.unique_id = id

def store_arbitrary(unique_id, object):
    conn = sqlite3.connect('example.db')

    c = conn.cursor()

    keys, values = [], []

    keys_str = ""
    values_str = ""

    table_name = "ID_" + str(unique_id)
    for i, (k, v) in enumerate(vars(object).items()):
        keys.append(k)
        values.append(v)
        keys_str += "'" + str(k) +"'"
        values_str += "?"
        if i < len(vars(object).items()) - 1:
            keys_str += ", "
            values_str += ", "

    keys_str = " (" + keys_str +")"
    print("CREATE TABLE " + table_name + keys_str)

    c.execute("CREATE TABLE " + table_name + keys_str)

    # Insert a row of data
    c.execute("INSERT INTO " + table_name +" VALUES ("+ values_str + ")", values)

    # Save (commit) the changes
    conn.commit()

    # We can also close the connection if we are done with it.
    # Just be sure any changes have been committed or they will be lost.
    conn.close()

def load_arbitrary(unique_id):
    conn = sqlite3.connect('example.db')
    table_name = "ID_" + str(unique_id)
    c = conn.cursor()
    t = ("Peter", )
    c.execute("SELECT * FROM "+table_name+" WHERE name=?", t)

    print(c.fetchone())

def store_container(container):
    pass





if __name__ == '__main__':
    arr = np.zeros(shape=(100000, 4096), dtype=np.float16)
    print(arr.nbytes / 1000000)

    np.save("Numpy_test.npy", arr, allow_pickle=False)


