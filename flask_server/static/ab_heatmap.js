class ABHeatmap {
    constructor(divName) {
        this.divName = divName;
        this.grid_col = "rgb(255,255,255)"
        this.background = "rgb(17,17,17)"

        this.grid_renderer = []

        this.source = new Bokeh.ColumnDataSource({
            data: { xs: [], ys: [], r1: [], r2:[], a1: [], a2: [], color:[], alpha:[] }
        });

        this.plot = Bokeh.Plotting.figure({
            title: 'Color CIE-Lab (AB - Plane)',
            tools: "pan,wheel_zoom,box_zoom,reset,save",
            height: 300,
            width: 300,
            x_axis_label: "A-Channel",
            y_axis_label: "Y-Channel",
            x_range: new Bokeh.Range1d({ start: -128, end: 128 }),
            y_range: new Bokeh.Range1d({ start: -128, end: 128 }),
        });

        this.plot.center[0].grid_line_alpha = 0.0
        this.plot.center[1].grid_line_alpha = 0.0

        this.plot.background_fill_color = this.background
        this.plot.background_fill_alpha = 0.0
        this.plot.border_fill_alpha = 0.0
        this.plot.sizing_mode = "scale_width"

        var r = annular_wedge({
            x: { field: "xs" },
            y: { field: "ys" },
            inner_radius={ field: "r1" },
            outer_radius={ field: "r2" },
            start_angle={ field: "a1" },
            end_angle={ field: "a2" },
            color={ field: "color" },
            alpha={ field: "alpha" },
            source=this.source
        })

        r.glyph.h.units = "screen"
        r.glyph.w.units = "screen"

        var doc = new Bokeh.Document();
        doc.add_root(this.plot);
        Bokeh.embed.add_document_standalone(doc, document.getElementById(divName));
        this.source.change.emit()
    }

    setBackgroundColor(r, g, b) {
        let col = "rgb(" + r + "," + g + "," + b + ")";
        let line = "rgb(255,255,255)";
        if (r + g + b > 300) {
            line = "rgb(0,0,0)"
        }
        this.grid_renderer.forEach(function (elem) {
            elem.glyph.line_color = line;
        });
        this.plot.background_fill_color = col;
        this.plot.background_fill_color = col;
        if (r < 100) {
            this.plot.background_fill_alpha = 0.0;
            this.plot.border_fill_alpha = 0.0;
        } else {
            this.plot.background_fill_alpha = 1.0;
            this.plot.border_fill_alpha = 1.0;
        }
        console.log(this.plot.background_fill_alpha, this.plot.background_fill_color)
    }

    setData(xs, ys, r1, r2, a1, a2, color, alpha) {
        this.source.data.xs = xs;
        this.source.data.ys = ys;
        this.source.data.r1 = r1;
        this.source.data.r2 = r2;
        this.source.data.a1 = a1;
        this.source.data.a2 = a2;
        this.source.data.color = color;
        this.source.data.alpha = alpha;

        this.source.change.emit();
    }
}