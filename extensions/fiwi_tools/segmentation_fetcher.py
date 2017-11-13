"""
Gaudenz Halter
University of Zurich

#### Loading an exported Segmentation from the FIWI-Database
"""
import os
import glob


class SegmentationFetcher():

    def __init__(self, root_dir = "\\\\130.60.131.134\\fiwi_datenbank\\SCR\\"):
        self.root_dir = root_dir

    def get_segmentation_by_id(self, filemaker_id, path = None):
        """
        Loads the segmentation exported by ELAN.
        :param filemaker_id: filemaker_id as list of integers i.e [931,1,1]
        :return: a list of segments where: [SegmentID, Segment-Start, Segment-End], start and end in [ms]
        """

        if path is None:
            path  =  self.root_dir + "SEGM/" + str(filemaker_id[0]) + "_" + str(filemaker_id[1]) + "_" + str(filemaker_id[2]) + "_SEGM.txt"

        if not os.path.isfile(path):
            raise IOError("File not found: ", path)

        try:
            segments = []
            with open(path, mode="rb") as f:
                for l in f:
                    segm_source = l.replace("\n", "")
                    segm_source = segm_source.split("\t")
                    if segm_source[0] == "Sequence_No":
                        continue

                    segments.append([int(segm_source[0]), int(segm_source[1]), int(segm_source[2])])

            return segments
        except IOError as e:
            print e.message
            return None


class ScreenshotFetcher():
    def __init__(self, root_path):
        self.root_path = root_path.replace("\\", "/")

    def get_all_shots_of_movie(self, filemaker_id):
        """
        
        :param filemaker_id: filemaker_id as list of integers i.e [931,1,1]
        :return: a list of shots where: [segm_id, segm_shot_id, path]
        """
        movie_dir = "SCR/" + str(filemaker_id[0]) + "_" + str(filemaker_id[1]) + "_" + str(filemaker_id[2])
        shot_files = glob.glob(self.root_path + "/" + movie_dir+"/*")
        result = []

        for s in shot_files:
            s = s.replace("\\", "/")
            path = s
            s = s.replace(self.root_path + "/" + movie_dir+ "/", "").split("_")
            segm_id = s[0]
            segm_shot_id = s[1]
            result.append([segm_id, segm_shot_id, path])

        return result

if __name__ == '__main__':

    fm_id = [931,1,1]

    fetcher = SegmentationFetcher("\\\\130.60.131.134\\fiwi_datenbank\\")
    result = fetcher.get_segmentation_by_id(fm_id)
    print result

    fetcher = ScreenshotFetcher("\\\\130.60.131.134\\fiwi_datenbank\\")
    result = fetcher.get_all_shots_of_movie(fm_id)
    print result


