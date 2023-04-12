/**
 * This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

'use strict';

((config) => {
    console.log('Init ###########################################');

    function createStore(rawData, updateHandler) {
        const isProxy = Symbol('isProxy');
        let cancelId = null;
        let oldValue = null;
        function emitUpdate() {
            if (!updateHandler) return;

            clearTimeout(cancelId);
            cancelId = setTimeout(() => {
                const newValue = state.toRaw();
                updateHandler(newValue, oldValue);
                oldValue = newValue;
            }, 100);
        }
        function toRaw(obj) {
            const raw = Array.isArray(obj) ? [] : {};
            Object.entries(obj).forEach(([k, v]) => {
                if (!v[isProxy]) return Reflect.set(raw, k, v);
                return Reflect.set(raw, k, v.toRaw());
            });
            return raw;
        }
        const handler = {
            set(obj, key, val) {
                if (typeof obj[key] === 'object' && obj[key] !== null) {
                    return false;
                }
                if (obj[key] === val) return true;
                const isSuccess = Reflect.set(obj, key, val);
                if (isSuccess) emitUpdate();
                return isSuccess;
            },
            get(obj, key, val) {
                if (key === 'toRaw') return () => toRaw(obj);
                if (key === isProxy) return true;
                if (!(key in obj)) return undefined;
                if (typeof obj[key] === 'object' && obj[key] !== null && !obj[key][isProxy]) {
                    obj[key] = new Proxy(obj[key], handler);
                }
                return Reflect.get(obj, key, val);
            }
        };
        const state = new Proxy(rawData, handler);
        return state;
    }

    const dataStore = createStore(
        {
            axes: { x: '', y: '', x2: 'none', y2: 'none' },
            params: {},
            hidden: {}
        },
        updateTable
    );

    const uiStore = createStore({}, updateUI);

    function applyDefaultSetup() {
        uiStore.descriptions = config.defaults.show_descriptions;
        uiStore.autoscale = config.defaults.autoscale;
        uiStore.sticky = config.defaults.sticky;

        // Set UI options
        document.getElementById('showDescriptions').checked = config.defaults.show_descriptions;
        document.getElementById('autoScaleImages').checked = config.defaults.autoscale;
        document.getElementById('stickyNavigation').checked = config.defaults.sticky;

        // Set selected axis
        for (const coord of Object.keys(dataStore.axes)) {
            document.getElementById(coord + '_' + dataStore.axes[coord]).checked = true;
        }
    }

    function loadData() {
        dataStore.axes.x = config.axes[0].id;
        dataStore.axes.y = config.axes[1]?.id || '';

        // rawData.ext/title/description
        for (const axis of config.axes) {
            // axis.id/title/description
            dataStore.params[axis.id] = axis.values[0].key;
            dataStore.hidden[axis.id] = {};
            for (const val of axis.values) {
                // val.key/title/description/show
                if (!val.show) {
                    dataStore.hidden[axis.id][val.key] = true;
                    document.querySelector(`.form-check-input[data-axis-id="${axis.id}"][data-val-key="${val.key}"]`).checked = false;
                }
            }
        }

        for (const coord of Object.keys(dataStore.axes)) {
            dataStore.axes[coord] = config.defaults[coord] || dataStore.axes[coord];
        }

        applyDefaultSetup();
        console.log(`Loaded data for '${config.title}'`);
    }

    function createListeners() {
        $('#sel_table').on('shown.bs.tab', '.nav-link', ({ target }) => {
            const { axisId, valKey } = target.dataset;
            if (dataStore.params[axisId] !== valKey) {
                dataStore.params[axisId] = valKey;
            }
        });

        $('#axis_selectors').on('click', '.btn-check', ({ target }) => {
            const [coord, ...id] = target.id.split('_');
            dataStore.axes[coord] = id.join('_');
        });

        $('#image_table').on('click', '.table_img', ({ target }) => {
            updateModal(target);
            imgModal.show();
        });

        $('#showDescriptions').on('change', ({ target }) => { uiStore.descriptions = target.checked; });
        $('#autoScaleImages').on('change', ({ target }) => { uiStore.autoscale = target.checked; });
        $('#stickyNavigation').on('change', ({ target }) => { uiStore.sticky = target.checked; });
        $('#toggle_nav_button').on('click', updateTitleSticky);
        $('#toggle_adv_button').on('click', updateTitleSticky);

        $('#settings_accordion_collapse').on('click', 'button', ({ target }) => {
            const { axisId } = target.dataset;
            const axis = getAxisById(axisId);
            const shouldHide = axis.values.some(val => canShowVal(axisId, val.key));
            document.querySelectorAll(`.form-check-input[data-axis-id="${axis.id}"]`).forEach(input => {
                input.checked = !shouldHide;
            });

            for (const val of axis.values) {
                dataStore.hidden[axisId][val.key] = shouldHide;
            }
        });
        $('#settings_accordion_collapse').on('change', '.form-check-input', ({ target }) => {
            const show = !target.checked;
            const { axisId, valKey } = target.dataset;
            dataStore.hidden[axisId][valKey] = show;
        });
    }

    function updateUI() {
        toggleDescriptions();
        updateScaling();
        updateTitleSticky();
    }

    function getAxisById(id) {
        return config.axes.find(axis => axis.id === id);
    }

    const modalElm = document.getElementById('image_info_modal');
    const modalImgElm = modalElm.querySelector('.popup_modal_img');
    const modalMetaElm = modalElm.querySelector('.popup_modal_undertext');
    const imgModal = new bootstrap.Modal(modalElm, { backdrop: true });
    modalImgElm.onload = () => { modalImgElm.style.display = ''; };

    function updateModal(img) {
        const dataSet = img.dataset.set.split(',');
        let metaText = '';
        modalImgElm.style.display = 'none';
        try {
            metaText = 'crunchMetadata' in window ? window.crunchMetadata(config, dataSet) : '';
        } catch (e) {
            console.error(e);
            metaText = e.message;
        }
        const text = 'Image: ' + img.alt + (metaText.length > 1 ? ', parameters: \n' + metaText : '\n(parameters hidden)');

        modalImgElm.src = img.src;
        Object.entries(img.dataset).forEach(([k, v]) => { modalImgElm.dataset[k] = v; });
        modalMetaElm.textContent = text;
    }

    function clickRowImage(x, y) {
        const img = document.querySelector(`#image_table img[data-row="${y}"][data-col="${x}"]`);
        if (!img) return;
        updateModal(img);
        imgModal.handleUpdate();
    }

    function navigateImageModal(key) {
        if (key === 'Escape') {
            imgModal.hide();
            return true;
        }

        const x = Number(modalImgElm.dataset.col);
        const y = Number(modalImgElm.dataset.row);

        switch (key) {
        case 'ArrowLeft':
            clickRowImage(x - 1, y);
            break;
        case 'ArrowRight':
            clickRowImage(x + 1, y);
            break;
        case 'ArrowUp':
            clickRowImage(x, y - 1);
            break;
        case 'ArrowDown':
            clickRowImage(x, y + 1);
            break;
        default:
            return false;
        }
        return true;
    }

    function getNextActiveTab(tabs) {
        let firstTab = null;
        let nextTab = null;
        let foundActive = false;
        tabs.forEach(tab => {
            const isActive = tab.classList.contains('active');
            if (!tab.disabled && !isActive && !firstTab) firstTab = tab;
            if (isActive) {
                foundActive = true;
                return;
            }
            if (foundActive && !tab.disabled && !nextTab) nextTab = tab;
        });

        return nextTab || firstTab;
    }

    function selectTab(elm, key) {
        // right and left are managed by bootstrap
        let tab;
        let group = elm.closest('tr');
        switch (key) {
        case 'ArrowUp':
            while (group && !tab) {
                group = group.previousElementSibling;
                tab = group?.querySelector('.nav-link.active:not(:disabled)');
            }
            break;
        case 'ArrowDown':
            while (group && !tab) {
                group = group.nextElementSibling;
                tab = group?.querySelector('.nav-link.active:not(:disabled)');
            }
            break;
        default:
            return false;
        }
        if (tab) tab.focus();
        return true;
    }

    window.addEventListener('keydown', (kbevent) => {
        let hasTriggered = false;
        const elem = document.activeElement;
        if (elem.classList.contains('nav-link')) {
            hasTriggered = selectTab(elem, kbevent.key);
        }

        if (imgModal._isShown) {
            hasTriggered = navigateImageModal(kbevent.key);
        }

        if (hasTriggered) {
            kbevent.preventDefault();
            kbevent.stopPropagation();
        }
    }, true);

    function escapeHtml(text) {
        return text
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function canShowVal(id, key) {
        return !dataStore.hidden[id][key];
    }

    function getXAxisContent(xAxisId, yAxisId, xAxisValues, yValKey, x2AxisId, x2val, y2AxisId, y2val) {
        const dataSet = [];
        let index = 0;
        for (const subAxis of config.axes) {
            if (subAxis.id === xAxisId) {
                index = dataSet.length;
                dataSet.push(0);
            } else if (subAxis.id === yAxisId) {
                dataSet.push(yValKey);
            } else if (subAxis.id === x2AxisId) {
                dataSet.push(x2val.key);
            } else if (subAxis.id === y2AxisId) {
                dataSet.push(y2val.key);
            } else {
                dataSet.push(dataStore.params[subAxis.id]);
            }
        }
        const newContent = [];
        for (const xVal of xAxisValues) {
            dataSet[index] = xVal.key;
            const actualUrl = dataSet.join('/') + '.' + config.ext;
            const metadata = window.crunchMetadata(config, dataSet, true);
            const img = new Image(metadata.width, metadata.height);
            img.classList.add('table_img');
            img.src = actualUrl;
            img.alt = actualUrl;
            img.loading = 'lazy';
            img.dataset.set = dataSet.join(',');
            img.onerror = setImgPlaceholder;
            newContent.push(img);
        }
        return newContent;
    }

    function setImgPlaceholder(evt) {
        const img = evt.target;
        img.onerror = undefined;
        img.src = './placeholder.png';
    }

    function optDescribe(isFirst, title, extraVal) {
        const label = document.createDocumentFragment();
        const titleTxt = document.createTextNode(title);
        const br = document.createElement('br');
        if (extraVal) {
            if (isFirst) {
                const span = document.createElement('span');
                span.title = escapeHtml(extraVal.description);
                span.style.fontWeight = 'bold';
                span.textContent = extraVal.title;
                label.appendChild(span);
            }
            label.appendChild(br);
        }
        label.appendChild(titleTxt);
        return label;
    }

    function updateTable(state, prevState) {
        updateHiddenTabs(); // TODO: move under updateUI
        if (prevState) {
            const needUpdateAxes = Object.keys(state.axes).some(coord => {
                return state.axes[coord] !== prevState.axes[coord];
            });

            const selectedAxis = Object.values(state.axes).filter(id => id !== 'none');
            const needUpdateParam = Object.keys(state.params).some(id => {
                return state.params[id] !== prevState.params[id] && !selectedAxis.includes(id);
            });
            // TODO: hide col or row instead of redraw
            const needUpdateHidden = selectedAxis.some(id => {
                return Object.keys(state.hidden[id]).some(key => {
                    return state.hidden[id][key] !== prevState.hidden[id][key];
                });
            });
            console.log('Need update table:', needUpdateAxes || needUpdateParam || needUpdateHidden);
            if (!needUpdateAxes && !needUpdateParam && !needUpdateHidden) return;
        }

        const { x, y, x2, y2 } = dataStore.axes;
        console.log('Do fill table, x=' + x + ', y=' + y + ', x2=' + x2 + ', y2=' + y2);

        const xAxis = getAxisById(x);
        const yAxis = getAxisById(y);
        const x2Axis = x2 === 'none' || x2 === x || x2 === y ? {} : getAxisById(x2);
        const y2Axis = y2 === 'none' || y2 === x2 || y2 === x || y2 === y ? {} : getAxisById(y2);
        const table = document.getElementById('image_table');
        let superFirst = true;

        const xAxisValues = xAxis.values.filter(val => canShowVal(xAxis.id, val.key));
        const yAxisValues = yAxis.values.filter(val => canShowVal(yAxis.id, val.key));
        const x2AxisValues = x2Axis.values?.filter(val => canShowVal(x2Axis.id, val.key)) || [null];
        const y2AxisValues = y2Axis.values?.filter(val => canShowVal(y2Axis.id, val.key)) || [null];
        const nbColumn = x2AxisValues.length * xAxisValues.length;

        table.innerHTML = '';
        const header = document.createElement('thead');
        header.id = 'image_table_header';
        header.classList.add('sticky_top');
        header.appendChild(document.createElement('th'));

        for (const x2val of x2AxisValues) {
            let x2first = true;
            for (const val of xAxisValues) {
                const th = document.createElement('th');
                if (!superFirst) th.classList.add('superaxis_second');
                th.title = escapeHtml(val.description);
                th.style.width = `${Math.floor(90 / nbColumn)}vw`;
                th.appendChild(optDescribe(x2first, val.title, x2val));
                header.appendChild(th);
                x2first = false;
            }
            superFirst = !superFirst;
        }
        table.appendChild(header);

        const body = document.createElement('tbody');
        superFirst = true;
        for (const y2val of y2AxisValues) {
            let y2first = true;
            for (const val of yAxisValues) {
                const row = document.createElement('tr');
                const label = document.createElement('td');
                label.classList.add('axis_label_td');
                if (!superFirst) label.classList.add('superaxis_second');
                label.title = escapeHtml(val.description);
                label.appendChild(optDescribe(y2first, val.title, y2val));
                row.appendChild(label);
                y2first = false;
                let col = 1;
                for (const x2val of x2AxisValues) {
                    getXAxisContent(x, y, xAxisValues, val.key, x2Axis.id, x2val, y2Axis.id, y2val).forEach(img => {
                        const content = document.createElement('td');
                        img.dataset.row = body.childElementCount + 1;
                        img.dataset.col = col++;
                        content.appendChild(img);
                        row.appendChild(content);
                    });
                }
                body.appendChild(row);
                if (x === y) break;
            }
            superFirst = !superFirst;
        }
        table.appendChild(body);
    }

    function updateScaling() {
        const autoscale = uiStore.autoscale;
        document.getElementById('image_table').classList.toggle('scale', autoscale);
    }

    function toggleDescriptions() {
        const show = uiStore.descriptions;
        for (const cName of ['tab-content', 'axis_table_cell']) {
            for (const elem of document.getElementsByClassName(cName)) {
                elem.classList.toggle('tab_hidden', !show);
            }
        }
    }

    function updateHiddenTabs() {
        const hidden = dataStore.hidden;
        const selectedAxis = Object.values(dataStore.axes).filter(id => id !== 'none');
        document.querySelectorAll('#sel_table .nav-link').forEach(tab => {
            const { axisId, valKey } = tab.dataset;
            tab.classList.toggle('tab_hidden', !!hidden[axisId][valKey]);
            tab.disabled = hidden[axisId][valKey] || selectedAxis.includes(axisId);
        });
    }

    let anyRangeActive = false;

    function enableRange(id) {
        const range = document.getElementById('range_tablist_' + id);
        const label = document.getElementById('label_range_tablist_' + id);
        range.oninput = () => {
            anyRangeActive = true;
            label.innerText = (range.value / 2) + ' seconds';
        };
        const tabs = document.querySelectorAll(`.nav-link[data-axis-id="${id}"]`);
        return {
            range,
            counter: 0,
            tabs
        };
    }

    function startAutoScroll() {
        const rangeSet = [];
        for (const axis of config.axes) {
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
                    const tab = getNextActiveTab(data.tabs);
                    if (tab) tab.click();
                }
            }
            lastUpdate = timestamp;
            window.requestAnimationFrame(autoScroll);
        }
        window.requestAnimationFrame(autoScroll);
    }

    function updateTitleStickyDirect(topBar) {
        // client rect is dynamically animated, so, uh, just hack it for now.
        setTimeout(() => {
            const height = Math.round(topBar.getBoundingClientRect().height);
            const header = document.getElementById('image_table_header');
            if (header.style.top === (height + 'px')) {
                return;
            }
            header.style.top = height + 'px';
            updateTitleStickyDirect(topBar);
        }, 50);
    }

    function updateTitleSticky() {
        const topBar = document.getElementById('top_nav_bar');
        topBar.classList.toggle('sticky_top', uiStore.sticky);
        const imgTable = document.getElementById('image_table_header');
        if (!imgTable) return;
        if (!uiStore.sticky) {
            imgTable.style.top = '';
            return;
        }
        // TODO: Actually smooth attachment.
        updateTitleStickyDirect(topBar);
    }

    loadData();
    startAutoScroll();
    createListeners();
})(window.rawData);
