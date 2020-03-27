// create a data source to hold data
class ColorAB {
    constructor(divName) {
        this.divName = divName;
        this.grid_col = "rgb(255,255,255)"
        this.background = "rgb(17,17,17)"

        this.grid_renderer = []

        this.source = new Bokeh.ColumnDataSource({
            data: { x: [], y: [], image: [] }
        });
        this.source.selected.callback = function(){console.log("Hello World")}
        console.log(this.source)

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
        this.aspect = 9.0 / 16


        var r = this.plot.image_url({url: { field: "image" },x: { field: "x" },y: { field: "y" },
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
        for (var i = 0; i < 10; i++) {
            let t = this.plot.circle({ x: 0, y: 0, radius: i * this.q, fill_alpha: 0, line_color: this.grid_col, line_alpha: 0.2, line_width: 1.0 })
            this.grid_renderer.push(t);

        }
        
        var doc = new Bokeh.Document();
        doc.add_root(this.plot);
        Bokeh.embed.add_document_standalone(doc, document.getElementById(divName));
        this.source.change.emit()
    }

    setBackgroundColor(r, g, b){
        let col = "rgb(" + r + "," + g + "," + b + ")";
        let line = "rgb(255,255,255)";
        if (r + g + b > 300){
            line = "rgb(0,0,0)"
        }
        this.grid_renderer.forEach(function(elem){
            elem.glyph.line_color = line;
        });
        this.plot.background_fill_color = col;
        this.plot.background_fill_color = col;
        if (r < 100){
            this.plot.background_fill_alpha = 0.0;
            this.plot.border_fill_alpha = 0.0;
        }else{
            this.plot.background_fill_alpha = 1.0;
            this.plot.border_fill_alpha = 1.0;
        }
        console.log(this.plot.background_fill_alpha, this.plot.background_fill_color)
    }

    setData(a, b, urls){
        this.source.data.x = a;
        this.source.data.y =b;
        this.source.data.image = urls
        this.source.change.emit();
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
            complete: function(){
                setTimeout(function(){that.poll(pollTime); }, pollTime);
            }
        });

    }
}