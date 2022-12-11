/**
 * This file is part of Stable Diffusion Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

function loadData() {
    // rawData.ext/title/description
    for (var axis of rawData.axes) {
        // axis.id/title/description
        for (var val of axis.values) {
            // val.key/title/description
            document.getElementById('clicktab_' + axis.id + '__' + val.key).onclick = fillTable;
        }
        document.getElementById('x_' + axis.id).onclick = fillTable;
        document.getElementById('y_' + axis.id).onclick = fillTable;
        console.log(document.getElementById('x_' + axis.id))
    }
    console.log("Loaded data for '" + rawData.title + "'");
    document.getElementById('x_' + rawData.axes[0].id).click();
    document.getElementById('autoScaleImages').onchange = updateScaling;
    fillTable();
}

function fillTable() {
    var x = document.querySelector('input[name="x_axis_selector"]:checked').id.substring(2);
    var y = document.querySelector('input[name="y_axis_selector"]:checked').id.substring(2);
    var table = document.getElementById("image_table");
    var newContent = "<th>";
    var xAxis = null;
    var yAxis = null;
    for (var axis of rawData.axes) {
        if (axis.id == x) {
            xAxis = axis;
        }
        if (axis.id == y) {
            yAxis = axis;
        }
    }
    for (var val of xAxis.values) {
        newContent += "<td title=\"" + val.description.replaceAll('"', "&quot;") + "\">" + val.title + "</td>";
    }
    newContent += "</th>";
    for (var val of yAxis.values) {
        newContent += "<tr><td title=\"" + val.description.replaceAll('"', "&quot;") + "\">" + val.title + "</td>";
        var url = "";
        for (var subAxis of rawData.axes) {
            if (subAxis.id == x) {
                url += "/{X}"
            }
            else if (subAxis.id == y) {
                url += "/" + val.key;
            }
            else {
                var valSelectedKey;
                for (var subVal of subAxis.values) {
                    if (window.getComputedStyle(document.getElementById('tab_' + subAxis.id + '__' + subVal.key)).display != "none") {
                        valSelectedKey = subVal.key;
                    }
                }
                url += "/" + valSelectedKey;
            }
        }
        for (var xVal of xAxis.values) {
            newContent += "<td><img class=\"table_img\" src=\"" + url.replace("{X}", xVal.key).substring(1) + "." + rawData.ext + "\" /></td>";
        }
        newContent += "</tr>";
        if (x == y) {
            break;
        }
    }
    table.innerHTML = newContent;
    updateScaling();
}

function updateScaling() {
    var percent;
    if (document.getElementById('autoScaleImages').checked) {
        var x = document.querySelector('input[name="x_axis_selector"]:checked').id.substring(2);
        for (var axis of rawData.axes) {
            if (axis.id == x) {
                xAxis = axis;
            }
        }
        percent = (90 / xAxis.values.length) + "vw";
    }
    else {
        percent = "";
    }
    for (var image of document.getElementById("image_table").getElementsByClassName("table_img")) {
        image.style.width = percent;
    }
}

loadData();
