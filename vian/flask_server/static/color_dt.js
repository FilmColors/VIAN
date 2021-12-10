class ColorDT {
    constructor(divName) {
        this.divName = divName;
        new ResizeObserver(() => {this.onResize()}).observe(document.getElementById(divName));

        this.source = new Bokeh.ColumnDataSource({data:{
            url : [],
            x : [],
            y : [],
            sat: [],
            lum: [],
            chroma : [],
            hue : [],
            a: [], 
            b: [], 
            uuids: []
        }});

        this.segment_starts = [];

        this.plot = Bokeh.Plotting.figure({
            tools: "pan,wheel_zoom,box_zoom,reset,save",
            aspect_ratio: 2,
            x_axis_type: "datetime",
        });

        let args = {
            seconds:['%Ss'], minsec:["%M:%S"], hours:["%Hh"], hourmin:["%H:%M:%S"], months:["%H:%M:%S"], days:['%Ss'], years:["%H:%M:%S"]
        }
        let f = new Bokeh.DatetimeTickFormatter(args)
        this.plot.below[0].formatter = f;
        this.plot.below[0].axis_label = "Time";

        this.plot.add_layout(new Bokeh.LinearAxis(), "below");
        this.plot.below[1].axis_label = "Start of Segment [ID]";

        this.plot.add_layout(new Bokeh.Grid(), "center");
        
        this.plot.center[0].grid_line_alpha = 0.3;
        this.plot.center[1].grid_line_alpha = 0.3;
        this.plot.center[2].grid_line_alpha = 0.3;

        this.aspect = 9.0 / 16

        this.lineRenderer = this.plot.line({x: { field: "x" }, y: { field: "y" }, line_alpha:0.7, line_width:2, source: this.source});

        this.border_renderer = this.plot.rect({
            x: { field: "x" },
            y: { field: "y" },
            fill_color: "transparent",
            line_width: 2,
            source:this.source,
        });

        this.glyph_renderer = this.plot.image_url({
            url: { field: "url" },
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
    setImageSize(s){
        this.glyph_renderer.glyph.h = s * this.aspect;
        this.glyph_renderer.glyph.w = s;
        this.glyph_renderer.glyph.h.units = "screen";
        this.glyph_renderer.glyph.w.units = "screen";

        this.border_renderer.glyph.height = s * this.aspect;
        this.border_renderer.glyph.width = s;
        this.border_renderer.glyph.height.units = "screen";
        this.border_renderer.glyph.width.units = "screen";

        this.source.change.emit();
    }

    setBackgroundColor(back, front) {
        let background = "rgb(" + back + "," + back + "," + back + ")";
        let foreground = "rgb(" + front + "," + front + "," + front + ")";

        this.plot.background_fill_color = background;
        this.plot.border_fill_color = background;

        this.border_renderer.glyph.line_color = foreground;

        this.plot.center[0].grid_line_color = foreground; //parallel to y-axis
        this.plot.center[1].grid_line_color = foreground;
        this.plot.center[2].grid_line_color = foreground;

        this.lineRenderer.glyph.line_color = foreground;

        this.plot.xaxis[0].axis_line_color = foreground;
        this.plot.xaxis[0].major_tick_line_color = foreground;
        this.plot.xaxis[0].minor_tick_line_color = foreground;
        this.plot.xaxis[0].axis_label_text_color = foreground;
        this.plot.xaxis[0].major_label_text_color = foreground;
        this.plot.xaxis[1].axis_line_color = foreground;
        this.plot.xaxis[1].major_tick_line_color = foreground;
        this.plot.xaxis[1].minor_tick_line_color = foreground;
        this.plot.xaxis[1].axis_label_text_color = foreground;
        this.plot.xaxis[1].major_label_text_color = foreground;
        this.plot.yaxis[0].axis_line_color = foreground;
        this.plot.yaxis[0].major_tick_line_color = foreground;
        this.plot.yaxis[0].minor_tick_line_color = foreground;
        this.plot.yaxis[0].axis_label_text_color = foreground;
        this.plot.yaxis[0].major_label_text_color = foreground;
        this.plot.outline_line_color = foreground;
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
                if (that.source.data.x.length != e.data.time.length) {
                    let time = []
                    for (var i = 0; i < e.data.time.length; i++){
                        time.push(new Date(e.data.time[i]))
                    }

                    that.source.data.x = e.data.time;
                    that.source.data.y = e.data.luminance;

                    that.source.data.sat = e.data.saturation;
                    that.source.data.lum = e.data.luminance;
                    that.source.data.chroma = e.data.chroma;
                    that.source.data.hue = e.data.hue;

                    that.source.data.a = e.data.a;
                    that.source.data.b = e.data.b;

                    that.source.data.url = e.data.urls
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

    setData(times, luminance, saturation, chroma, hue, a, b, urls, uuids, segment_starts, segment_ids){
        //console.log(uuids);

        let time = []
        for (var i = 0; i < times.length; i++){
            time.push(new Date(times[i]))
        }
        //console.log(this.source)

        this.source.data.x = time;
        this.source.data.y = luminance;

        this.source.data.sat = saturation;
        this.source.data.lum = luminance;
        this.source.data.chroma = chroma;
        this.source.data.hue = hue;

        this.source.data.a = a;
        this.source.data.b = b;

        this.source.data.uuids = uuids;

        this.source.data.url = urls;
        this.segment_starts = segment_starts;
        this.segment_ids = segment_ids;
        this.source.change.emit();


        this.plot.xaxis[1].ticker = new Bokeh.FixedTicker({ticks:this.segment_starts});

        let res_dict = {};
        for (var i = 0; i < this.segment_ids.length; i++){
            res_dict[this.segment_starts[i]] = this.segment_ids[i].toString();
        }
        //console.log(res_dict, this.segment_starts, segment_ids);
        this.plot.xaxis[1].major_label_overrides = res_dict;

        this.plot.center[2].ticker = new Bokeh.FixedTicker({ticks:this.segment_starts});
    }

    parameterChanged(value){

        var label = "";
        var values = null;
        switch (value){
            case "saturation":
                values = this.source.data.sat;
                label = "Saturation";
                break;
            case "chroma":
                values = this.source.data.chroma;
                label = "Chroma";
                break;
            case "hue":
                values = this.source.data.hue;
                label = "Hue";
                break;
            case "a-channel":
                values = this.source.data.a;
                label = "A-Channel";
                break;
            case "b-channel":
                values = this.source.data.b;
                label = "B-Channel";
                break;
            case "luminance":
                values = this.source.data.lum;
                label = "Luminance";
                break;
            default:
                throw "Channel not used";
                break;
        }

        this.plot.left[0].axis_label = label;
        this.source.data.y = values;
        this.source.change.emit();
    }

    xAxisOptionChanged(value){
        var label = "";
        switch (value){
            case "time":
                label = "Time";

                this.plot.below[0].visible = true;
                this.plot.below[1].visible = false;

                this.plot.center[0].visible = true;
                this.plot.center[2].visible = false;

                break;
            case "segments":
                label = "Start of Segment [ID]";

                this.plot.below[0].visible = false;
                this.plot.below[1].visible = true;

                this.plot.center[0].visible = false;
                this.plot.center[2].visible = true;
                break;
            default:
                throw "Option not available";
                break;
        }
    }

    showScreenshotBorders(show){
        if(show){
            this.border_renderer.glyph.line_alpha=1.0;
        }else{
            this.border_renderer.glyph.line_alpha=0.0;
        }
    }
    showConnectingLine(show){
        if(show){
            this.lineRenderer.glyph.line_alpha = 1.0;
        }else{
            this.lineRenderer.glyph.line_alpha = 0.0;
        }
    }

    onResize() {
        let elem = document.getElementById(this.divName)
        if (elem.clientHeight*this.plot.aspect_ratio > elem.clientWidth) {
            this.plot.sizing_mode = "scale_width"
        } else {
            this.plot.sizing_mode = "scale_height"
        }
    }

}
