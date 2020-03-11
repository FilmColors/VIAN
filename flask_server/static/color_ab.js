// create a data source to hold data
class ColorAB {
    constructor(divName) {
        this.divName = divName;
        this.grid_col = "rgb(255,255,255)"
        this.background = "rgb(17,17,17)"

        this.source = new Bokeh.ColumnDataSource({
            data: { x: [], y: [], image: [] }
        });

        this.plot = Bokeh.Plotting.figure({
            title: 'Color CIE-Lab (AB - Plane)',
            tools: "pan,wheel_zoom,box_zoom,reset,save",
            height: 300,
            width: 300,
            x_range: new Bokeh.Range1d({ start: -128, end: 128 }),
            y_range: new Bokeh.Range1d({ start: -128, end: 128 })
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
            global_alpha: 0.2,
            source: this.source
            });
        r.glyph.h.units = "screen"
        r.glyph.w.units = "screen"

        console.log(r)

        this.q = 20
        for (var i = 0; i < 10; i++) {
            this.plot.circle({ x: 0, y: 0, radius: i * this.q, fill_alpha: 0, line_color: this.grid_col, line_alpha: 0.2, line_width: 1.0 })
        }
        var doc = new Bokeh.Document();
        doc.add_root(this.plot);
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
                if (e.changes || that.source.data.x.length == 0) {
                    that.source.data.x = e.data.a;
                    that.source.data.y = e.data.b;
                    that.source.data.image = e.data.urls
                }
            },
            error: function (error, timeout) {
                console.log(error);
            }
            complete: function(){
                setTimeout(function(){that.poll(pollTime); }, pollTime);
            }
        });

    }
}

// // Define a new component called button-counter
// function pollAB(timeout){
//     $.ajax({
//                 type: 'GET',
//                 contentType: 'application/json',
//                 dataType: 'json',
//                 url: "/screenshot-data/",
//                 success: function (e) {
//                     if (e.changes || source.data.x.length == 0){
//                         source.data.x = e.data.a;
//                         source.data.y = e.data.b;
//                         source.data.image = e.data.url
//                         source.change.emit()
//                     }


//                     setTimeout(function(){ pollAB(timeout) ;}, timeout)
//                 },
//                 error: function (error, timeout) {
//                     console.log(error);
//                     setTimeout(function(){
//                         setTimeout(function(){ pollAB(timeout); }, timeout)
//                     }, timeout)
//                 }
//     })
// }

// var source = new Bokeh.ColumnDataSource({
//     data: { x: [], y: [], image: [] }
// });

// // make a plot with some tools
// var plot = Bokeh.Plotting.figure({
//     title:'Color CIE-Lab (AB - Plane)',
//     tools: "pan,wheel_zoom,box_zoom,reset,save",
//     height: 300,
//     width: 300,
//     x_range: new Bokeh.Range1d({ start: -128, end: 128 }),
//     y_range: new Bokeh.Range1d({ start: -128, end: 128 })
// });

// grid_col = "rgb(255,255,255)"
// background = "rgb(17,17,17)"

// plot.center[0].grid_line_alpha = 0.0
// plot.center[1].grid_line_alpha = 0.0

// plot.background_fill_color = background
// plot.background_fill_alpha = 0.0
// plot.border_fill_alpha = 0.0
// plot.sizing_mode = "scale_width"
// aspect = 9.0 / 16

// plot.image_url({ field:"image"}, { field: "x" }, { field: "y" },
//      dw = 10,
//      dh = 10 * aspect,
//      dw_units ="screen",
//      dh_units ="screen",
//      anchor="center",
//      global_alpha=0.2,
//      {
//     source: source
// });

// q = 20
// for (var i = 0; i < 10; i++){
// console.log(i * q)
//     plot.circle({x:0, y:0, radius: i * q, fill_alpha: 0, line_color: grid_col, line_alpha: 0.2, line_width: 1.0})
// }


// var doc = new Bokeh.Document();
// doc.add_root(plot);
// Bokeh.embed.add_document_standalone(doc, document.getElementById("ab-color"));

// pollAB(1000);