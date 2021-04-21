import cv2
import pymediainfo



from pprint import pprint
from pymediainfo import MediaInfo

movie_path = "C:/Users//gaude\Downloads/Solaris_cut.mov"


def get_frame_dimensions(movie_path):
    try:
        media_info = MediaInfo.parse(movie_path)

        height = None
        display_aspect = None

        for t in media_info.to_data()['tracks']:
            if t['track_type'] == "Video":
                height = int(t['sampled_height'])
                display_aspect = float(t['display_aspect_ratio'])
                break

        return (int(height * display_aspect), height)
    except Exception as e:
        cap = cv2.VideoCapture(movie_path)
        cap.read()

        return (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


cap = cv2.VideoCapture(movie_path)
final_width, height = get_frame_dimensions(movie_path)

while True:
    ret, frame = cap.read()
    frame = cv2.resize(frame, (final_width, height), interpolation=cv2.INTER_CUBIC)
    cv2.imshow("out", frame)
    cv2.waitKey(5)