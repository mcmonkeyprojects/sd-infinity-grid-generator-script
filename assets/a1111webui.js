/**
 * This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.
 */

'use strict';

(() => {
    /* eslint dot-notation: off */
    function genParamQuote(text) {
        // Referenced to match generation_parameters_copypaste.py - quote(text)
        if (!text.includes(',')) {
            return text;
        }
        return `"${text.toString().replaceAll('\\', '\\\\').replaceAll('"', '\\"')}"`;
    }

    function formatMet(name, val, bad) {
        if (val == null) {
            return '';
        }
        val = val.toString();
        if (bad !== undefined && val === bad) {
            return '';
        }
        return `${name}: ${genParamQuote(val)}`;
    }

    function formatMetadata(valSet) {
        if (!Object.keys(valSet).length) {
            return '';
        }
        const metadataSet = [`Prompt: ${valSet['prompt']}`];

        // Referenced to match processing.py - create_infotext(p)
        if (valSet.negativeprompt) {
            metadataSet.push(`Negative prompt: ${valSet['negativeprompt']}`);
        }

        const handled = ['steps', 'sampler', 'cfgscale', 'seed', 'restorefaces', 'width', 'height', 'model', 'varseed', 'varstrength', 'denoising', 'eta', 'clipskip', 'vae', 'sigmachurn', 'sigmatmin', 'sigmatmax', 'sigmanoise', 'prompt', 'negativeprompt'];
        const keyData = [
            formatMet('Steps', valSet['steps']),
            formatMet('Sampler', valSet['sampler']),
            formatMet('CFG scale', valSet['cfgscale']),
            formatMet('Seed', valSet['seed']),
            formatMet('Face restoration', valSet['restorefaces'], 'false'),
            formatMet('Size', valSet['width'] + 'x' + valSet['height']),
            // model hash
            formatMet('Model', valSet['model']),
            // Batch size, batch pos
            formatMet('Variation seed', valSet['varseed'], '0'),
            formatMet('Variation seed strength', valSet['varstrength'], '0'),
            // Seed resize from
            formatMet('Denoising strength', valSet['denoising']),
            // Conditional mask weight
            formatMet('Eta', valSet['eta']),
            formatMet('Clip skip', valSet['clipskip'], '1'),
            // ENSD
        ].filter(Boolean);
        metadataSet.push(keyData.join(', '));

        // Not part of normal gen-params
        const extraData = [
            formatMet('VAE', valSet['vae']),
            formatMet('Sigma Churn', valSet['sigmachurn'], '0'),
            formatMet('Sigma T-Min', valSet['sigmatmin'], '0'),
            formatMet('Sigma T-Max', valSet['sigmatmax'], '1'),
            formatMet('Sigma Noise', valSet['sigmanoise'], '1'),
        ].filter(Boolean);
        if (valSet['restorefaces'] === 'CodeFormer') {
            extraData.push(formatMet('CodeFormer Weight', valSet['codeformerweight']));
        }
        metadataSet.push(extraData.join(', '));

        const lastData = [];
        for (const [key, value] of Object.entries(valSet)) {
            if (!handled.includes(key)) {
                lastData.push(`${key}: ${value}`);
            }
        }
        metadataSet.push(`(Other): ${lastData.join(', ')}`);

        return metadataSet.join('\n');
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

    window.crunchMetadata = function crunchMetadata(rawData, dataSet, needRaw = false) {
        if (!('metadata' in rawData)) {
            return '';
        }
        if (dataSet.length !== rawData.axes.length) {
            throw new Error(`metadata parsing failed. Wrong data length. ${dataSet.length} vs ${rawData.axes.length}`);
        }

        const initialData = structuredClone(rawData.metadata);
        rawData.axes.forEach((axis, index) => {
            const actualVal = axis.values.find(val => val.key === dataSet[index]);
            if (!actualVal) {
                throw new Error(`metadata parsing failed for part ${index}: ${dataSet[index]}`);
            }
            for (let [key, value] of Object.entries(actualVal.params)) {
                crunchParamHook(initialData, key.replaceAll(' ', ''), value);
            }
        });

        return needRaw ? initialData : formatMetadata(initialData);
    };
})();
