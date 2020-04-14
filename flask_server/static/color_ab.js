// create a data source to hold data
class ColorAB {
    constructor(divName) {
        this.divName = divName;
        this.grid_col = "rgb(255,255,255)"
        this.background = "rgb(17,17,17)"

        this.selectionCallback = null;

        this.grid_renderer = []

        this.source = new Bokeh.ColumnDataSource({
            data: { x: [], y: [], image: [], uuids: [] }
        });

        this.source_grid = new Bokeh.ColumnDataSource({
            data: { x: [], y: [], radius: [] }
        });

        var that = this;
        // this.source.selected.callback = function(){console.log("Hello World")}
        this.source.selected.change.connect(function (a, selection) {
            that.onSelectionChanged(that.source, selection);
        })
        console.log(this.source)

        this.plot = Bokeh.Plotting.figure({
            title: 'Color CIE-Lab (AB - Plane)',
            tools: "lasso_select, pan,wheel_zoom,box_zoom,reset,save",
            height: 300,
            width: 300,
            x_axis_label: "A-Channel",
            y_axis_label: "Y-Channel",
            match_aspect:true, 

            // x_range: new Bokeh.Range1d({ start: -128, end: 128 }),
            // y_range: new Bokeh.Range1d({ start: -128, end: 128 }),
        });

        this.plot.center[0].grid_line_alpha = 0.0
        this.plot.center[1].grid_line_alpha = 0.0

        this.plot.background_fill_color = this.background
        this.plot.background_fill_alpha = 0.0
        this.plot.border_fill_alpha = 0.0
        this.plot.sizing_mode = "scale_width"
        this.aspect = 9.0 / 16

        this.plot.circle({
            x: { field: 'x' },
            y: { field: 'y' },
            fill_alpha: 0.0,
            line_alpha: 0.0,
            source: this.source
        })

        var r = this.plot.image_url({
            url: { field: "image" }, x: { field: "x" }, y: { field: "y" },
            w: 20,
            h: 20 * this.aspect,
            anchor: "center",
            // global_alpha: 0.2,
            source: this.source
        });
        r.glyph.h.units = "screen"
        r.glyph.w.units = "screen"

        // this.plot.add_tools(Bokeh.LassoSelectTool({callback:function(){console.log("Hello World")}}))

        this.q = 20

        // for (var i = 0; i < 10; i++) {
        //     let t = this.plot.circle({ x: 0, y: 0, 
        //         radius: i * this.q, 
        //         fill_alpha: 0, 
        //         line_color: 
        //         this.grid_col, 
        //         line_alpha: 0.2, 
        //         line_width: 1.0 }
        //     )
        //     this.grid_renderer.push(t);
        // }

        for (var i = 0; i < 10; i++) {
            this.source_grid.data.x.push(0);
            this.source_grid.data.y.push(0);
            this.source_grid.data.radius.push(i * this.q);
        }

        this.plot.circle({
            x: { field: "x" },
            y: { field: "y" },
            radius: { field: "radius" },
            fill_alpha: 0,
            line_color: this.grid_col,
            line_alpha: 0.1,
            line_width: 1.0,
            source: this.source_grid
        })

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

    setData(a, b, urls, uuids) {
       

        this.source.data.x = a;
        this.source.data.y = b;
        this.source.data.image = urls;
        this.source.data.uuids = uuids;

        if (a.length > 0){
            this.ab_max = Math.max(Math.abs(Math.min(Math.min(...a), Math.min(...b))), Math.max(Math.max(...a), Math.max(...b)))
            this.update_grid(this.ab_max)
        }


        this.source.change.emit();
    }

    update_grid(max){
        this.source_grid.data.x = [];
        this.source_grid.data.y = [];
        this.source_grid.data.radius = [];
        
        let step = Math.ceil(max / 20)
        let grid_max = step * 20
        if (grid_max > 100){
            let step = 20
        }else if (grid_max > 50){
            let step = 10
        }else{
            let step = 5
        }

        let n_steps = grid_max / step + 1

        for (var i = 0; i < n_steps; i++) {
            this.source_grid.data.x.push(0);
            this.source_grid.data.y.push(0);
            this.source_grid.data.radius.push(i * step);
        }

        
        this.source_grid.change.emit();

        // this.plot.reset.emit()
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
}