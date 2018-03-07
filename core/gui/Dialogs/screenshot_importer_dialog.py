import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog

from core.data.enums import ScreenshotNamingConventionOptions, ImageType, get_enum
from core.gui.ewidgetbase import EDialogWidget
from core.data.importers import ScreenshotImporter
from core.data.computation import ts_to_ms, ms_to_frames
from functools import partial
from core.data.containers import VIANProject


class DialogScreenshotImport(EDialogWidget):
    def __init__(self, parent):
        super(DialogScreenshotImport, self).__init__(parent, parent, "_docs/build/html/step_by_step/screenshots/export_screenshots.html")
        path = os.path.abspath("qt_ui/DialogImportScreenshots.ui")
        uic.loadUi(path, self)
        self.files = []

        self.lineEdit_Delimiter.setText("_")
        self.checkBox_UseLocation.stateChanged.connect(self.set_timestamp_enabled)
        self.btn_Import.clicked.connect(partial(self.on_import, self.main_window.project, self.main_window.project.movie_descriptor.fps))
        self.btn_Cancel.clicked.connect(self.close)
        self.btn_Browse.clicked.connect(self.on_browse)
        self.btn_Help.clicked.connect(self.on_help)


    def on_browse(self):
        files = QFileDialog.getOpenFileNames()[0]
        self.files = files
        self.lineEdit_Files.setText(str(files))


    def on_import(self, project:VIANProject, fps):
        mode = 0
        files = []
        scr_paths = []
        timestamps = []
        segment_ranges = []
        segment_ids = []

        # If the Time Location is given, we just want to parse the screenshots locations and place them in the Project
        if self.checkBox_UseLocation.isChecked() and self.lineEdit_Delimiter.text() != "":
            scr_ranges = []
            idx_h = self.sB_PositionTimeH.value() - 1
            idx_m = self.sB_PositionTimeM.value() - 1
            idx_s = self.sB_PositionTimeS.value() - 1
            idx_ms = self.sB_PositionTimeMS.value() - 1
            idx_segment = self.sB_PositionSegment.value() - 1

            has_time_location = (idx_h >= 0 or idx_m >= 0 or idx_s >= 0 or idx_ms >= 0)

            if has_time_location:
                files = self.files
                mode = 0
                timestamps = []
                for f in self.files:
                    dir, file = os.path.split(f)
                    file = file.split(".")[0]
                    file = file.split(self.lineEdit_Delimiter.text())
                    try:
                        t_hour = 0
                        t_min = 0
                        t_sec = 0
                        t_milli = 0

                        if idx_h > 0:
                            t_hour = int(file[idx_h])
                        if t_min > 0:
                            t_min = int(file[idx_m])
                        if idx_s > 0:
                            t_sec = int(file[idx_s])
                        if idx_ms > 0:
                            t_milli = int(file[idx_ms])

                        time_ms = ts_to_ms(t_hour, t_min, t_sec, t_milli)
                        timestamps.append(time_ms)
                        scr_paths.append(f)

                    except Exception as e:
                        raise e
                        print("Error in Screenshot Import", str(e))
                        continue

            elif idx_segment >= 0:
                mode = 1
                segment_ids = []
                for f in self.files:
                    dir, file = os.path.split(f)
                    file = file.split(".")[0]
                    file = file.split(self.lineEdit_Delimiter.text())
                    try:
                        segment_id = int(file[idx_segment])
                        scr_paths.append(f)
                        segment_ids.append(segment_id - 1)
                    except Exception as e:
                        print("Error in Screenshot Import", str(e))
                        continue
                for s in project.get_main_segmentation().segments:
                    segment_ranges.append([ms_to_frames(s.get_start(), fps), ms_to_frames(s.get_end(), fps)])

            else:
                mode = 2
                scr_paths = self.files

        args = dict(
            mode=mode,
            movie_path = project.movie_descriptor.movie_path,
            scr_paths = scr_paths,
            segment_ids = segment_ids,
            segment_ranges = segment_ranges,
            timestamps = timestamps
        )

        importer = ScreenshotImporter(args)
        self.main_window.run_job_concurrent(importer)



    def set_timestamp_enabled(self, state):
        self.lineEdit_Delimiter.setEnabled(state)
        self.sB_PositionSegment.setEnabled(state)
        self.sB_PositionTimeH.setEnabled(state)
        self.sB_PositionTimeM.setEnabled(state)
        self.sB_PositionTimeS.setEnabled(state)
        self.sB_PositionTimeMS.setEnabled(state)

