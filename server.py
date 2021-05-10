from core.container.corpus import Corpus, VIANProject
from core.analysis.analysis_import import *

import numpy as np

from bokeh.models import Slider, Select, ColumnDataSource, Slider
from bokeh.plotting import figure
from core.data.computation import lch_to_human_readable, ms2datetime

from random import random
import cv2
from bokeh.layouts import column, layout
from bokeh.models import Button
from bokeh.palettes import RdYlBu3
from bokeh.plotting import figure, curdoc


def cvt_img(t, bw=False):

    if bw:
        t = cv2.cvtColor(t.astype(np.uint8)[::-1], cv2.COLOR_BGR2GRAY)
        t = cv2.cvtColor(t.astype(np.uint8), cv2.COLOR_GRAY2RGBA)
    else:
        t = cv2.cvtColor(t.astype(np.uint8)[::-1], cv2.COLOR_BGR2RGBA)
    img = np.zeros((t.shape[0], t.shape[1]), dtype=np.uint32)
    view = img.view(dtype=np.uint8).reshape(t.shape[0], t.shape[1], 4)
    view[:] = t[:]
    return img


def create_view(msource1, msource2, col1, col2, m_source_oflow1, m_source_oflow2,
                  m_source_eyet1, m_source_eyet2 ):
    p_m1 = figure(plot_width=400, plot_height=250)
    p_m1.image_rgba(image='img', x=0, y=0, dw='dw', dh='dh', source=msource1)
    p_m1.circle(x='xs', y='ys', source=source_spatial1, line_color="black", alpha=0.5)

    p_m2 = figure(plot_width=400, plot_height=250, x_range=p_m1.x_range, y_range=p_m1.y_range)
    p_m2.image_rgba(image='img', x=0, y=0, dw='dw', dh='dh', source=msource2)
    p_m2.circle(x='xs', y='ys', source=source_spatial2, line_color="black", alpha=0.5)

    p_col = figure(plot_width=800, plot_height=200, title="Color",  x_axis_type='datetime')
    p_col.vbar(x="x", bottom=0, top=1, color="red", width=3, source=source_time)
    p_col.line(x='t', y='l', source=col1, legend="Luminance")
    p_col.line(x='t', y='f', source=m_source_oflow1, color="gray", legend="Optical Flow")
    p_col.line(x='t', y='f', source=m_source_eyet1, color="red", legend="Eyetracking Variance")

    p_col2 = figure(plot_width=800, plot_height=200, title="Black & White",  x_axis_type='datetime')
    p_col2.vbar(x="x", bottom=0, top=1, color="red", width=3, source=source_time)
    p_col2.line(x='t', y='l', source=col2)
    p_col2.line(x='t', y='f', source=m_source_oflow2, color="gray")
    p_col2.line(x='t', y='f', source=m_source_eyet2, color="red")

    return [[p_m1, p_m2], p_col, p_col2]


corpus = Corpus().load("C:/Users/gaude/Documents/VIAN/corpora/eyetracking_corpus2/eyetracking_corpus.vian_corpus")
corpus.reload()

all_projects = dict()

source_time = ColumnDataSource(data=dict(x=[0]))
source_spatial1 = ColumnDataSource(data=dict(xs = [], ys = []))
source_spatial2 = ColumnDataSource(data=dict(xs = [], ys = []))

for k, p in corpus.projects_loaded.items():
    s_name = p.name.replace("True", "").replace("False", "")
    if s_name not in all_projects:
        all_projects[s_name] = dict(p1=p, p2=None)
    else:
        all_projects[s_name]['p2'] = p

pnames = list(all_projects.keys())

cap1 = None
cap2 = None

spatial_ds1 = None
spatial_ds2 = None
frame_pos = 0

def on_set_movie(attr, old, new):
    set_movie(new)


def set_movie(n):
    p1 = all_projects[n]['p1']
    p2 = all_projects[n]['p2']

    p1.connect_hdf5()
    p2.connect_hdf5()

    global cap1, cap2, spatial_ds1, spatial_ds2

    cap1 = cv2.VideoCapture(p1.movie_descriptor.movie_path)
    cap2 = cv2.VideoCapture(p2.movie_descriptor.movie_path)

    duration = cap1.get(cv2.CAP_PROP_FRAME_COUNT)
    time_slider.end = duration
    set_frame(0)

    t_range = np.array(list(range(len(np.array(p1.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata()).tolist())))) * 30 * cap1.get(cv2.CAP_PROP_FPS)
    t_range = [ms2datetime(t) for t in t_range]

    m_source_oflow1.data = dict(
        t = t_range,
        f = p1.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata() / np.amax(p1.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata())
    )
    m_source_oflow2.data = dict(
        t=t_range,
        f = p2.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata() / np.amax(p2.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata())
    )

    eyedata = EyetrackingAnalysis().get_timeline_datasets(p1.get_analyses_by_name("EyetrackingAnalysis")[0], p1)[0].data
    t_range = np.array(list(range(len(np.array(eyedata).tolist())))) * (1000 / (p1.movie_descriptor.fps / 30))
    t_range = [ms2datetime(t) for t in t_range]
    m_source_eyet1.data = dict(
        t=t_range,
        f=eyedata / np.amax(eyedata)
    )

    eyedata = EyetrackingAnalysis().get_timeline_datasets(p2.get_analyses_by_name("EyetrackingAnalysis")[0], p2)[0].data
    t_range = np.array(list(range(len(np.array(eyedata).tolist())))) * (1000 / (p1.movie_descriptor.fps / 30))
    m_source_eyet2.data = dict(
        t=t_range,
        f=eyedata / np.amax(eyedata)
    )

    spatial_ds1 = EyetrackingAnalysis().get_spatial_overlays(p1.get_analyses_by_name("EyetrackingAnalysis")[0], p1)[0]
    spatial_ds2 = EyetrackingAnalysis().get_spatial_overlays(p2.get_analyses_by_name("EyetrackingAnalysis")[0], p2)[0]

    colorimetry_data1 = dict(t=[], l=[], c=[], h=[])
    try:
        for i, entry in enumerate(p1.colormetry_analysis.iter_avg_color()):
            l, c, h = lch_to_human_readable([entry['l'], entry['c'], entry['h']])
            colorimetry_data1['t'].append(ms2datetime(entry['time_ms']))
            colorimetry_data1['l'].append(l / 100)
            colorimetry_data1['c'].append(c / 100)
            colorimetry_data1['h'].append(h / 360)
    except Exception as e:
        raise e

    colorimetry_data2 = dict(t=[], l=[], c=[], h=[])
    try:
        for i, entry in enumerate(p2.colormetry_analysis.iter_avg_color()):
            l, c, h = lch_to_human_readable([entry['l'], entry['c'], entry['h']])
            colorimetry_data2['t'].append(ms2datetime(entry['time_ms']))
            colorimetry_data2['l'].append(l / 100)
            colorimetry_data2['c'].append(c / 100)
            colorimetry_data2['h'].append(h / 360)
    except Exception as e:
        raise e


    m_source_col1.data = colorimetry_data1
    m_source_col2.data = colorimetry_data2



def on_time_change(attr, old, new):
    set_frame(new)


#bokeh serve --show extensions/plugins/eyetracking_bokeh/server.py

def set_frame(frame_pos):

    if cap1 is  None or cap2 is  None:
        return

    def update(idx, cap, source, bw=False):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, f1 = cap.read()
        f1 = cvt_img(f1, bw)
        if ret is None:
            return
        source.data = dict(
            img = [f1], dw=[f1.shape[1]], dh=[f1.shape[0]]
        )

    source_time.data = dict(x=[ms2datetime(frame_pos * cap1.get(cv2.CAP_PROP_FPS))])

    update(frame_pos, cap1, m_source1, False)
    update(frame_pos, cap2, m_source2, True)

    global spatial_ds1, spatial_ds2
    if spatial_ds1 is not None:
        data = spatial_ds1.get_data_for_time(None, frame_pos)
        source_spatial1.data = dict(
            xs = data[:, 0],
            ys=data[:, 1]
        )
    if spatial_ds2 is not None:
        data = spatial_ds2.get_data_for_time(None, frame_pos)
        source_spatial2.data = dict(
            xs = data[:, 0],
            ys=data[:, 1]
        )


movie_sel = Select(options=pnames, value=pnames[0])
movie_sel.on_change("value", on_set_movie)
time_slider = Slider(start = 0, end=100, value = 0)
time_slider.on_change("value", on_time_change)


m_source1 = ColumnDataSource(data=dict(
    img = [ cvt_img(np.zeros(shape=(500,500,3), dtype=np.uint8))], dw=[10], dh=[10],
))
m_source2 = ColumnDataSource(data=dict(
    img = [ cvt_img(np.zeros(shape=(500,500,3), dtype=np.uint8))], dw=[10], dh=[10],
))

m_source_col1 = ColumnDataSource(data= dict(t=[], l=[], c=[], h=[]))
m_source_col2 = ColumnDataSource(data= dict(t=[], l=[], c=[], h=[]))

m_source_oflow1 = ColumnDataSource(data= dict(t=[], f=[]))
m_source_oflow2 = ColumnDataSource(data= dict(t=[], f=[]))

m_source_eyet1 = ColumnDataSource(data= dict(t=[], f=[]))
m_source_eyet2 = ColumnDataSource(data= dict(t=[], f=[]))

lt = [
    movie_sel, time_slider
]

lt += create_view(m_source1, m_source2,
                  m_source_col1, m_source_col2,
                  m_source_oflow1, m_source_oflow2,
                  m_source_eyet1, m_source_eyet2)

set_movie(pnames[0])
# put the button and plot in a layout and add to the document
curdoc().add_root(layout(lt, sizing_mode="scale_width"))