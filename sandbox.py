from bokeh.io import output_file, show
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.layouts import layout
from bokeh.sampledata.commits import data
from bokeh.transform import jitter

from core.container.project import *
import cv2


t = cv2.imread("data/test_image.png")
t = cv2.cvtColor(t, cv2.COLOR_BGR2RGBA)
img = np.zeros((t.shape[0],t.shape[1]), dtype=np.uint32)
view = img.view(dtype=np.uint8).reshape(t.shape[0],t.shape[1], 4)
view[:] = t[:]
print(img.shape, img.dtype, np.amin(img), np.amax(img))

p = figure(plot_width=800)
p.image_rgba(image=[img], x=0, y=0, dw=10, dh=10)

show(p)


import numpy as np
from bokeh.plotting import figure, output_file, show

N = 20
img = np.empty((N,N), dtype=np.uint32)
view = img.view(dtype=np.uint8).reshape((N, N, 4))
for i in range(N):
    for j in range(N):
        view[i, j, 0] = int(i/N*255)
        view[i, j, 1] = 158
        view[i, j, 2] = int(j/N*255)
        view[i, j, 3] = 255

p = figure(tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")])
p.x_range.range_padding = p.y_range.range_padding = 0

print(img.shape, img.dtype, np.amin(img), np.amax(img))
# must give a vector of images
p.image_rgba(image=[img], x=0, y=0, dw=10, dh=10)

output_file("image_rgba.html", title="image_rgba.py example")

show(p)  # open a browser