// create a data source to hold data
var source = new Bokeh.ColumnDataSource({
    data: { x: [], y: [] }
});

// make a plot with some tools
var plot = Bokeh.Plotting.figure({
    title:'Example of Random data',
    tools: "pan,wheel_zoom,box_zoom,reset,save",
    height: 300,
    width: 300
});

// add a line with data from the source
plot.line({ field: "x" }, { field: "y" }, {
    source: source,
    line_width: 2
});

plot.sizing_mode = "scale_height"
console.log(plot)
// show the plot, appending it to the end of the current section
Bokeh.Plotting.show(plot);

function addPoint() {
    // add data --- all fields must be the same length.
    source.data.x.push(Math.random())
    source.data.y.push(Math.random())

    // notify the DataSource of "in-place" changes
    source.change.emit()
}

var addDataButton = document.createElement("Button");
addDataButton.appendChild(document.createTextNode("Add Some Data!!!"));
document.currentScript.parentElement.appendChild(addDataButton);
addDataButton.addEventListener("click", addPoint);

addPoint();
addPoint();
