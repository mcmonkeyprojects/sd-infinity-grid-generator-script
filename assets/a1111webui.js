/**
 * This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

function formatMetadata(valSet) {
    var count = Object.keys(valSet).length;
    if (count == 0) {
        return '';
    }
    else if (count == 1) {
        return valSet['error'];
    }
    // Referenced to match processing.py - create_infotext(p)
    var negative = valSet['negativeprompt'];
    if (negative.length > 0) {
        negative = '\nNegative prompt: ' + negative;
    }
    const handled = ['steps', 'sampler', 'cfgscale', 'seed', 'restorefaces', 'width', 'height', 'model', 'varseed', 'varstrength', 'denoising', 'eta', 'clipskip', 'vae', 'sigmachurn', 'sigmatmin', 'sigmatmax', 'sigmanoise', 'prompt', 'negativeprompt'];
    var keyData = formatMet('Steps', valSet['steps'])
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
        ;
        // Not part of normal gen-params
    var extraData = formatMet('VAE', valSet['vae'])
        + formatMet('Sigma Churn', valSet['sigmachurn'], '0')
        + formatMet('Sigma T-Min', valSet['sigmatmin'], '0')
        + formatMet('Sigma T-Max', valSet['sigmatmax'], '1')
        + formatMet('Sigma Noise', valSet['sigmanoise'], '1')
        + (valSet['restorefaces'] == 'CodeFormer' ? formatMet('CodeFormer Weight', valSet['codeformerweight']) : '')
        ;
    lastData = '';
    for (const [key, value] of Object.entries(valSet)) {
        if (!handled.includes(key)) {
            lastData += `${key}: ${value}, `;
        }
    }
    if (lastData.length > 2) {
        lastData = '\n(Other): ' + lastData.substring(0, lastData.length - 2);
    }
    keyData = keyData.substring(0, keyData.length - 2);
    if (extraData.length > 2) {
        extraData = extraData.substring(0, extraData.length - 2);
    }
    return valSet['prompt'] + negative + '\n' + keyData + '\n' + extraData + lastData;
}

function crunchParamHook(data, key, value) {
    if (key == 'promptreplace') {
        var replacers = value.split('=', 2);
        var match = replacers[0].trim();
        var replace = replacers[1].trim();
        data['prompt'] = data['prompt'].replaceAll(match, replace);
        data['negativeprompt'] = data['negativeprompt'].replaceAll(match, replace);
        return true;
    }
    return false;
}
