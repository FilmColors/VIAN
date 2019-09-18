from core.data.computation import images_to_movie


import cv2
img = cv2.imread("qt_ui/images/template_mode.png")
images_to_movie([img], "data/template.mp4", time_scale = 24, fps=24, size=(1280, 720), codec="MP4V")