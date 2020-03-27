// create a data source to hold data

class ColorDT {
    constructor(divName) {

        this.divName = divName;
        this.grid_col = "rgb(255,255,255)"
        this.background = "rgb(17,17,17)"

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
            // scene_ids : [],
        }});

        this.menu = [("Saturation", "Saturation"), ("Chroma", "Chroma"), ("Hue", "Hue"), ("Luminance", "Luminance"), ("A-Channel", "A-Channel"), ("B-Channel", "B-Channel")]
        this.dropdown = new Bokeh.Widgets.Dropdown({label:"Select Feature", button_type:"warning", menu:this.menu}) 

        var that = this;
        this.dropdown.change.connect(function(){that.parameterChanged(that.source, that.dropdown)})
        this.plot = Bokeh.Plotting.figure({
            title:'Color dT',
            tools: "pan,wheel_zoom,box_zoom,reset,save",
            height: 500,
            width: 1200,
            x_axis_type: "datetime",
            y_axis_label: "Saturation", 
        });

        

        this.plot.background_fill_color = this.background
        this.plot.background_fill_alpha = 0.0
        this.plot.border_fill_alpha = 0.0
        this.plot.center[0].grid_line_alpha = 0.3
        this.plot.center[1].grid_line_alpha = 0.3

        this.plot.sizing_mode = "scale_width"
        this.aspect = 9.0 / 16
        
        this.plot.below[0].axis_label = "Time"
        // seconds = ['%Ss']
        
        let args = {
            seconds: ['%Ss'],
            minsec: [':%M:%S'],
            minutes: [':%M', '%Mm'],
            hourmin: ['%H:%M'],
            hours: ['%Hh', '%H:%M']
        }
        args = {
            seconds:['%Ss'], minutes:["%H:%M:%S"], hours:["%H"], hourmin:["%H:%M:%S"],
                                                 months:["%H:%M:%S"], years:["%H:%M:%S"]
        }
        let f = new Bokeh.DatetimeTickFormatter(args)
        // console.log(f)

        this.plot.below[0].formatter = f;
        // this.plot.left[0]
       
        this.plot.line({x: { field: "x" }, y: { field: "y" }, line_color : "rgb(255,255,255)", line_alpha:0.2, source: this.source});

        var r = this.plot.image_url({url: { field: "url" },x: { field: "x" },y: { field: "y" },
            w: 20,
            h: 20 * this.aspect,
            anchor: "center",
            global_alpha: 0.8,
            source: this.source
            });
        r.glyph.h.units = "screen"
        r.glyph.w.units = "screen"
        
        console.log(this.plot);
        var doc = new Bokeh.Document();
        doc.add_root(new Bokeh.Column({children: [this.dropdown, this.plot], sizing_mode: "scale_width"}));
        Bokeh.embed.add_document_standalone(doc, document.getElementById(divName));
        this.source.change.emit()
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

    setBackgroundColor(r, g, b){
        let col = "rgb(" + r + "," + g + "," + b + ")";

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

    setData(times, luminance, saturation, chroma, hue, a, b, urls, uuids){
        let time = []
        for (var i = 0; i < times.length; i++){
            time.push(new Date(times[i]))
        }

        this.source.data.x =time;
        this.source.data.y = luminance;

        this.source.data.sat = saturation;
        this.source.data.lum = luminance;
        this.source.data.chroma =chroma;
        this.source.data.hue = hue;

        this.source.data.a = a;
        this.source.data.b = b;

        this.source.uuids = uuids;

        this.source.data.url = urls
        this.source.change.emit();
    }

    parameterChanged(source, dropdown){
        var t = dropdown.value;
        var values = null;
        if (t == "Saturation"){
            values = source.data.sat;
        }else if (t == "Chroma"){
            values = source.data.chroma
        }
        else if (t == "Hue"){
            values = source.data.hue
        }
        else if (t == "A-Channel"){
            values = source.data.a
        }
        else if (t == "B-Channel"){
            values = source.data.b
        }
        else {
            values = source.data.lum
        }
        source.data.y = values;
        source.change.emit()
    }

}
