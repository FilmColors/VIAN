
class ColorAB {
    constructor(divName) {
        this.divName = divName;

        this.selectionCallback = null;

        this.source = new Bokeh.ColumnDataSource({
            data: { x: [], y: [], image: [], uuids: [] }
        });

        this.source_grid = new Bokeh.ColumnDataSource({
            data: { x: [], y: [], radius: [] }
        });

        var that = this;
        this.source.selected.change.connect(function (a, selection) {
            that.onSelectionChanged(that.source, selection);
        })

        new ResizeObserver(() => {this.onResize()}).observe(document.getElementById(divName));

        this.plot = Bokeh.Plotting.figure({
            tools: "lasso_select,pan,wheel_zoom,box_zoom,reset,save",
            aspect_ratio: 1,
            x_axis_label: "A-Channel",
            y_axis_label: "B-Channel",
            match_aspect: true,
        });

        this.plot.center[0].grid_line_alpha = 0.0
        this.plot.center[1].grid_line_alpha = 0.0

        this.aspect = 9.0 / 16

        this.grid_renderer = this.plot.circle({
            x: { field: "x" },
            y: { field: "y" },
            radius: { field: "radius" },
            fill_alpha: 0,
            line_alpha: 0.6,
            line_width: 1.0,
            source: this.source_grid
        })

        this.glyph_renderer = this.plot.image_url({
            url: { field: "image" },
            x: { field: "x" },
            y: { field: "y" },
            anchor: "center",
            source: this.source
        });

        var doc = new Bokeh.Document();
        doc.add_root(this.plot);
        Bokeh.embed.add_document_standalone(doc, document.getElementById(divName));
        this.source.change.emit()
    }

    setBackgroundColor(back, front) {
        let col = "rgb(" + back + "," + back + "," + back + ")";
        let line = "rgb(" + front + "," + front + "," + front + ")";

        this.grid_renderer.glyph.line_color = line;
        this.plot.background_fill_color = col;
        this.plot.border_fill_color = col;

        this.plot.xaxis[0].axis_line_color = line;
        this.plot.xaxis[0].major_tick_line_color = line;
        this.plot.xaxis[0].minor_tick_line_color = line;
        this.plot.xaxis[0].axis_label_text_color = line;
        this.plot.xaxis[0].major_label_text_color = line;
        this.plot.yaxis[0].axis_line_color = line;
        this.plot.yaxis[0].major_tick_line_color = line;
        this.plot.yaxis[0].minor_tick_line_color = line;
        this.plot.yaxis[0].axis_label_text_color = line;
        this.plot.yaxis[0].major_label_text_color = line;
        this.plot.outline_line_color = line;
    }

    setImageSize(s){
        this.glyph_renderer.glyph.h = s * this.aspect;
        this.glyph_renderer.glyph.w = s;
        this.glyph_renderer.glyph.h.units = "screen";
        this.glyph_renderer.glyph.w.units = "screen";

        this.source.change.emit();
    }
    setCircleInterval(s){
        this.interval = s;

        this.update_grid(this.interval);
    }

    setData(a, b, urls, uuids) {
        this.source.data.x = a;
        this.source.data.y = b;
        this.source.data.image = urls;
        this.source.data.uuids = uuids;

        if (a.length > 0){
            this.ab_max = Math.max(Math.abs(Math.min(Math.min(...a), Math.min(...b))), Math.max(Math.max(...a), Math.max(...b)))
            this.plot.x_range = new Bokeh.Range1d({ start: this.ab_max*-1, end: this.ab_max });
            this.plot.y_range = new Bokeh.Range1d({ start: this.ab_max*-1, end: this.ab_max });
        }
        this.source.change.emit();
    }

    update_grid(interval){
        this.source_grid.data.x = [];
        this.source_grid.data.y = [];
        this.source_grid.data.radius = [];

        //in Lab color space, the ranges for a and b values are [-110, 110]
        for (var i = parseFloat(interval); i <= 110; i = i + parseFloat(interval)) {
            this.source_grid.data.x.push(0);
            this.source_grid.data.y.push(0);
            this.source_grid.data.radius.push(i);
        }
        this.source_grid.change.emit();
    }

    poll(pollTime) {
        var that = this;
        this.source.change.emit();
        $.ajax({
            type: 'GET',
            contentType: 'application/json',
            dataType: 'json',
            url: "/screenshot-data/",
            success: function (e) {
                if (e.changes || that.source.data.x.length == 0) {
                    that.source.data.x = e.data.a;
                    that.source.data.y = e.data.b;
                    that.source.data.image = e.data.urls
                }
            },
            error: function (error, timeout) {
                console.log(error);
            },
            complete: function () {
                setTimeout(function () { that.poll(pollTime); }, pollTime);
            }
        });

    }

    onSelectionChanged(source, selection) {
        if (this.selectionCallback != null) {
            let uuids = [];
            selection.indices.forEach(elem => {
                uuids.push(source.data.uuids[elem]);
            })
            if (uuids.length == 0) {
                this.selectionCallback(source.data.uuids);
            }
            else {
                this.selectionCallback(uuids);
            }

        }
    }

    onResize(){
        let elem = document.getElementById(this.divName)
        if (elem.clientHeight > elem.clientWidth){
            this.plot.sizing_mode = "scale_width"
        }else{
            this.plot.sizing_mode = "scale_height"
    }
}


}