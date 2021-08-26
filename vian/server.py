# "C:/Users/gaude/Documents/VIAN/corpora/eyetracking_corpus2/eyetracking_corpus.vian_corpus"
from core.container.corpus import Corpus, VIANProject
from core.analysis.analysis_import import *

import numpy as np

from bokeh.models import Slider, Select, ColumnDataSource, Slider, Tabs, Panel, Spinner
from bokeh.plotting import figure
from core.data.computation import lch_to_human_readable, ms2datetime

from matplotlib import pyplot as plt

from random import random
import cv2
from bokeh.layouts import column, layout, row
from bokeh.models import Button
from bokeh.colors import RGB
from bokeh.palettes import RdYlBu3
from bokeh.plotting import figure, curdoc

from core.data.computation import resize_with_aspect
import pickle

R_SIZE = 300

ds_col = ColumnDataSource(data=dict(xs=[], ys=[], a1=[], a2=[], r1=[], r2=[], color=[], alpha=[]))
ds_col2 = ColumnDataSource(data=dict(xs=[], ys=[], a1=[], a2=[], r1=[], r2=[], color=[], alpha=[]))


def palette_heatmap_ds(source, image):
    def pol2cart(r, phi):
        x = r * np.cos(phi)
        y = r * np.sin(phi)
        return (x, y)

    C_BINS = 40
    HUE_BINS = 70

    rgbs = image

    labs = cv2.cvtColor(rgbs.astype(np.float32) / 255, cv2.COLOR_BGR2LAB)
    labs = np.reshape(labs, newshape=(labs.shape[0] * labs.shape[1], 3))
    labs = labs[np.where(labs[:, 0] > 0)]
    lchs = lab_to_lch(labs)

    hist = cv2.calcHist([lchs[:, 1], lchs[:, 2]], [0, 1], None,
                        [C_BINS, HUE_BINS],
                        [0, 128, -np.pi, np.pi])

    hist /= (image.shape[0] * image.shape[1])
    hist = np.log10(hist + 1)
    hist /= np.amax(hist)
    xs = [0] * (C_BINS * HUE_BINS)
    ys = [0] * (C_BINS * HUE_BINS)
    a1, a2 = [], []
    r1, r2 = [], []
    color = []
    alpha = []

    for c in range(C_BINS):
        for h in range(HUE_BINS):
            a1.append(h * ((np.pi * 2) / HUE_BINS) - np.pi)
            a2.append((1 + h) * ((np.pi * 2) / HUE_BINS) - np.pi)
            r1.append(c * (128 / C_BINS))
            r2.append((c + 1) * (128 / C_BINS))

            ab = pol2cart((c + 0.5) * (128 / C_BINS), (0.5 + h) * ((np.pi * 2) / HUE_BINS) - np.pi)
            color.append([50,
                          ab[0],
                          ab[1]])
            alpha.append(hist[c][h])

    alpha = np.array(alpha)
    alpha = np.clip(alpha, 0.01, 1.0)
    color = cv2.cvtColor(np.array([color, color], dtype=np.float32), cv2.COLOR_LAB2RGB)[0]
    color = [RGB(c[0] * 255, c[1] * 255, c[2] * 255) for c in color]

    source.data = dict(
        xs=xs, ys=ys, a1=a1, a2=a2, r1=r1, r2=r2, color=color, alpha=alpha
    )


def palette_heatmap_plot(ds, title):
    """
       .. figure:: palette_plot.png
          :scale: 50 %
          :align: center
          :alt: LA Plots as created from this code

       :param screenshot_ds: The ColumnDataSource as create from  genererate_interactive_ds()
       :return: A bokeh visualizations
       """
    p = figure(plot_width=400, plot_height=400, x_range=[-128, 128], y_range=[-128, 128], title=title)
    p.annular_wedge(x='xs', y='ys', inner_radius='r1', outer_radius='r2',
                    start_angle='a1', end_angle='a2', color='color', alpha='alpha', source=ds)
    return (p)


contour_source1 = ColumnDataSource(data={'xs': [], 'ys': [], 'line_color': [], 'xt': [], 'yt': [], 'text': []})
contour_source2 = ColumnDataSource(data={'xs': [], 'ys': [], 'line_color': [], 'xt': [], 'yt': [], 'text': []})


def get_contour_data(source, X, Y, w, h):
    print(w, h)
    n_bins_x = 32
    n_bins_y = 18
    hist, bx, by = np.histogram2d(X, Y, bins=[np.arange(0, w, w / n_bins_x), np.arange(0, h, h / n_bins_y)])

    hist = np.rot90(hist)
    X, Y = np.meshgrid(range(n_bins_x - 1), range(n_bins_y - 1))
    cs = plt.contour(X, Y, hist)

    xs = []
    ys = []
    xt = []
    yt = []
    col = []
    text = []
    isolevelid = 0

    for isolevel in cs.collections:

        isocol = isolevel.get_color()[0]
        thecol = 3 * [None]
        theiso = str(cs.get_array()[isolevelid])
        isolevelid += 1
        for i in range(3):
            thecol[i] = int(255 * isocol[i])
        thecol = '#%02x%02x%02x' % (thecol[0], thecol[1], thecol[2])

        for path in isolevel.get_paths():
            v = path.vertices
            x = ((v[:, 0] / (n_bins_x)) * w) + (w / n_bins_x)
            y = ((v[:, 1] / (n_bins_y)) * h) + (h / n_bins_y)
            xs.append(x.tolist())
            ys.append(y.tolist())
            xt.append(x[int(len(x) / 2)])
            yt.append(y[int(len(y) / 2)])
            text.append(theiso)
            col.append(thecol)

    source.data = {'xs': xs, 'ys': ys, 'line_color': col, 'xt': xt, 'yt': yt, 'text': text}
    return hist


def cvt_img(t, bw=False):
    t = resize_with_aspect(t, width=300)
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
                m_source_eyet1, m_source_eyet2):
    p_m1 = figure(plot_width=400, plot_height=250)
    p_m1.image_rgba(image='img', x=0, y=0, dw='dw', dh='dh', source=msource1)
    p_m1.multi_line(xs='xs', ys='ys', line_color='line_color', source=contour_source1)
    p_m1.circle(x='xs', y='ys', source=source_spatial1, fill_alpha=0.5, line_color="black", color="red", alpha=0.5)

    p_m2 = figure(plot_width=400, plot_height=250, x_range=p_m1.x_range, y_range=p_m1.y_range)
    p_m2.image_rgba(image='img', x=0, y=0, dw='dw', dh='dh', source=msource2)
    p_m2.multi_line(xs='xs', ys='ys', line_color='line_color', source=contour_source2)
    p_m2.circle(x='xs', y='ys', source=source_spatial2, line_color="black", fill_alpha=0.5, color="red", alpha=0.5)

    p_col = figure(plot_width=800, plot_height=200, title="Eyetracking - Color", x_axis_type='datetime')
    p_col.vbar(x="x", bottom=0, top=1, color="red", width=3, source=source_time)
    p_col.line(x='t', y='f', source=m_source_oflow1, color="gray", legend="Optical Flow")
    p_col.line(x='t', y='f', source=m_source_eyet1, color="red", legend="Eyetracking Variance (Color)")
    p_col.line(x='t', y='f', source=m_source_eyet2, color="blue", legend="Eyetracking Variance (B&W)")

    # p_col2 = figure(plot_width=800, plot_height=200, title="Eyetracking - Black & White",  x_axis_type='datetime',
    #                 x_range=p_col.x_range, y_range=p_col.y_range)
    # p_col2.vbar(x="x", bottom=0, top=1, color="red", width=3, source=source_time)
    # p_col2.line(x='t', y='f', source=m_source_oflow2, color="gray")
    # p_col2.line(x='t', y='f', source=m_source_eyet2, color="red")

    p_coli = figure(plot_width=800, plot_height=200, title="Colorimetry", x_axis_type='datetime', x_range=p_col.x_range,
                    y_range=p_col.y_range)
    p_coli.vbar(x="x", bottom=0, top=1, color="red", width=3, source=source_time)
    p_coli.line(x='t', y='l', source=col1, color="gray", legend="Luminance")
    p_coli.line(x='t', y='c', source=col1, color="green", legend="Chroma")
    p_coli.line(x='t', y='h', source=col1, color="blue", legend="Hue")

    tab1 = Panel(child=row([p_coli], sizing_mode="scale_width"), title="Colorimetry")

    p_col_distribution = palette_heatmap_plot(ds_col, title="Color Histogram - Total")
    p_col_distribution2 = palette_heatmap_plot(ds_col2, title="Color Histogram - Fixations")

    tab2 = Panel(child=row([p_col_distribution, p_col_distribution2], sizing_mode="scale_width"),
                 title="Fixation color distribution")

    return [[p_m1, p_m2], [p_col], [Tabs(tabs=[tab1, tab2])]]


corpus = Corpus().load("C:/Users/gaude/Documents/VIAN/corpora/eyetracking_corpus2/eyetracking_corpus.vian_corpus")
corpus.reload()

all_projects = dict()

source_time = ColumnDataSource(data=dict(x=[0]))
source_spatial1 = ColumnDataSource(data=dict(xs=[], ys=[]))
source_spatial2 = ColumnDataSource(data=dict(xs=[], ys=[]))

for k, p in corpus.projects_loaded.items():
    s_name = p.name.replace("True", "").replace("False", "")
    old_path = p.movie_descriptor.movie_path
    p.movie_descriptor.movie_path = os.path.join("videos", os.path.split(old_path)[1])

    p.store_project()

    if s_name not in all_projects:
        all_projects[s_name] = dict(p1=p, p2=None)
    else:
        all_projects[s_name]['p2'] = p

pnames = list(all_projects.keys())

cap1 = None
cap2 = None

width = 300
height = 300

spatial_ds1 = None
spatial_ds2 = None
frame_pos = 0

cach_dir = "bokehcache"
if not os.path.isdir(cach_dir):
    os.mkdir(cach_dir)


def on_set_movie(attr, old, new):
    set_movie(new)


def dump_spatial(self):
    return dict(
        fixations_sampled=self.fixations_sampled,
        time_np=self.time_np,
        fixations_np=self.fixations_np,
        fps=self.fps,
        height=self.height,
        width=self.width
    )


def load_spatial(self, d):
    self.fixations_sampled = d['fixations_sampled']
    self.time_np = d['time_np']
    self.fixations_np = d['fixations_np']
    self.fps = d['fps']
    self.height = d['height']
    self.width = d['width']


def set_movie(n):
    global cap1, cap2, spatial_ds1, spatial_ds2, height, width

    p1 = all_projects[n]['p1']
    p2 = all_projects[n]['p2']

    p1.connect_hdf5()
    cap1 = cv2.VideoCapture(p1.movie_descriptor.movie_path)

    if p2 is not None:
        p2.connect_hdf5()
        cap2 = cv2.VideoCapture(p2.movie_descriptor.movie_path)

    height = cap1.get(cv2.CAP_PROP_FRAME_HEIGHT)
    width = cap1.get(cv2.CAP_PROP_FRAME_WIDTH)
    duration = cap1.get(cv2.CAP_PROP_FRAME_COUNT)
    time_slider.end = duration
    time_spinner.high = duration
    time_slider.value = 0
    time_spinner.value = 0
    set_frame(0)

    cache_path = os.path.join(cach_dir, n + ".pkl")
    if os.path.isfile(cache_path) is False:
        t_range = np.array(list(
            range(len(np.array(p1.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata()).tolist())))) * 30 * cap1.get(
            cv2.CAP_PROP_FPS)
        t_range = [ms2datetime(t) for t in t_range]

        m_source_oflow1.data = dict(
            t=t_range,
            f=p1.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata() / np.amax(
                p1.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata())
        )

        eyedata1 = EyetrackingAnalysis().get_timeline_datasets(p1.get_analyses_by_name("EyetrackingAnalysis")[0], p1)[
            0].data
        t_range = np.array(list(range(len(np.array(eyedata1).tolist())))) * (1000 / (p1.movie_descriptor.fps / 30))
        t_range = [ms2datetime(t) for t in t_range]

        spatial_ds1 = EyetrackingAnalysis().get_spatial_overlays(p1.get_analyses_by_name("EyetrackingAnalysis")[0], p1)[0]

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
        m_source_col1.data = colorimetry_data1
        eyedata2 = None

        if p2 is not None:
            m_source_oflow2.data = dict(
                t=t_range,
                f=p2.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata() / np.amax(
                    p2.get_analyses_by_name("OpticalFlowAnalysis")[0].get_adata())
            )
            eyedata2 = EyetrackingAnalysis().get_timeline_datasets(p2.get_analyses_by_name("EyetrackingAnalysis")[0], p2)[
                0].data
            t_range2 = np.array(list(range(len(np.array(eyedata2).tolist())))) * (1000 / (p1.movie_descriptor.fps / 30))

            spatial_ds2 = EyetrackingAnalysis().get_spatial_overlays(p2.get_analyses_by_name("EyetrackingAnalysis")[0], p2)[
                0]

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
            m_source_col2.data = colorimetry_data2
        else:
            m_source_eyet2.data = dict()
            m_source_col2.data = dict()

        if eyedata2 is None:
            eyedata2 = np.array([0] * len(t_range))
            t_range2 = t_range

        print(eyedata1.shape, eyedata2.shape)
        tmax = np.amax(np.array(eyedata1.tolist() + eyedata2.tolist()))
        m_source_eyet1.data = dict(
            t=t_range,
            f=eyedata1 / tmax
        )

        m_source_eyet2.data = dict(
            t=t_range2,
            f=eyedata2 / tmax
        )

        cache = dict(
            m_source_oflow2=dict(m_source_oflow2.data),
            m_source_oflow1=dict(m_source_oflow1.data),
            m_source_eyet1=dict(m_source_eyet1.data),
            m_source_eyet2=dict(m_source_eyet2.data),
            spatial_ds1=dump_spatial(spatial_ds1),
            spatial_ds2=dump_spatial(spatial_ds2),
            m_source_col1=dict(m_source_col1.data),
            m_source_col2=dict(m_source_col2.data)
        )
        with open(cache_path, "wb") as f:
            pickle.dump(cache, f)
    else:
        with open(cache_path, "rb") as f:
            d = pickle.load(f)

        m_source_oflow1.data = d['m_source_oflow1']
        m_source_oflow2.data = d['m_source_oflow2']

        m_source_eyet1.data = d['m_source_eyet1']
        m_source_eyet2.data = d['m_source_eyet2']

        if spatial_ds1 is None:
            spatial_ds1 = EyetrackingAnalysis().get_spatial_overlays(p1.get_analyses_by_name("EyetrackingAnalysis")[0], p1)[0]
        if spatial_ds2 is None:
            spatial_ds2 = EyetrackingAnalysis().get_spatial_overlays(p2.get_analyses_by_name("EyetrackingAnalysis")[0], p2)[0]

        load_spatial(spatial_ds1, d['spatial_ds1'])
        load_spatial(spatial_ds2, d['spatial_ds2'])
        m_source_col1.data = d['m_source_col1']
        m_source_col2.data = d['m_source_col2']


def on_time_change(attr, old, new):
    time_slider.value = new
    time_spinner.value = new
    set_frame(new)


# bokeh serve --show extensions/plugins/eyetracking_bokeh/server.py

def set_frame(frame_pos):
    if cap1 is None or cap2 is None:
        return

    def update(idx, cap, source, bw=False):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, f1 = cap.read()
        f1_ret = cvt_img(f1, bw)
        if ret is None:
            return

        source.data = dict(
            img=[f1_ret], dw=[f1.shape[1]], dh=[f1.shape[0]]
        )
        return f1

    source_time.data = dict(x=[ms2datetime(frame_pos * cap1.get(cv2.CAP_PROP_FPS))])

    frame = update(frame_pos, cap1, m_source1, False)
    palette_heatmap_ds(ds_col, frame)

    update(frame_pos, cap2, m_source2, True)

    global spatial_ds1, spatial_ds2
    if spatial_ds1 is not None:
        data = spatial_ds1.get_data_for_time(None, frame_pos)
        source_spatial1.data = dict(
            xs= data[:, 0],
            ys=(data[:, 1] * -1) + height
        )
        hist = get_contour_data(contour_source1, data[:, 0], data[:, 1], width, height)

        pxls = cv2.resize(hist, frame.shape[:2][::-1], cv2.INTER_NEAREST)
        f2 = frame.copy()

        f2[np.where(pxls == 0)] = [0, 0, 0]

        palette_heatmap_ds(ds_col2, f2)

    if spatial_ds2 is not None:
        data = spatial_ds2.get_data_for_time(None, frame_pos)
        source_spatial2.data = dict(
            xs=data[:, 0],
            ys=(data[:, 1] * -1) + height
        )
        get_contour_data(contour_source2, data[:, 0], data[:, 1], width, height)


movie_sel = Select(options=pnames, value=pnames[0])
movie_sel.on_change("value", on_set_movie)

time_slider = Slider(start=0, end=100, value=0, step=10, value_throttled=2.0)
time_slider.on_change("value", on_time_change)
time_spinner = Spinner(low=0, high=100, value=0, step=10)
time_spinner.on_change("value", on_time_change)

m_source1 = ColumnDataSource(data=dict(
    img=[cvt_img(np.zeros(shape=(500, 500, 3), dtype=np.uint8))], dw=[10], dh=[10],
))
m_source2 = ColumnDataSource(data=dict(
    img=[cvt_img(np.zeros(shape=(500, 500, 3), dtype=np.uint8))], dw=[10], dh=[10],
))

m_source_col1 = ColumnDataSource(data=dict(t=[], l=[], c=[], h=[]))
m_source_col2 = ColumnDataSource(data=dict(t=[], l=[], c=[], h=[]))

m_source_oflow1 = ColumnDataSource(data=dict(t=[], f=[]))
m_source_oflow2 = ColumnDataSource(data=dict(t=[], f=[]))

m_source_eyet1 = ColumnDataSource(data=dict(t=[], f=[]))
m_source_eyet2 = ColumnDataSource(data=dict(t=[], f=[]))

lt = [
    movie_sel, [time_slider,time_spinner]
]

lt += create_view(m_source1, m_source2,
                  m_source_col1, m_source_col2,
                  m_source_oflow1, m_source_oflow2,
                  m_source_eyet1, m_source_eyet2)

# put the button and plot in a layout and add to the document

# Caching
for n in pnames:
    print("Caching", n)
    set_movie(n)

# bokeh serve server.py --port 5100 --allow-websocket-origin=pcatestwebapp.westeurope.cloudapp.azure.com
set_movie(pnames[0])
curdoc().add_root(layout(lt, sizing_mode="scale_width"))