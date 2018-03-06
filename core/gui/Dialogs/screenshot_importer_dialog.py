import os

from PyQt5 import uic
from PyQt5.QtWidgets import QFileDialog

from core.data.enums import ScreenshotNamingConventionOptions, ImageType, get_enum
from core.gui.ewidgetbase import EDialogWidget
from core.data.importers import ScreenshotImporter
from core.data.computation import ts_to_ms, ms_to_frames

from core.data.containers import VIANProject


class DialogScreenshotImport(EDialogWidget):
    def __init__(self, parent, manager):
        super(DialogScreenshotImport, self).__init__(parent, parent, "_docs/build/html/step_by_step/screenshots/export_screenshots.html")
        path = os.path.abspath("qt_ui/DialogImportScreenshots.ui")
        uic.loadUi(path, self)
        self.files = []


    def on_browse(self):
        files = QFileDialog.getOpenFileNames()[0]
        self.files = files


    def on_import(self, project:VIANProject, fps):
        # If the Time Location is given, we just want to parse the screenshots locations and place them in the Project
        if self.checkBox_UseLocation.isChecked():
            scr_ranges = []
            idx_h = self.sB_PositionTimeH.value()
            idx_m = self.sB_PositionTimeM.value()
            idx_s = self.sB_PositionTimeS.value()
            idx_ms = self.sB_PositionTimeMS.value()
            idx_segment = self.sB_PositionSegment.value()

            has_time_location = (idx_h != 0 or idx_m != 0 or idx_s != 0 or idx_ms != 0)

            if has_time_location:
                timestamps = []
                files = []
                for f in self.files:
                    dir, file = os.path.split(f)
                    file = file.split(".").pop()
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
                        files.append(f)

                    except Exception as e:
                        print("Error in Screenshot Import", str(e))
                        continue

                args = [
                    0,
                    timestamps,
                    files
                ]

            elif idx_segment > 0:
                scr_ranges = []
                files = []
                for f in self.files:
                    dir, file = os.path.split(f)
                    file = file.split(".").pop()
                    file = file.split(self.lineEdit_Delimiter.text())
                    try:
                        segment_id = int(file[idx_segment])
                        segm = project.get_main_segmentation()[segment_id - 1]
                        scr_ranges.append([ms_to_frames(segm.get_start(), fps), ms_to_frames(segm.get_end(), fps)])
                        files.append(f)
                    except Exception as e:
                        print("Error in Screenshot Import", str(e))
                        continue

                args = [
                    1,
                    scr_ranges,
                    files
                ]
            else:
                args = [
                    self.files
                ]

        importer = ScreenshotImporter(args)
        self.main_window.run_job_concurrent(importer)



