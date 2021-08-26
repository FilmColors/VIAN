import cv2
import sys
import numpy as np
from core.data.computation import frame2ms, ms_to_frames


from core.data.interfaces import IConcurrentJob


class BasicTrackingJob(IConcurrentJob):
    def run_concurrent(self, args, sign_progress):
        annotation_id = args[0]
        bbox = tuple(args[1])
        movie_path = args[2]
        fps = args[5]
        start_frame = ms_to_frames(args[3], fps)
        end_frame = ms_to_frames(args[4], fps)
        method = args[6]
        resolution = args[7]

        keys = []

        # TRACKING
        if method == 'BOOSTING':
            tracker = cv2.TrackerBoosting_create()
        elif method == 'MIL':
            tracker = cv2.TrackerMIL_create()
        elif method == 'KCF':
            tracker = cv2.TrackerKCF_create()
        elif method == 'TLD':
            tracker = cv2.TrackerTLD_create()
        elif method == 'MEDIANFLOW':
            tracker = cv2.TrackerMedianFlow_create()
        elif method == 'GOTURN':
            tracker = cv2.TrackerGOTURN_create()
        else:
            raise Exception("Tracking Method not identifiable. " + str(method))

        # Read video
        capture = cv2.VideoCapture(movie_path)

        # Exit if video not opened.
        if not capture.isOpened():
            raise RuntimeError("Tracking: Could not open video.")

        # Read first frame.
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError("Tracking: Could not read Frame.")



        # Initialize tracker with first frame and bounding box
        ok = tracker.init(frame, bbox)

        for i in range(start_frame, end_frame, 1):
            sign_progress(round(float(i - start_frame) / (end_frame - start_frame),2))
            # Read a new frame
            ok, frame = capture.read()
            if not ok:
                break

            # Update tracker
            ok, bbox = tracker.update(frame)

            # Draw bounding box
            if ok:
                # Tracking success
                if i % resolution == 0:
                    time = frame2ms(i, fps)
                    pos = [bbox[0], bbox[1]]
                    keys.append([time, pos])

                    p1 = (int(bbox[0]), int(bbox[1]))
                    p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                    cv2.rectangle(frame, p1, p2, (255, 0, 0), 2, 1)
                    # cv2.imshow("Returned", frame)
                    # cv2.waitKey(30)


        return [annotation_id, keys]

    def modify_project(self, project, result, sign_progress=None, main_window = None):
        annotation_id = result[0]
        keys = result[1]

        annotation = project.get_by_id(annotation_id)

        if annotation is not None:
            for k in keys:
                annotation.add_key(k[0], k[1])

