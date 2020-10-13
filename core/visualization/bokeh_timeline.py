from bokeh.io import output_file, show
from bokeh.models import ColumnDataSource
from bokeh.plotting import figure
from bokeh.layouts import layout
from bokeh.embed import components

from core.container.project import *
import cv2
from random import sample
from core.data.computation import resize_with_aspect

def format_plot(p):
    return 
    p.background_fill_color = (17,17,17)


def generate_classification_plot(exp:Experiment, TOOLTIPS, TOOLS, x_range):
    plots = dict()
    for ukw in exp.get_unique_keywords():
        if len(ukw.tagged_containers) > 0:
            cl = ukw.class_obj.name + ":" + ukw.voc_obj.name
            if cl not in plots:
                plots[cl] = dict(start=[], end=[], y=[], text=[])
            for c in ukw.tagged_containers:
                plots[cl]['start'].append(c.get_start())
                plots[cl]['end'].append(c.get_end())
                plots[cl]['y'].append(ukw.word_obj.name)
                plots[cl]['text'].append(c.get_annotation_body())

    all_vis = []
    for n, c in plots.items():
        ds = ColumnDataSource(c)
        y_labels = list(set(c['y']))
        p = figure(plot_width=800, plot_height=300, y_range=y_labels, x_axis_type='datetime',
                   title=n, tooltips=TOOLTIPS, tools=TOOLS, x_range = x_range)

        p.hbar(left='start', right="end", y='y', source=ds, alpha=0.3)
        all_vis.append(p)
    return all_vis

def generate_plot(project:VIANProject, return_as_embed=False):
    _SEGMENTATIONS = []
    d = dict(start = [], end = [], text=[], segmentation=[])
    for s in project.segmentation:
        name = s.name
        i = 0
        while name in _SEGMENTATIONS:
            name = s.name + "_" + str(i)
            i += 1
        _SEGMENTATIONS.append(name)
        for t in s.segments:# type:Segment
            d['start'].append(t.get_start())
            d['end'].append(t.get_end())
            d['text'].append(t.get_annotation_body())
            d['segmentation'].append(name)

    source_segments = ColumnDataSource(d)

    d2 = dict(t = [], l=[], c=[], h=[])
    try:
        for i, entry in enumerate(project.colormetry_analysis.iter_avg_color()):
            l, c, h = lch_to_human_readable([entry['l'], entry['c'], entry['h']])
            d2['t'].append(entry['time_ms'])
            d2['l'].append(l)
            d2['c'].append(c)
            d2['h'].append(h)
    except Exception as e:
        log_warning(e)

    cap = cv2.VideoCapture(project.movie_descriptor.movie_path)
    d3 = dict(img=[], t = [], y=[])
    i = 0

    for scr in sample(project.screenshots, np.clip(len(project.screenshots), 0, 100)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(scr.frame_pos))
        ret, t = cap.read()
        t = resize_with_aspect(t, width=128)
        t = cv2.cvtColor(t, cv2.COLOR_BGR2RGBA)
        img = np.zeros((t.shape[0], t.shape[1]), dtype=np.uint32)
        view = img.view(dtype=np.uint8).reshape(t.shape[0], t.shape[1], 4)
        view[:] = t[:]

        d3['img'].append(img[::-1])
        d3['t'].append(scr.get_start())
        d3['y'].append(i*200)
        i += 1
        if i == 5:
            i = 0

    source_screenshots = ColumnDataSource(d3)

    _COLORIMETRY = ["Luminance", "Chroma", "Hue"]
    colorimetry = ColumnDataSource(d2)

    output_file("bars.html")

    TOOLTIPS = [
        ("Text", "@text"),
        ("(start, end)", "(@start, @end)"),
    ]
    TOOLS = ["xpan", "save", "reset", "xwheel_zoom"]

    p = figure(plot_width=800, plot_height=300, y_range=_SEGMENTATIONS, x_axis_type='datetime',
               title="Segmentation", tooltips=TOOLTIPS, tools=TOOLS)
    p.hbar(left='start', right="end", y='segmentation',  source=source_segments, alpha=0.3)
    p.css_classes.append("sticky-top")

    p_scr = figure(plot_width=800, plot_height=600, x_axis_type='datetime',
               title="Segmentation", tooltips=TOOLTIPS,  x_range = p.x_range, y_range = None,tools=TOOLS)
    p_scr.image_rgba(x='t', image="img", y="y", source= source_screenshots, dh_units="screen", dw_units="screen", dw =150, dh=150*(10/16) )

    p_colorimetry = figure(plot_width=800, plot_height=300, x_axis_type='datetime',
               title="Luminance", x_range = p.x_range,tools=TOOLS)
    p_colorimetry.line(x="t", y="l", source=colorimetry, line_color="blue")
    p_colorimetry1 = figure(plot_width=800, plot_height=300, x_axis_type='datetime',
                           title="Chroma", x_range=p.x_range,tools=TOOLS)
    p_colorimetry1.line(x="t", y="c", source=colorimetry, line_color="red")
    p_colorimetry2 = figure(plot_width=800, plot_height=300, x_axis_type='datetime',
                           title="Hue", x_range=p.x_range,tools=TOOLS)

    p_colorimetry2.line(x="t", y="h", source=colorimetry, line_color="green")

    p.xaxis[0].formatter.days = ['%Hh']
    p.x_range.range_padding = 0
    p.ygrid.grid_line_color = None

    ps = generate_classification_plot(project.experiments[0], TOOLTIPS, TOOLS, p.x_range)


    plots = [p_scr, p, p_colorimetry, p_colorimetry1, p_colorimetry2] + ps
    for p in plots:
        format_plot(p)
    lt = layout(plots, sizing_mode="stretch_width")

    if return_as_embed:
        return components(lt)
    else:
        show(lt, sizing_mode="stretch_width")


if __name__ == '__main__':
    project = VIANProject().load_project("C:\\Users\\gaude\\Documents\\VIAN\\projects\\VIAN-Teaching_01\\VIAN-Teaching_01.eext")
    generate_plot(project)