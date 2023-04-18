/**
 * This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

'use strict';

function loadData() {
    document.getElementById('x_' + rawData.axes[0].id).click();
    document.getElementById('x2_none').click();
    document.getElementById('y2_none').click();
    // rawData.ext/title/description
    for (var axis of rawData.axes) {
        // axis.id/title/description
        for (var val of axis.values) {
            // val.key/title/description/show
            var clicktab = document.getElementById('clicktab_' + axis.id + '__' + val.key);
            clicktab.addEventListener('click', fillTable);
            if (!val.show) {
                document.getElementById('showval_' + axis.id + '__' + val.key).checked = false;
                clicktab.classList.add('tab_hidden');
            }
        }
        for (var prefix of ['x_', 'y_', 'x2_', 'y2_']) {
            document.getElementById(prefix + axis.id).addEventListener('click', fillTable);
        }
        for (var label of ['x2_none', 'y2_none']) {
            document.getElementById(label).addEventListener('click', fillTable);
        }
    }
    console.log(`Loaded data for '${rawData.title}'`);
    document.getElementById('autoScaleImages').addEventListener('change', updateScaling);
    document.getElementById('stickyNavigation').addEventListener('change', toggleTopSticky);
    document.getElementById('toggle_nav_button').addEventListener('click', updateTitleSticky);
    fillTable();
    startAutoScroll();
    document.getElementById('showDescriptions').checked = rawData.defaults.show_descriptions;
    document.getElementById('autoScaleImages').checked = rawData.defaults.autoscale;
    document.getElementById('stickyNavigation').checked = rawData.defaults.sticky;
    for (var axis of ['x', 'y', 'x2', 'y2']) {
        if (rawData.defaults[axis] !== '') {
            console.log('find ' + axis + '_' + rawData.defaults[axis]);
            document.getElementById(axis + '_' + rawData.defaults[axis]).click();
        }
    }
}

function getAxisById(id) {
    for (var axis of rawData.axes) {
        if (axis.id === id) {
            return axis;
        }
    }
}

function getNextAxis(axes, startId) {
    var next = false;
    for (var subAxis of axes) {
        if (subAxis.id === startId) {
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
        if (window.getComputedStyle(document.getElementById('tab_' + axis.id + '__' + subVal.key)).display !== 'none') {
            return subVal.key;
        }
    }
    return null;
}

var popoverLastImg = null;

function clickRowImage(rows, x, y) {
    $('#image_info_modal').modal('hide');
    var columns = rows[y].getElementsByTagName('td');
    columns[x].getElementsByTagName('img')[0].click();
}

window.addEventListener('keydown', function (kbevent) {
    if ($('#image_info_modal').is(':visible')) {
        if (kbevent.key === 'Escape') {
            $('#image_info_modal').modal('toggle');
            kbevent.preventDefault();
            kbevent.stopPropagation();
            return false;
        }
        var tableElem = document.getElementById('image_table');
        var rows = tableElem.getElementsByTagName('tr');
        var matchedRow = null;
        var x = 0, y = 0;
        for (var row of rows) {
            var columns = row.getElementsByTagName('td');
            for (var column of columns) {
                var images = column.getElementsByTagName('img');
                if (images.length === 1 && images[0] === popoverLastImg) {
                    matchedRow = row;
                    break;
                }
                x++;
            }
            if (matchedRow != null) {
                break;
            }
            x = 0;
            y++;
        }
        if (matchedRow == null) {
            return;
        }
        if (kbevent.key === 'ArrowLeft') {
            if (x > 1) {
                x--;
                clickRowImage(rows, x, y);
            }
        }
        else if (kbevent.key === 'ArrowRight') {
            x++;
            var columns = matchedRow.getElementsByTagName('td');
            if (columns.length > x) {
                clickRowImage(rows, x, y);
            }
        }
        else if (kbevent.key === 'ArrowUp') {
            if (y > 1) {
                y--;
                clickRowImage(rows, x, y);
            }
        }
        else if (kbevent.key === 'ArrowDown') {
            y++;
            if (rows.length > y) {
                clickRowImage(rows, x, y);
            }
        }
        else {
            return;
        }
        kbevent.preventDefault();
        kbevent.stopPropagation();
        return false;
    }
    var elem = document.activeElement;
    if (!elem.id.startsWith('clicktab_')) {
        return;
    }
    var axisId = elem.id.substring('clicktab_'.length);
    var splitIndex = axisId.indexOf('__');
    axisId = axisId.substring(0, splitIndex);
    var axis = getAxisById(axisId);
    if (kbevent.key === 'ArrowLeft') {
        var tabPage = document.getElementById('tablist_' + axis.id);
        var tabs = tabPage.getElementsByClassName('nav-link');
        var newTab = clickTabAfterActiveTab([].slice.call(tabs).reverse());
        newTab.focus();
    }
    else if (kbevent.key === 'ArrowRight') {
        var tabPage = document.getElementById('tablist_' + axis.id);
        var tabs = tabPage.getElementsByClassName('nav-link');
        var newTab = clickTabAfterActiveTab(tabs);
        newTab.focus();
    }
    else if (kbevent.key === 'ArrowUp') {
        var next = getNextAxis(rawData.axes.slice().reverse(), axisId);
        if (next != null) {
            var selectedKey = getSelectedValKey(next);
            var swapToTab = this.document.getElementById(`clicktab_${next.id}__${selectedKey}`);
            swapToTab.focus();
        }
    }
    else if (kbevent.key === 'ArrowDown') {
        var next = getNextAxis(rawData.axes, axisId);
        if (next != null) {
            var selectedKey = getSelectedValKey(next);
            var swapToTab = this.document.getElementById(`clicktab_${next.id}__${selectedKey}`);
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

function canShowVal(axis, val) {
    return document.getElementById(`showval_${axis}__${val}`).checked;
}

function getXAxisContent(x, y, xAxis, val, x2Axis, x2val, y2Axis, y2val) {
    var imgPath = [];
    var index = 0;
    for (var subAxis of rawData.axes) {
        if (subAxis.id === x) {
            index = imgPath.length;
            imgPath.push(null);
        }
        else if (subAxis.id === y) {
            imgPath.push(val.key);
        }
        else if (x2Axis != null && subAxis.id === x2Axis.id) {
            imgPath.push(x2val.key);
        }
        else if (y2Axis != null && subAxis.id === y2Axis.id) {
            imgPath.push(y2val.key);
        }
        else {
            imgPath.push(getSelectedValKey(subAxis));
        }
    }
    var newContent = '';
    for (var xVal of xAxis.values) {
        if (canShowVal(xAxis.id, xVal.key)) {
            imgPath[index] = xVal.key;
            var actualUrl = imgPath.join('/') + '.' + rawData.ext;
            newContent += `<td><img class="table_img" data-img-path="${escapeHtml(imgPath.join(','))}" onclick="doPopupFor(this)" onerror="setImgPlaceholder(this)" src="${actualUrl}" alt="${actualUrl}" /></td>`;
        }
    }
    return newContent;
}

// Public function
function setImgPlaceholder(img) {
    img.onerror = undefined;
    img.src = './placeholder.png';
}

function optDescribe(isFirst, val) {
    return isFirst && val != null ? '<span title="' + escapeHtml(val.description) + '"><b>' + val.title + '</b></span><br>' : (val != null ? '<br>' : '');
}

function fillTable() {
    var x = getCurrentSelectedAxis('x');
    var y = getCurrentSelectedAxis('y');
    var x2 = getCurrentSelectedAxis('x2');
    var y2 = getCurrentSelectedAxis('y2');
    console.log('Do fill table, x=' + x + ', y=' + y + ', x2=' + x2 + ', y2=' + y2);
    var xAxis = getAxisById(x);
    var yAxis = getAxisById(y);
    var x2Axis = x2 === 'None' || x2 === x || x2 === y ? null : getAxisById(x2);
    var y2Axis = y2 === 'None' || y2 === x2 || y2 === x || y2 === y ? null : getAxisById(y2);
    var table = document.getElementById('image_table');
    var newContent = '<tr id="image_table_header" class="sticky_top"><th></th>';
    var superFirst = true;
    for (var x2val of (x2Axis == null ? [null] : x2Axis.values)) {
        if (x2val != null && !canShowVal(x2Axis.id, x2val.key)) {
            continue;
        }
        var x2first = true;
        for (var val of xAxis.values) {
            if (!canShowVal(xAxis.id, val.key)) {
                continue;
            }
            newContent += `<th${(superFirst ? '' : ' class="superaxis_second"')} title="${val.description.replaceAll('"', "&quot;")}">${optDescribe(x2first, x2val)}${val.title}</th>`;
            x2first = false;
        }
        superFirst = !superFirst;
    }
    newContent += '</tr>';
    superFirst = true;
    for (var y2val of (y2Axis == null ? [null] : y2Axis.values)) {
        if (y2val != null && !canShowVal(y2Axis.id, y2val.key)) {
            continue;
        }
        var y2first = true;
        for (var val of yAxis.values) {
            if (!canShowVal(yAxis.id, val.key)) {
                continue;
            }
            newContent += `<tr><td class="axis_label_td${(superFirst ? '' : ' superaxis_second')}" title="${escapeHtml(val.description)}">${optDescribe(y2first, y2val)}${val.title}</td>`;
            y2first = false;
            for (var x2val of (x2Axis == null ? [null] : x2Axis.values)) {
                if (x2val != null && !canShowVal(x2Axis.id, x2val.key)) {
                    continue;
                }
                newContent += getXAxisContent(x, y, xAxis, val, x2Axis, x2val, y2Axis, y2val);
            }
            newContent += '</tr>';
            if (x === y) {
                break;
            }
        }
        superFirst = !superFirst;
    }
    table.innerHTML = newContent;
    updateScaling();
}

function getCurrentSelectedAxis(axisPrefix) {
    var id = document.querySelector(`input[name="${axisPrefix}_axis_selector"]:checked`).id;
    var index = id.indexOf('_');
    return id.substring(index + 1);
}

function updateScaling() {
    var percent;
    if (document.getElementById('autoScaleImages').checked) {
        var x = getCurrentSelectedAxis('x');
        var xAxis = getAxisById(x);
        var count = xAxis.values.length;
        var x2 = getCurrentSelectedAxis('x2');
        if (x2 !== 'none') {
            var x2Axis = getAxisById(x2);
            count *= x2Axis.values.length;
        }
        percent = (90 / count) + 'vw';
    }
    else {
        percent = '';
    }
    for (var image of document.getElementById('image_table').getElementsByClassName('table_img')) {
        image.style.width = percent;
    }
    updateTitleSticky();
}

// Public function
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

// Public function
function toggleShowAllAxis(axisId) {
    var axis = getAxisById(axisId);
    var any = false;
    for (var val of axis.values) {
        any = canShowVal(axisId, val.key);
        if (any) {
            break;
        }
    }
    for (var val of axis.values) {
        document.getElementById('showval_' + axisId + '__' + val.key).checked = !any;
        var element = document.getElementById('clicktab_' + axisId + '__' + val.key);
        element.classList.remove('tab_hidden'); // Remove either way to guarantee no duplication
        if (any) {
            element.classList.add('tab_hidden');
        }
    }
    fillTable();
}

// Public function
function toggleShowVal(axis, val) {
    var show = canShowVal(axis, val);
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
    };
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

// Public function
function doPopupFor(img) {
    popoverLastImg = img;
    var imgPath = unescapeHtml(img.dataset.imgPath).split(',');
    var modalElem = document.getElementById('image_info_modal');
    var metaText = window.crunchMetadata(imgPath);
    var params = escapeHtml(metaText).replaceAll('\n', '\n<br>');
    var text = 'Image: ' + img.alt + (params.length > 1 ? ', parameters: <br>' + params : '<br>(parameters hidden)');
    modalElem.innerHTML = `<div class="modal-dialog" style="display:none">(click outside image to close)</div><div class="modal_inner_div"><img class="popup_modal_img" src="${img.src}"><br><div class="popup_modal_undertext">${text}</div>`;
    $('#image_info_modal').modal('toggle');
}

function updateTitleStickyDirect() {
    var height = Math.round(document.getElementById('top_nav_bar').getBoundingClientRect().height);
    var header = document.getElementById('image_table_header');
    if (header.style.top !== height + 'px') { // This check is to reduce the odds of the browser yelling at us
        header.style.top = height + 'px';
    }
}

function updateTitleSticky() {
    var topBar = document.getElementById('top_nav_bar');
    if (!topBar.classList.contains('sticky_top')) {
        document.getElementById('image_table_header').style.top = '0';
        return;
    }
    // client rect is dynamically animated, so, uh, just hack it for now.
    // TODO: Actually smooth attachment.
    var rate = 50;
    for (var time = 0; time <= 500; time += rate) {
        setTimeout(updateTitleStickyDirect, time);
    }
}

function toggleTopSticky() {
    var topBar = document.getElementById('top_nav_bar');
    if (topBar.classList.contains('sticky_top')) {
        topBar.classList.remove('sticky_top');
    }
    else {
        topBar.classList.add('sticky_top');
    }
    updateTitleSticky();
}

loadData();
