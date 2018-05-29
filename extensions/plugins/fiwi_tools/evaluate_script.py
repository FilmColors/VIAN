"""

This file the frequency of a word per film 
using the exported GlossarDB and MasterDB from Filemaker

This script is included into VIAN. 

@author: Gaudenz Halter
"""

import numpy as np
import csv
import os
from sys import stdout as console

from core.data.plugin import GAPlugin, GAPLUGIN_WNDTYPE_MAINWINDOW
from core.gui.ewidgetbase import EDialogWidget
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from core.concurrent.worker import SimpleWorker

from PyQt5 import uic

class FiwiGlossary2Template(GAPlugin):
    def __init__(self, main_window):
        super(FiwiGlossary2Template, self).__init__(main_window)
        self.plugin_name = "GlossaryDB Evaluation"
        self.windowtype = GAPLUGIN_WNDTYPE_MAINWINDOW

    def get_window(self, parent):
        wnd = FiwiGlossary2TemplateDialog(self.main_window)
        wnd.show()

class FiwiGlossary2TemplateDialog(EDialogWidget):
    def __init__(self, main_window):
        super(FiwiGlossary2TemplateDialog, self).__init__(main_window, main_window)
        path = os.path.abspath("extensions/plugins/fiwi_tools/gui/fiwi_glossary_evaluation.ui")
        uic.loadUi(path, self)
        self.db_path = ""
        self.gl_path = ""
        self.out_path = ""


    def on_ok(self):
        if os.path.isfile(self.line_db.text()) and os.path.isfile(self.line_gl.text()) and os.path.isfile(self.line_out.text()):
            self.main_window.run_job_concurrent(SimpleWorker(parse, self.main_window.worker_finished,
                                                             self.main_window.worker_progress,
                                                             args = [self.line_db.text(),
                                                                     self.line_gl.text(),
                                                                     self.line_out.text()
                                                                     ]))

    def on_browse_db(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.db_path = file
                self.line_db.setText(file)
        except:
            pass

    def on_browse_gl(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.gl_path = file
                self.line_gl.setText(file)
        except:
            pass

    def on_browse_out(self):
        try:
            file = QFileDialog.getOpenFileName()[0]
            if os.path.isfile(file):
                self.out_path = file
                self.line_out.setText(file)
        except:
            pass

def parse(args):

    glossary_path = args[1]
    database_path = args[0]
    outfile = args[2]

    # Parse the Glossary
    glossary_words = []
    glossary_ids = []
    glossary_categories = []
    glossary_omit = []


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
    result = []

    all_segments = []
    with open(database_path, 'r') as input_file:
        reader = csv.reader(input_file, delimiter=';')
        counter = 0

        idx_id = 0
        current_id = []
        current_film = []
        failed_words = []
        failed_n = []
        failed_column = []

        n_yes = 0
        for row in reader:
            if counter == 0:
                idx_id = row.index("FileMaker ID") #TODO
                headers = row
            else:
                if counter % 100 == 0:
                    console.write("\r" + str(counter))
                new_id = row[idx_id]
                if new_id != current_id:
                    result.append(current_film)
                    current_film = [0] * (len(glossary_words) + 1)
                    current_film[len(current_film) - 1] = new_id
                    current_id = new_id

                row_counter = 0
                for c in row:

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