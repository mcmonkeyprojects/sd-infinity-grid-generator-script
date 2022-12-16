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
    startAutoScroll();
}

function escapeHtml(text) {
    return text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}

function unescapeHtml(text) {
    return text.replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&quot;', '"').replaceAll('&#039;', "'").replaceAll('&amp;', '&');
}

function fillTable() {
    var x = document.querySelector('input[name="x_axis_selector"]:checked').id.substring(2);
    var y = document.querySelector('input[name="y_axis_selector"]:checked').id.substring(2);
    var table = document.getElementById('image_table');
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
        newContent += '<td title="' + val.description.replaceAll('"', "&quot;") + '">' + val.title + '</td>';
    }
    newContent += "</th>";
    for (var val of yAxis.values) {
        newContent += '<tr><td title="' + val.description.replaceAll('"', '&quot;') + '">' + val.title + '</td>';
        var url = "";
        for (var subAxis of rawData.axes) {
            if (subAxis.id == x) {
                url += '/{X}';
            }
            else if (subAxis.id == y) {
                url += '/' + val.key;
            }
            else {
                var valSelectedKey;
                for (var subVal of subAxis.values) {
                    if (window.getComputedStyle(document.getElementById('tab_' + subAxis.id + '__' + subVal.key)).display != 'none') {
                        valSelectedKey = subVal.key;
                    }
                }
                url += '/' + valSelectedKey;
            }
        }
        for (var xVal of xAxis.values) {
            var actualUrl = url.replace('{X}', xVal.key).substring(1) + '.' + rawData.ext;
            newContent += '<td><img class="table_img" id="autogen_img_' + escapeHtml(actualUrl).replace(' ', '%20') + '" onclick="doPopupFor(this)" src="' + actualUrl + '" /></td>';
        }
        newContent += '</tr>';
        if (x == y) {
            break;
        }
    }
    table.innerHTML = newContent;
    updateScaling();
}

function updateScaling() {
    var percent;
    var xAxis;
    if (document.getElementById('autoScaleImages').checked) {
        var x = document.querySelector('input[name="x_axis_selector"]:checked').id.substring(2);
        for (var axis of rawData.axes) {
            if (axis.id == x) {
                xAxis = axis;
            }
        }
        percent = (90 / xAxis.values.length) + 'vw';
    }
    else {
        percent = "";
    }
    for (var image of document.getElementById('image_table').getElementsByClassName('table_img')) {
        image.style.width = percent;
    }
}

function toggleDescriptions() {
    var show = document.getElementById('showDescriptions').checked;
    for (var cName of ['tabval_subdiv', 'axis_table_cell']) {
        for (var elem of document.getElementsByClassName(cName)) {
            elem.style.display = show ? 'block' : 'none';
        }
    }
}

var anyRangeActive = false;

function toggleTimers() {
    var show = document.getElementById('showTimers').checked;
    if (!show) {
        anyRangeActive = false;
    }
    for (var elem of document.getElementsByClassName('timer_box')) {
        elem.style.display = show ? 'block' : 'none';
    }
}

const timer = ms => new Promise(res => setTimeout(res, ms));

function enableRange(id) {
    var range = document.getElementById('range_tablist_' + id);
    var label = document.getElementById('label_range_tablist_' + id);
    range.oninput = function() {
        anyRangeActive = true;
        label.innerText = (range.value/2) + ' seconds';
    }
    var data = {};
    data.range = range;
    data.counter = 0;
    data.id = id;
    data.tabPage = document.getElementById('tablist_' + id);
    data.tabs = data.tabPage.getElementsByClassName('nav-link');
    return data;
}

async function startAutoScroll() {
    var rangeSet = [];
    for (var axis of rawData.axes) {
        rangeSet.push(enableRange(axis.id));
    }
    while (true) {
        await timer(500);
        if (!anyRangeActive) {
            continue;
        }
        for (var data of rangeSet) {
            if (data.range.value <= 0) {
                continue;
            }
            data.counter++;
            if (data.counter < data.range.value) {
                continue;
            }
            data.counter = 0;
            var next = false;
            for (var tab of data.tabs) {
                if (next) {
                    tab.click();
                    next = false;
                    break;
                }
                if (tab.classList.contains('active')) {
                    next = true;
                }
            }
            if (next) {
                data.tabs[0].click();
            }
        }
    }
}

function doPopupFor(img) {
    console.log("popup for " + img);
    var modalElem = document.getElementById('image_info_modal');
    var url = img.id.substring('autogen_img_'.length);
    var text = 'Image: ' + url + '<br>';
    modalElem.innerHTML = '<div class="modal-dialog" onclick="javascript:$(\'#image_info_modal\').modal(\'hide\');">(click outside image to close)</div><div class="modal_inner_div"><img class="popup_modal_img" src="' + unescapeHtml(url) + '"><br><div class="popup_modal_undertext">' + text + '</div>';
    $('#image_info_modal').modal('toggle');
}

loadData();
