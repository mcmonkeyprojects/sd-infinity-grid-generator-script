/**
 * This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

'use strict';

function loadData() {
    document.getElementById('x_' + rawData.axes[0].id).click();
    document.getElementById('x2_none').click();
    document.getElementById('y2_none').click();
    // rawData.ext/title/description
    for (const axis of rawData.axes) {
        // axis.id/title/description
        for (const val of axis.values) {
            // val.key/title/description/show
            const clicktab = document.getElementById('clicktab_' + axis.id + '__' + val.key);
            clicktab.addEventListener('click', fillTable);
            if (!val.show) {
                document.getElementById('showval_' + axis.id + '__' + val.key).checked = false;
                clicktab.classList.add('tab_hidden');
            }
        }
        for (const prefix of ['x_', 'y_', 'x2_', 'y2_']) {
            document.getElementById(prefix + axis.id).addEventListener('click', fillTable);
        }
        for (const label of ['x2_none', 'y2_none']) {
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
    for (const axis of ['x', 'y', 'x2', 'y2']) {
        if (rawData.defaults[axis] !== '') {
            console.log('find ' + axis + '_' + rawData.defaults[axis]);
            document.getElementById(axis + '_' + rawData.defaults[axis]).click();
        }
    }
}

function getAxisById(id) {
    return rawData.axes.find(axis => axis.id === id);
}

function getNextAxis(axes, startId) {
    let next = false;
    for (const subAxis of axes) {
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
    for (const subVal of axis.values) {
        if (window.getComputedStyle(document.getElementById('tab_' + axis.id + '__' + subVal.key)).display !== 'none') {
            return subVal.key;
        }
    }
    return null;
}

let popoverLastImg = null;

function clickRowImage(rows, x, y) {
    $('#image_info_modal').modal('hide');
    const columns = rows[y].getElementsByTagName('td');
    columns[x].getElementsByTagName('img')[0].click();
}

window.addEventListener('keydown', (kbevent) => {
    if ($('#image_info_modal').is(':visible')) {
        if (kbevent.key === 'Escape') {
            $('#image_info_modal').modal('toggle');
            kbevent.preventDefault();
            kbevent.stopPropagation();
            return false;
        }
        const tableElem = document.getElementById('image_table');
        const rows = tableElem.getElementsByTagName('tr');
        let matchedRow = null;
        let x = 0;
        let y = 0;
        for (const row of rows) {
            const columns = row.getElementsByTagName('td');
            for (const column of columns) {
                const images = column.getElementsByTagName('img');
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
            const columns = matchedRow.getElementsByTagName('td');
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
    const elem = document.activeElement;
    if (!elem.id.startsWith('clicktab_')) {
        return;
    }
    let axisId = elem.id.substring('clicktab_'.length);
    const splitIndex = axisId.lastIndexOf('__');
    axisId = axisId.substring(0, splitIndex);
    const axis = getAxisById(axisId);
    if (kbevent.key === 'ArrowLeft') {
        const tabPage = document.getElementById('tablist_' + axis.id);
        const tabs = tabPage.getElementsByClassName('nav-link');
        const newTab = clickTabAfterActiveTab(Array.from(tabs).reverse());
        newTab.focus();
    }
    else if (kbevent.key === 'ArrowRight') {
        const tabPage = document.getElementById('tablist_' + axis.id);
        const tabs = tabPage.getElementsByClassName('nav-link');
        const newTab = clickTabAfterActiveTab(tabs);
        newTab.focus();
    }
    else if (kbevent.key === 'ArrowUp') {
        const next = getNextAxis(Array.from(rawData.axes).reverse(), axisId);
        if (next != null) {
            const selectedKey = getSelectedValKey(next);
            const swapToTab = this.document.getElementById(`clicktab_${next.id}__${selectedKey}`);
            swapToTab.focus();
        }
    }
    else if (kbevent.key === 'ArrowDown') {
        const next = getNextAxis(rawData.axes, axisId);
        if (next != null) {
            const selectedKey = getSelectedValKey(next);
            const swapToTab = this.document.getElementById(`clicktab_${next.id}__${selectedKey}`);
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
    const imgPath = [];
    let index = 0;
    for (const subAxis of rawData.axes) {
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
    let newContent = '';
    for (const xVal of xAxis.values) {
        if (canShowVal(xAxis.id, xVal.key)) {
            imgPath[index] = xVal.key;
            const actualUrl = imgPath.join('/') + '.' + rawData.ext;
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

function optDescribe(isFirst, title, subVal) {
    let label = '';
    if (subVal) {
        if (isFirst) {
            label += '<span title="' + escapeHtml(subVal.description) + '"><b>' + subVal.title + '</b></span>';
        }
        label += '<br>';
    }
    return label + title;
}

function fillTable() {
    const x = getCurrentSelectedAxis('x');
    const y = getCurrentSelectedAxis('y');
    const x2 = getCurrentSelectedAxis('x2');
    const y2 = getCurrentSelectedAxis('y2');
    console.log('Do fill table, x=' + x + ', y=' + y + ', x2=' + x2 + ', y2=' + y2);
    const xAxis = getAxisById(x);
    const yAxis = getAxisById(y);
    const x2Axis = x2 === 'None' || x2 === x || x2 === y ? null : getAxisById(x2);
    const y2Axis = y2 === 'None' || y2 === x2 || y2 === x || y2 === y ? null : getAxisById(y2);
    const table = document.getElementById('image_table');
    let newContent = '<tr id="image_table_header" class="sticky_top"><th></th>';
    let superFirst = true;
    for (const x2val of (x2Axis == null ? [null] : x2Axis.values)) {
        if (x2val != null && !canShowVal(x2Axis.id, x2val.key)) {
            continue;
        }
        let x2first = true;
        for (const val of xAxis.values) {
            if (canShowVal(xAxis.id, val.key)) {
                newContent += `<th${(superFirst ? '' : ' class="superaxis_second"')} title="${val.description.replaceAll('"', '&quot;')}">${optDescribe(x2first, val.title, x2val)}</th>`;
                x2first = false;
            }
        }
        superFirst = !superFirst;
    }
    newContent += '</tr>';
    superFirst = true;
    for (const y2val of (y2Axis == null ? [null] : y2Axis.values)) {
        if (y2val != null && !canShowVal(y2Axis.id, y2val.key)) {
            continue;
        }
        let y2first = true;
        for (const val of yAxis.values) {
            if (!canShowVal(yAxis.id, val.key)) {
                continue;
            }
            newContent += `<tr><td class="axis_label_td${(superFirst ? '' : ' superaxis_second')}" title="${escapeHtml(val.description)}">${optDescribe(y2first, val.title, y2val)}</td>`;
            y2first = false;
            for (const x2val of (x2Axis == null ? [null] : x2Axis.values)) {
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
    const id = document.querySelector(`input[name="${axisPrefix}_axis_selector"]:checked`).id;
    const index = id.indexOf('_');
    return id.substring(index + 1);
}

function updateScaling() {
    let percent;
    if (document.getElementById('autoScaleImages').checked) {
        const x = getCurrentSelectedAxis('x');
        const xAxis = getAxisById(x);
        let count = xAxis.values.length;
        const x2 = getCurrentSelectedAxis('x2');
        if (x2 !== 'none') {
            const x2Axis = getAxisById(x2);
            count *= x2Axis.values.length;
        }
        percent = (90 / count) + 'vw';
    }
    else {
        percent = '';
    }
    for (const image of document.getElementById('image_table').getElementsByClassName('table_img')) {
        image.style.width = percent;
    }
    updateTitleSticky();
}

// Public function
function toggleDescriptions() {
    const show = document.getElementById('showDescriptions').checked;
    for (const cName of ['tabval_subdiv', 'axis_table_cell']) {
        for (const elem of document.getElementsByClassName(cName)) {
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
    const axis = getAxisById(axisId);
    let any = false;
    for (const val of axis.values) {
        any = canShowVal(axisId, val.key);
        if (any) {
            break;
        }
    }
    for (const val of axis.values) {
        document.getElementById('showval_' + axisId + '__' + val.key).checked = !any;
        const element = document.getElementById('clicktab_' + axisId + '__' + val.key);
        element.classList.remove('tab_hidden'); // Remove either way to guarantee no duplication
        if (any) {
            element.classList.add('tab_hidden');
        }
    }
    fillTable();
}

// Public function
function toggleShowVal(axis, val) {
    const show = canShowVal(axis, val);
    const element = document.getElementById('clicktab_' + axis + '__' + val);
    if (show) {
        element.classList.remove('tab_hidden');
    }
    else {
        element.classList.add('tab_hidden');
    }
    fillTable();
}

let anyRangeActive = false;

function enableRange(id) {
    const range = document.getElementById('range_tablist_' + id);
    const label = document.getElementById('label_range_tablist_' + id);
    range.oninput = () => {
        anyRangeActive = true;
        label.innerText = (range.value / 2) + ' seconds';
    };
    const tabPage = document.getElementById('tablist_' + id);
    return {
        range,
        counter: 0,
        tabs: tabPage.getElementsByClassName('nav-link')
    };
}

function clickTabAfterActiveTab(tabs) {
    let firstTab = null;
    let foundActive = false;
    const nextTab = Array.from(tabs).find(tab => {
        const isActive = tab.classList.contains('active');
        const isHidden = tab.classList.contains('tab_hidden');
        if (!isHidden && !isActive && !firstTab) firstTab = tab;
        if (isActive) {
            foundActive = true;
            return false;
        }
        return (foundActive && !isHidden);
    }) || firstTab;

    if (nextTab) nextTab.click();
    return nextTab;
}

function startAutoScroll() {
    const rangeSet = [];
    for (const axis of rawData.axes) {
        rangeSet.push(enableRange(axis.id));
    }
    let lastUpdate = 0;
    function autoScroll(timestamp) {
        if (!anyRangeActive || timestamp - lastUpdate < 500) {
            window.requestAnimationFrame(autoScroll);
            return;
        }

        for (const data of rangeSet) {
            if (data.range.value <= 0) {
                continue;
            }
            data.counter += 1;

            if (data.counter > data.range.value) {
                data.counter = 0;
                clickTabAfterActiveTab(data.tabs);
            }
        }
        lastUpdate = timestamp;
        window.requestAnimationFrame(autoScroll);
    }
    window.requestAnimationFrame(autoScroll);
}

// Public function
function doPopupFor(img) {
    popoverLastImg = img;
    const imgPath = unescapeHtml(img.dataset.imgPath).split(',');
    const modalElem = document.getElementById('image_info_modal');
    const metaText = window.crunchMetadata(imgPath);
    const params = escapeHtml(metaText).replaceAll('\n', '\n<br>');
    const text = 'Image: ' + img.alt + (params.length > 1 ? ', parameters: <br>' + params : '<br>(parameters hidden)');
    modalElem.innerHTML = `<div class="modal-dialog" style="display:none">(click outside image to close)</div><div class="modal_inner_div"><img class="popup_modal_img" src="${img.src}"><br><div class="popup_modal_undertext">${text}</div>`;
    $('#image_info_modal').modal('toggle');
}

function updateTitleStickyDirect() {
    const height = Math.round(document.getElementById('top_nav_bar').getBoundingClientRect().height);
    const header = document.getElementById('image_table_header');
    if (header.style.top !== height + 'px') { // This check is to reduce the odds of the browser yelling at us
        header.style.top = height + 'px';
    }
}

function updateTitleSticky() {
    const topBar = document.getElementById('top_nav_bar');
    if (!topBar.classList.contains('sticky_top')) {
        document.getElementById('image_table_header').style.top = '0';
        return;
    }
    // client rect is dynamically animated, so, uh, just hack it for now.
    // TODO: Actually smooth attachment.
    const rate = 50;
    for (let time = 0; time <= 500; time += rate) {
        setTimeout(updateTitleStickyDirect, time);
    }
}

function toggleTopSticky() {
    const topBar = document.getElementById('top_nav_bar');
    if (topBar.classList.contains('sticky_top')) {
        topBar.classList.remove('sticky_top');
    }
    else {
        topBar.classList.add('sticky_top');
    }
    updateTitleSticky();
}

loadData();
