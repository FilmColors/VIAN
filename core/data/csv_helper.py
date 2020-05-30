import os
import csv

import sys

class CSVFile:
    """ A very simple csv file class, which handles a csv file as a dictionary of lists """
    def __init__(self, path = None, with_header = True):
        self._dataset = dict()
        self._header = []
        self._path = path

        self._iter_x = 0

        if self._path is not None and os.path.exists(self._path):
            self._read_data(self._path, with_header)

    def _read_data(self, path, with_header):
        with open(path, "r") as f:
            dialect = csv.Sniffer().sniff(f.read(1024))
            f.seek(0)

            for i, r in enumerate(csv.reader(f, dialect)):
                if i == 0:
                    if with_header:
                        self._header = r
                    else:
                        self._header = [str(q) for q in range(len(r))]
                    for q in self._header:
                        self._dataset[q] = []

                else:
                    for j, q in enumerate(self._header):
                        self._dataset[q].append(r[j])

    def read(self, p = None, with_header=True):
        self._header = []
        self._dataset = dict()

        if p is not None:
            self._path = p
        self._read_data(self._path, with_header)

        return self


    def save(self, p):
        new_line = "\n"
        try:
            with open(p,"w", newline=new_line, encoding="utf-8") as f:
                w = csv.writer(f)
                rows = [self._header]
                for i in range(len(self._dataset[self._header[0]])):
                    r = []
                    for k in self._header:
                        r.append(self._dataset[k][i])
                    rows.append(r)
                w.writerows(rows)
        except Exception as e:
            print(e)

    def set_header(self, header):
        self._header = header
        for q in self._header:
            self._dataset[q] = []

    def append(self, r):
        if set(r.keys()) != set(self._header):
            raise ValueError("Dict items not matching dataset")

        for k, v in r.items():
            self._dataset[k].append(v)

    def header(self):
        return self._header

    def extend(self, r):
        for q in r:
            self.append(q)

    def __iter__(self):
        self._iter_x = 0
        return self

    def __next__(self):
        if self._iter_x < len(self):
            d = dict()
            for i, v in enumerate(self._header):
                d[v] = self._dataset[v][self._iter_x]
            self._iter_x += 1
            return d
        else:
            raise StopIteration()

    def __len__(self):
        if len(self._header) > 0:
            return len(self._dataset[self._header[0]])
        else:
            return 0

    def __str__(self):
        r =  "HEADER: " + str(self._header) + "\n"
        for j, i in enumerate(self):
            r += "Row: " + str(j) +": " +str(i) + "\n"
            if j == 5:
                break
        return r



