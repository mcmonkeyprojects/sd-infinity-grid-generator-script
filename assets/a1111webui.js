/**
 * This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

'use strict';

function genParamQuote(text) {
    // Referenced to match generation_parameters_copypaste.py - quote(text)
    if (!text.includes(',')) {
        return text;
    }
    return '"' + text.toString().replaceAll('\\', '\\\\').replaceAll('"', '\\"') + '"';
}

function formatMet(name, val, bad) {
    if (val == null) {
        return '';
    }
    val = val.toString();
    if (bad !== undefined && val === bad) {
        return '';
    }
    return name + ': ' + genParamQuote(val) + ', ';
}

function formatMetadata(valSet) {
    const count = Object.keys(valSet).length;
    if (count === 0) {
        return '';
    }
    if (count === 1) {
        return valSet['error'] || '';
    }
    // Referenced to match processing.py - create_infotext(p)
    let negative = '';
    if (valSet['negativeprompt']) {
        negative = '\nNegative prompt: ' + valSet['negativeprompt'];
    }
    const handled = ['steps', 'sampler', 'cfgscale', 'seed', 'restorefaces', 'width', 'height', 'model', 'varseed', 'varstrength', 'denoising', 'eta', 'clipskip', 'vae', 'sigmachurn', 'sigmatmin', 'sigmatmax', 'sigmanoise', 'prompt', 'negativeprompt'];
    let keyData = formatMet('Steps', valSet['steps'])
        + formatMet('Sampler', valSet['sampler'])
        + formatMet('CFG scale', valSet['cfgscale'])
        + formatMet('Seed', valSet['seed'])
        + formatMet('Face restoration', valSet['restorefaces'], 'false')
        + formatMet('Size', valSet['width'] + 'x' + valSet['height'])
        // model hash
        + formatMet('Model', valSet['model'])
        // Batch size, batch pos
        + formatMet('Variation seed', valSet['varseed'], '0')
        + formatMet('Variation seed strength', valSet['varstrength'], '0')
        // Seed resize from
        + formatMet('Denoising strength', valSet['denoising'])
        // Conditional mask weight
        + formatMet('Eta', valSet['eta'])
        + formatMet('Clip skip', valSet['clipskip'], '1')
        // ENSD
        + '';
        // Not part of normal gen-params
    keyData = keyData.substring(0, keyData.length - 2);

    let extraData = formatMet('VAE', valSet['vae'])
        + formatMet('Sigma Churn', valSet['sigmachurn'], '0')
        + formatMet('Sigma T-Min', valSet['sigmatmin'], '0')
        + formatMet('Sigma T-Max', valSet['sigmatmax'], '1')
        + formatMet('Sigma Noise', valSet['sigmanoise'], '1')
        + (valSet['restorefaces'] === 'CodeFormer' ? formatMet('CodeFormer Weight', valSet['codeformerweight']) : '');
    if (extraData.length > 2) {
        extraData = extraData.substring(0, extraData.length - 2);
    }

    let lastData = '';
    for (const [key, value] of Object.entries(valSet)) {
        if (!handled.includes(key)) {
            lastData += `${key}: ${value}, `;
        }
    }
    if (lastData.length > 2) {
        lastData = '\n(Other): ' + lastData.substring(0, lastData.length - 2);
    }
    return valSet['prompt'] + negative + '\n' + keyData + '\n' + extraData + lastData;
}

function crunchParamHook(data, key, value) {
    if (key !== 'promptreplace') {
        data[key] = value;
        return;
    }
    const replacers = value.split('=', 2);
    const match = replacers[0].trim();
    const replace = replacers[1].trim();
    data['prompt'] = data['prompt'].replaceAll(match, replace);
    data['negativeprompt'] = data['negativeprompt'].replaceAll(match, replace);
}

// Public function
function crunchMetadata(parts) {
    if (!('metadata' in rawData)) {
        return '';
    }
    if (parts.length !== rawData.axes.length) {
        return `metadata parsing failed. Wrong data length. ${parts.length} vs ${rawData.axes.length}`;
    }
    const initialData = structuredClone(rawData.metadata);
    for (let index = 0; index < parts.length; index++) {
        const part = parts[index];
        const axis = rawData.axes[index];
        const actualVal = axis.values.find(val => val.key === part);
        if (actualVal == null) {
            return `Error metadata parsing failed for part ${index}: ${part}`;
        }
        for (const [key, value] of Object.entries(actualVal.params)) {
            crunchParamHook(initialData, key.replaceAll(' ', ''), value);
        }
    }
    return formatMetadata(initialData);
}
