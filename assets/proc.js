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

function getAxisById(id) {
    for (var axis of rawData.axes) {
        if (axis.id == id) {
            return axis;
        }
    }
}

function getNextAxis(axes, startId) {
    var next = false;
    for (var subAxis of axes) {
        if (subAxis.id == startId) {
            next = true;
        }
        else if (next) {
            return subAxis;
        }
    }
    return null;
}

function getSelectedValKey(axis) {
    for (var subVal of axis.values) {
        if (window.getComputedStyle(document.getElementById('tab_' + axis.id + '__' + subVal.key)).display != 'none') {
            return subVal.key;
        }
    }
    return null;
}

window.addEventListener('keydown', function(kbevent) {
    var elem = document.activeElement;
    if (!elem.id.startsWith('clicktab_')) {
        return;
    }
    var axisId = elem.id.substring('clicktab_'.length);
    var splitIndex = axisId.indexOf('__');
    axisId = axisId.substring(0, splitIndex);
    var axis = getAxisById(axisId);
    if (kbevent.key == "ArrowLeft") {
        var tabPage = document.getElementById('tablist_' + axis.id);
        var tabs = tabPage.getElementsByClassName('nav-link');
        var newTab = clickTabAfterActiveTab([].slice.call(tabs).reverse());
        newTab.focus();
    }
    else if (kbevent.key == "ArrowRight") {
        var tabPage = document.getElementById('tablist_' + axis.id);
        var tabs = tabPage.getElementsByClassName('nav-link');
        var newTab = clickTabAfterActiveTab(tabs);
        newTab.focus();
    }
    else if (kbevent.key == "ArrowUp") {
        var next = getNextAxis(rawData.axes.slice().reverse(), axisId);
        if (next != null) {
            var selectedKey = getSelectedValKey(next);
            var swapToTab = this.document.getElementById('clicktab_' + next.id + '__' + selectedKey);
            swapToTab.focus();
        }
    }
    else if (kbevent.key == "ArrowDown") {
        var next = getNextAxis(rawData.axes, axisId);
        if (next != null) {
            var selectedKey = getSelectedValKey(next);
            var swapToTab = this.document.getElementById('clicktab_' + next.id + '__' + selectedKey);
            swapToTab.focus();
        }
    }
    else {
        return;
    }
    kbevent.preventDefault();
    kbevent.stopPropagation();
    return false;
}, true);

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
    var xAxis = getAxisById(x);
    var yAxis = getAxisById(y);
    for (var val of xAxis.values) {
        if (!document.getElementById('showval_' + xAxis.id + '__' + val.key).checked) {
            continue;
        }
        newContent += '<th title="' + val.description.replaceAll('"', "&quot;") + '">' + val.title + '</th>';
    }
    newContent += "</th>";
    for (var val of yAxis.values) {
        if (!document.getElementById('showval_' + yAxis.id + '__' + val.key).checked) {
            continue;
        }
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
                url += '/' + getSelectedValKey(subAxis);
            }
        }
        for (var xVal of xAxis.values) {
            if (!document.getElementById('showval_' + xAxis.id + '__' + xVal.key).checked) {
                continue;
            }
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
        xAxis = getAxisById(x);
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
            if (show) {
                elem.classList.remove('tab_hidden');
            }
            else {
                elem.classList.add('tab_hidden');
            }
        }
    }
}

function toggleShowVal(axis, val) {
    var show = document.getElementById('showval_' + axis + '__' + val).checked;
    var element = document.getElementById('clicktab_' + axis + '__' + val);
    if (show) {
        element.classList.remove('tab_hidden');
    }
    else {
        element.classList.add('tab_hidden');
    }
    fillTable();
}

var anyRangeActive = false;

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

function clickTabAfterActiveTab(tabs) {
    var next = false;
    for (var tab of tabs) {
        if (tab.classList.contains('active')) {
            next = true;
        }
        else if (tab.classList.contains('tab_hidden')) {
            // Skip past
        }
        else if (next) {
            tab.click();
            return tab;
        }
    }
    if (next) { // Click the first non-hidden
        for (var tab of tabs) {
            if (tab.classList.contains('tab_hidden')) {
                // Skip past
            }
            else {
                tab.click();
                return tab;
            }
        }
    }
    return null;
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
            clickTabAfterActiveTab(data.tabs);
        }
    }
}

function genParamQuote(text) {
    // Referenced to match generation_parameters_copypaste.py - quote(text)
    if (!text.includes(',')) {
        return text;
    }
    return '"' + text.toString().replaceAll('\\', '\\\\').replaceAll('"', '\\"') + '"';
}

function formatMet(name, val, bad) {
    if (val == null) {
        return "";
    }
    val = val.toString();
    if (bad !== undefined && val == bad) {
        return "";
    }
    return name + ": " + genParamQuote(val) + ", "
}

function formatMetadata(valSet) {
    var count = Object.keys(valSet).length;
    if (count == 0) {
        return "";
    }
    else if (count == 1) {
        return valSet["error"];
    }
    // Referenced to match processing.py - create_infotext(p)
    var negative = valSet["negativeprompt"];
    if (negative.length > 0) {
        negative = "\nNegative prompt: " + negative;
    }
    // Keys we have but gen-param doesn't: VAE, sigma(churn/tmin/tmax/noise)
    var keyData = formatMet("Steps", valSet["steps"])
        + formatMet("Sampler", valSet["sampler"])
        + formatMet("CFG scale", valSet["cfgscale"])
        + formatMet("Seed", valSet["seed"])
        // face restore
        + formatMet("Size", valSet["width"] + "x" + valSet["height"])
        // model hash
        + formatMet("Model", valSet["model"])
        + formatMet("Hypernet", valSet["hypernetwork"], "none")
        + formatMet("Hypernet strength", valSet["hypernetworkstrength"], "none")
        // Batch size, batch pos
        + formatMet("Variation seed", valSet["varseed"], "0")
        + formatMet("Variation seed strength", valSet["varstrength"], "0")
        // Seed resize from
        + formatMet("Denoising strength", valSet["denoising"])
        // Conditional mask weight
        + formatMet("Eta", valSet["eta"])
        + formatMet("Clip skip", valSet["clipskip"], "1")
        // ENSD
        ;
    keyData = keyData.substring(0, keyData.length - 2);
    return valSet["prompt"] + negative + "\n" + keyData;
}

function crunchMetadata(url) {
    if (!('metadata' in rawData)) {
        return {};
    }
    initialData = rawData.metadata;
    var index = 0;
    for (var part of url.substring(0, url.indexOf('.')).split('/')) {
        var axis = rawData.axes[index++];
        var actualVal = null;
        for (var val of axis.values) {
            if (val.key == part) {
                actualVal = val;
                break;
            }
        }
        if (actualVal == null) {
            return { "error": "metadata parsing failed for part " + index + ": " + part };
        }
        for (var [key, value] of Object.entries(actualVal.params)) {
            if (key.replaceAll(' ', '') == "promptreplace") {
                var replacers = value.split('=', 2);
                var match = replacers[0].trim();
                var replace = replacers[1].trim();
                initialData["prompt"] = initialData["prompt"].replaceAll(match, replace);
                initialData["negativeprompt"] = initialData["negativeprompt"].replaceAll(match, replace);
            }
            else {
                initialData[key] = value;
            }
        }
    }
    return initialData;
}

function doPopupFor(img) {
    var modalElem = document.getElementById('image_info_modal');
    var url = img.id.substring('autogen_img_'.length);
    var params = escapeHtml(formatMetadata(crunchMetadata(unescapeHtml(url)))).replaceAll("\n", "\n<br>");
    var text = 'Image: ' + url + (params.length > 1 ? ', parameters: <br>' + params : '<br>(parameters hidden)');
    modalElem.innerHTML = '<div class="modal-dialog" style="display:none">(click outside image to close)</div><div class="modal_inner_div"><img class="popup_modal_img" src="' + unescapeHtml(url) + '"><br><div class="popup_modal_undertext">' + text + '</div>';
    $('#image_info_modal').modal('toggle');
}

loadData();
