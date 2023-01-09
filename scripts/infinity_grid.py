##################
# Stable Diffusion Infinity Grid Generator
#
# Author: Alex 'mcmonkey' Goodwin
# GitHub URL: https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script
# Created: 2022/12/08
# Last updated: 2022/12/08
#
# For usage help, view the README.md file in the extension root, or via the GitHub page.
#
##################

import gradio as gr
import os
import glob
import yaml
import json
import shutil
import math
from copy import copy
from modules import images, shared, sd_models, sd_vae, sd_samplers, scripts, processing
from modules.processing import process_images, Processed
from modules.shared import opts
from modules.hypernetworks import hypernetwork

######################### Constants #########################
refresh_symbol = '\U0001f504'  # 🔄
INF_GRID_README = "https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script"

######################### Utilities #########################
def getNameList():
    relPath = os.path.join(Script.BASEDIR, "assets")
    fileList = glob.glob(relPath + "/*.yml")
    justFileNames = list(map(lambda f: os.path.relpath(f, relPath), fileList))
    return justFileNames

def fixDict(d):
    if d is None:
        return None
    if type(d) is not dict:
        raise RuntimeError(f"Value '{d}' is supposed to be submapping but isn't (it's plaintext, a list, or some other incorrect format). Did you typo the formatting?")
    return {str(k).lower(): v for k, v in d.items()}

def cleanForWeb(text):
    if text is None:
        return None
    if type(text) is not str:
        raise RuntimeError(f"Value '{text}' is supposed to be text but isn't (it's a datamapping, list, or some other incorrect format). Did you typo the formatting?")
    return text.replace('"', '&quot;')

def cleanName(name):
    return str(name).lower().replace(' ', '').strip()

def getBestInList(name, list):
    backup = None
    bestLen = 999
    name = cleanName(name)
    for listVal in list:
        listValClean = cleanName(listVal)
        if listValClean == name:
            return listVal
        if name in listValClean:
            if len(listValClean) < bestLen:
                backup = listVal
                bestLen = len(listValClean)
    return backup

def getModelFor(name):
    return getBestInList(name, map(lambda m: m.title, sd_models.checkpoints_list.values()))

def getHypernetworkFor(name):
    return getBestInList(name, shared.hypernetworks.keys())

def getVaeFor(name):
    return getBestInList(name, sd_vae.vae_dict.keys())

def getSamplerFor(name):
    return getBestInList(name, sd_samplers.all_samplers_map.keys())

def getFaceRestorer(name):
    return getBestInList(name, map(lambda m: m.name(), shared.face_restorers))

def chooseBetterFileName(rawName, fullName):
    partialName = os.path.splitext(os.path.basename(fullName))[0]
    if '/' in rawName or '\\' in rawName or '.' in rawName or len(rawName) >= len(partialName):
        return rawName
    return partialName

def fixNum(num):
    if num is None or math.isinf(num) or math.isnan(num):
        return None
    return num

######################### Value Modes #########################
def applySampler(p, v):
    p.sampler_name = getSamplerFor(v)
def applySeed(p, v):
    p.seed = int(v)
def applySteps(p, v):
    p.steps = int(v)
def applyCfgScale(p, v):
    p.cfg_scale = float(v)
def applyModel(p, v):
    info = sd_models.get_closet_checkpoint_match(getModelFor(v))
    sd_models.reload_model_weights(shared.sd_model, info)
    p.sd_model = shared.sd_model
def applyVae(p, v):
    vaeName = cleanName(v)
    if vaeName not in ["auto", "none"]:
        vaeName = getVaeFor(vaeName)
    sd_vae.reload_vae_weights(None, sd_vae.vae_dict[vaeName])
def applyWidth(p, v):
    p.width = int(v)
def applyHeight(p, v):
    p.height = int(v)
def applyHypernetwork(p, v):
    hnName = cleanName(v)
    if hnName == "none":
        hnName = None
    else:
        hnName = getHypernetworkFor(hnName)
    hypernetwork.load_hypernetwork(hnName)
def applyHypernetworkStrength(p, v):
    hypernetwork.HypernetworkModule.multiplier = float(v)
def applyPrompt(p, v):
    p.prompt = v
def applyNegativePrompt(p, v):
    p.negative_prompt = v
def applyVarSeed(p, v):
    p.subseed = int(v)
def applyVarSeedStrength(p, v):
    p.subseed_strength = float(v)
def applyClipSkip(p, v):
    opts.CLIP_stop_at_last_layers = int(v)
def applyCodeformerWeight(p, v):
    opts.code_former_weight = float(v)
def applyDenoising(p, v):
    p.denoising_strength = float(v)
def applyEta(p, v):
    p.eta = float(v)
def applySigmaChurn(p, v):
    p.s_churn = float(v)
def applySigmaTmin(p, v):
    p.s_tmin = float(v)
def applySigmaTmax(p, v):
    p.s_tmax = float(v)
def applySigmaNoise(p, v):
    p.s_noise = float(v)
def applyOutWidth(p, v):
    p.inf_grid_out_width = int(v)
def applyOutHeight(p, v):
    p.inf_grid_out_height = int(v)
def applyRestoreFaces(p, v):
    input = str(v).lower().strip()
    if input == "false":
        p.restore_faces = False
        return
    p.restore_faces = True
    restorer = getFaceRestorer(input)
    if restorer is not None:
        opts.face_restoration_model = restorer
def applyPromptReplace(p, v):
    val = v.split('=', maxsplit=1)
    if len(val) != 2:
        raise RuntimeError(f"Invalid prompt replace, missing '=' symbol, for '{v}'")
    match = val[0].strip()
    replace = val[1].strip()
    if Script.VALIDATE_REPLACE and match not in p.prompt and match not in p.negative_prompt:
        raise RuntimeError(f"Invalid prompt replace, '{match}' is not in prompt '{p.prompt}' nor negative prompt '{p.negative_prompt}'")
    p.prompt = p.prompt.replace(match, replace)
    p.negative_prompt = p.negative_prompt.replace(match, replace)

validModes = {
    "sampler": { "dry": True, "type": "text", "apply": applySampler },
    "seed": { "dry": True, "type": "integer", "apply": applySeed },
    "steps": { "dry": True, "type": "integer", "min": 0, "max": 200, "apply": applySteps },
    "cfgscale": { "dry": True, "type": "decimal", "min": 0, "max": 50, "apply": applyCfgScale },
    "model": { "dry": False, "type": "text", "apply": applyModel },
    "vae": { "dry": False, "type": "text", "apply": applyVae },
    "width": { "dry": True, "type": "integer", "apply": applyWidth },
    "height": { "dry": True, "type": "integer", "apply": applyHeight },
    "hypernetwork": { "dry": False, "type": "text", "apply": applyHypernetwork },
    "hypernetworkstrength": { "dry": False, "type": "decimal", "min": 0, "max": 1, "apply": applyHypernetworkStrength },
    "prompt": { "dry": True, "type": "text", "apply": applyPrompt },
    "negativeprompt": { "dry": True, "type": "text", "apply": applyNegativePrompt },
    "varseed": { "dry": True, "type": "integer", "apply": applyVarSeed },
    "varstrength": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applyVarSeedStrength },
    "clipskip": { "dry": False, "type": "integer", "min": 1, "max": 12, "apply": applyClipSkip },
    "denoising": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applyDenoising },
    "eta": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applyEta },
    "sigmachurn": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applySigmaChurn },
    "sigmatmin": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applySigmaTmin },
    "sigmatmax": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applySigmaTmax },
    "sigmanoise": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applySigmaNoise },
    "outwidth": { "dry": True, "type": "integer", "min": 0, "apply": applyOutWidth },
    "outheight": { "dry": True, "type": "integer", "min": 0, "apply": applyOutHeight },
    "restorefaces": { "dry": True, "type": "text", "apply": applyRestoreFaces },
    "codeformerweight": { "dry": True, "type": "decimal", "min": 0, "max": 1, "apply": applyCodeformerWeight },
    "promptreplace": { "dry": True, "type": "text", "apply": applyPromptReplace }
}

######################### Validation #########################
def validateParams(params):
    for p,v in params.items():
        params[p] = validateSingleParam(p, v)

def validateSingleParam(p, v):
        p = cleanName(p)
        mode = validModes.get(p)
        if mode is None:
            raise RuntimeError(f"Invalid grid default parameter '{p}': unknown mode")
        modeType = mode["type"]
        if modeType == "integer":
            vInt = int(v)
            if vInt is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be an integer number")
            min = mode.get("min")
            max = mode.get("max")
            if min is not None and vInt < min:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be at least {min}")
            if max is not None and vInt > max:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must not exceed {max}")
        elif modeType == "decimal":
            vFloat = float(v)
            if vFloat is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be a decimal number")
            min = mode.get("min")
            max = mode.get("max")
            if min is not None and vFloat < min:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be at least {min}")
            if max is not None and vFloat > max:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must not exceed {max}")
        elif modeType == "boolean":
            vClean = str(v).lower().strip()
            if vClean != "true" and vClean != "false":
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be either 'true' or 'false'")
        elif p == "model":
            actualModel = getModelFor(v)
            if actualModel is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': model name unrecognized - valid {list(map(lambda m: m.title, sd_models.checkpoints_list.values()))}")
            return chooseBetterFileName(v, actualModel)
        elif p == "hypernetwork":
            hnName = cleanName(v)
            if hnName == "none":
                return hnName
            actualHn = getHypernetworkFor(hnName)
            if actualHn is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': hypernetwork name unrecognized - valid: {list(shared.hypernetworks.keys())}")
            return chooseBetterFileName(v, actualHn)
        elif p == "vae":
            vaeName = cleanName(v)
            if vaeName == "none" or vaeName == "auto":
                return vaeName
            actualVae = getVaeFor(vaeName)
            if actualVae is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': VAE name unrecognized - valid: {list(sd_vae.vae_dict.keys())}")
            return chooseBetterFileName(v, actualVae)
        elif p == "sampler":
            actualSampler = getSamplerFor(cleanName(v))
            if actualSampler is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': sampler name unrecognized - valid: {list(sd_samplers.all_samplers_map.keys())}")
        elif p == "restorefaces":
            restorerName = cleanName(v)
            if restorerName == "true":
                return opts.face_restoration_model
            if restorerName == "false":
                return "false"
            actualRestorer = getFaceRestorer(restorerName)
            if actualRestorer is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': Face Restorer name unrecognized - valid: 'true', 'false', {list(map(lambda m: m.name(), shared.face_restorers))}")
            return actualRestorer
        return v

######################### YAML Parsing and Processing #########################
class AxisValue:
    def __init__(self, axis, key, val):
        self.axis = axis
        self.key = str(key).lower()
        self.params = list()
        if isinstance(val, str):
            halves = val.split('=', maxsplit=1)
            if len(halves) != 2:
                raise RuntimeError(f"Invalid value '{key}': '{val}': not expected format")
            validateSingleParam(halves[0], halves[1])
            self.title = halves[1]
            self.params = { cleanName(halves[0]): halves[1] }
            self.description = None
            self.skip = False
            self.show = True
        else:
            self.title = val.get("title")
            self.description = val.get("description")
            self.skip = (str(val.get("skip"))).lower() == "true"
            self.params = fixDict(val.get("params"))
            self.show = (str(val.get("show"))).lower() != "false"
            if self.title is None or self.params is None:
                raise RuntimeError(f"Invalid value '{key}': '{val}': missing title or params")
            validateParams(self.params)
    
    def __str__(self):
        return f"(title={self.title}, description={self.description}, params={self.params})"
    def __unicode__(self):
        return self.__str__()

class Axis:
    def __init__(self, id, obj):
        self.values = list()
        self.id = str(id).lower()
        self.title = obj.get("title")
        self.default = obj.get("default")
        if self.title is None:
            raise RuntimeError("missing title")
        self.description = obj.get("description")
        valuesObj = obj.get("values")
        if valuesObj is None:
            raise RuntimeError("missing values")
        for key, val in valuesObj.items():
            try:
                self.values.append(AxisValue(self, key, val))
            except Exception as e:
                raise RuntimeError(f"value '{key}' errored: {e}")

class GridFileHelper:
    def parseYaml(self, yamlContent, grid_file):
        self.axes = list()
        yamlContent = fixDict(yamlContent)
        gridObj = fixDict(yamlContent.get("grid"))
        if gridObj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'grid' root key")
        self.title = gridObj.get("title")
        self.description = gridObj.get("description")
        self.author = gridObj.get("author")
        self.format = gridObj.get("format")
        if self.title is None or self.description is None or self.author is None or self.format is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing grid title, author, format, or description in grid obj {gridObj}")
        self.params = fixDict(gridObj.get("params"))
        if self.params is not None:
            validateParams(self.params)
        axesObj = fixDict(yamlContent.get("axes"))
        if axesObj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'axes' root key")
        for id, axisObj in axesObj.items():
            try:
                self.axes.append(Axis(id, fixDict(axisObj)))
            except Exception as e:
                raise RuntimeError(f"Invalid axis '{id}': errored: {e}")
        totalCount = 1
        for axis in self.axes:
            totalCount *= len(axis.values)
        if totalCount <= 0:
            raise RuntimeError(f"Invalid file {grid_file}: something went wrong ... is an axis empty? total count is {totalCount} for {len(self.axes)} axes")
        cleanDesc = self.description.replace('\n', ' ')
        print(f"Loaded grid file, title '{self.title}', description '{cleanDesc}', with {len(self.axes)} axes... combines to {totalCount} total images")
        return self

######################### Actual Execution Logic #########################
class SingleGridCall:
    def __init__(self, values):
        self.values = values
        self.replacements = list()
        self.skip = False
        for val in values:
            if val.skip:
                self.skip = True

    def flattenParams(self, grid):
        self.params = grid.params.copy() if grid.params is not None else dict()
        for val in self.values:
            for p, v in val.params.items():
                if cleanName(p) == "promptreplace":
                    self.replacements.append(v)
                else:
                    self.params[p] = v

    def applyTo(self, p, dry):
        for name, val in self.params.items():
            mode = validModes[cleanName(name)]
            if not dry or mode["dry"]:
                mode["apply"](p, val)
        for replace in self.replacements:
            applyPromptReplace(p, replace)

class GridRunner:
    def __init__(self, grid, doOverwrite, basePath, p, fast_skip):
        self.grid = grid
        self.totalRun = 0
        self.totalSkip = 0
        self.totalSteps = 0
        self.doOverwrite = doOverwrite
        self.basePath = basePath
        self.fast_skip = fast_skip
        self.p = p

    def buildValueSetList(self, axisList):
        result = list()
        if len(axisList) == 0:
            return result
        curAxis = axisList[0]
        if len(axisList) == 1:
            for val in curAxis.values:
                if not val.skip or not self.fast_skip:
                    newList = list()
                    newList.append(val)
                    result.append(SingleGridCall(newList))
            return result
        nextAxisList = axisList[1::]
        for obj in self.buildValueSetList(nextAxisList):
            for val in curAxis.values:
                if not val.skip or not self.fast_skip:
                    newList = obj.values.copy()
                    newList.append(val)
                    result.append(SingleGridCall(newList))
        return result

    def preprocess(self):
        self.valueSets = self.buildValueSetList(list(reversed(self.grid.axes)))
        print(f'Have {len(self.valueSets)} unique value sets, will go into {self.basePath}')
        for set in self.valueSets:
            set.filepath = os.path.join(self.basePath, '/'.join(list(map(lambda v: cleanName(v.key), set.values))))
            set.data = ', '.join(list(map(lambda v: f"{v.axis.title}={v.title}", set.values)))
            set.flattenParams(self.grid)
            set.doSkip = set.skip or (not self.doOverwrite and os.path.exists(set.filepath + "." + self.grid.format))
            if set.doSkip:
                self.totalSkip += 1
            else:
                self.totalRun += 1
                stepCount = set.params.get("steps")
                self.totalSteps += int(stepCount) if stepCount is not None else self.p.steps
        print(f"Skipped {self.totalSkip} files, will run {self.totalRun} files, for {self.totalSteps} total steps")

    def run(self, dry):
        shared.total_tqdm.updateTotal(self.totalSteps)
        iteration = 0
        last = None
        for set in self.valueSets:
            if set.doSkip:
                continue
            iteration += 1
            if not dry:
                print(f'On {iteration}/{self.totalRun} ... Set: {set.data}, file {set.filepath}')
            p = copy(self.p)
            oldClipSkip = opts.CLIP_stop_at_last_layers
            oldCodeformerWeight = opts.code_former_weight
            oldFaceRestorer = opts.face_restoration_model
            oldHnStrength = hypernetwork.HypernetworkModule.multiplier
            set.applyTo(p, dry)
            if dry:
                continue
            processed = process_images(p)
            if len(processed.images) != 1:
                raise RuntimeError(f"Something went wrong! Image gen '{set.data}' produced {len(processed.images)} images, which is wrong")
            os.makedirs(os.path.dirname(set.filepath), exist_ok=True)
            if hasattr(p, 'inf_grid_out_width') and hasattr(p, 'inf_grid_out_height'):
                processed.images[0] = processed.images[0].resize((p.inf_grid_out_width, p.inf_grid_out_height), resample=images.LANCZOS)
            info = processing.create_infotext(p, [p.prompt], [p.seed], [p.subseed], [])
            images.save_image(processed.images[0], path=os.path.dirname(set.filepath), basename="", forced_filename=os.path.basename(set.filepath), save_to_dirs=False, info=info, extension=self.grid.format, p=p, prompt=p.prompt, seed=processed.seed)
            last = processed
            opts.CLIP_stop_at_last_layers = oldClipSkip
            opts.code_former_weight = oldCodeformerWeight
            opts.face_restoration_model = oldFaceRestorer
            hypernetwork.HypernetworkModule.multiplier = oldHnStrength
        return last

class SettingsFixer():
    def __enter__(self):
        self.model = shared.sd_model
        self.hypernetwork = opts.sd_hypernetwork
        self.CLIP_stop_at_last_layers = opts.CLIP_stop_at_last_layers
        self.code_former_weight = opts.code_former_weight
        self.face_restoration_model = opts.face_restoration_model

    def __exit__(self, exc_type, exc_value, tb):
        sd_models.reload_model_weights(self.model)
        hypernetwork.load_hypernetwork(self.hypernetwork)
        hypernetwork.apply_strength()
        opts.code_former_weight = self.code_former_weight
        opts.face_restoration_model = self.face_restoration_model
        opts.CLIP_stop_at_last_layers = self.CLIP_stop_at_last_layers

######################### Web Data Builders #########################
class WebDataBuilder():

    def getBaseParamData(p):
        return {
            "sampler": p.sampler_name,
            "seed": p.seed,
            "restorefaces": (opts.face_restoration_model if p.restore_faces else None),
            "steps": p.steps,
            "cfgscale": p.cfg_scale,
            "model": chooseBetterFileName('', shared.sd_model.sd_checkpoint_info.model_name).replace(',', '').replace(':', ''),
            "vae": (None if sd_vae.loaded_vae_file is None else (chooseBetterFileName('', sd_vae.loaded_vae_file).replace(',', '').replace(':', ''))),
            "width": p.width,
            "height": p.height,
            "hypernetwork": (None if shared.loaded_hypernetwork is None else (chooseBetterFileName('', shared.loaded_hypernetwork.name)).replace(',', '').replace(':', '')),
            "hypernetworkstrength": (None if shared.loaded_hypernetwork is None or shared.opts.sd_hypernetwork_strength >= 1 else shared.opts.sd_hypernetwork_strength),
            "prompt": p.prompt,
            "negativeprompt": p.negative_prompt,
            "varseed": (None if p.subseed_strength == 0 else p.subseed),
            "varstrength": (None if p.subseed_strength == 0 else p.subseed_strength),
            "clipskip": opts.CLIP_stop_at_last_layers,
            "codeformerweight": opts.code_former_weight,
            "denoising": getattr(p, 'denoising_strength', None),
            "eta": fixNum(p.eta),
            "sigmachurn": fixNum(p.s_churn),
            "sigmatmin": fixNum(p.s_tmin),
            "sigmatmax": fixNum(p.s_tmax),
            "sigmanoise": fixNum(p.s_noise)
        }

    def buildJson(grid, publish_gen_metadata, p):
        result = {}
        result['title'] = grid.title
        result['description'] = grid.description
        result['ext'] = grid.format
        if publish_gen_metadata:
            result['metadata'] = WebDataBuilder.getBaseParamData(p)
        axes = list()
        for axis in grid.axes:
            jAxis = {}
            jAxis['id'] = str(axis.id).lower()
            jAxis['title'] = axis.title
            jAxis['description'] = axis.description or ""
            values = list()
            for val in axis.values:
                jVal = {}
                jVal['key'] = str(val.key).lower()
                jVal['title'] = val.title
                jVal['description'] = val.description or ""
                jVal['show'] = val.show
                if publish_gen_metadata:
                    jVal['params'] = val.params
                values.append(jVal)
            jAxis['values'] = values
            axes.append(jAxis)
        result['axes'] = axes
        return json.dumps(result)

    def radioButtonHtml(name, id, descrip, label):
        return f'<input type="radio" class="btn-check" name="{name}" id="{str(id).lower()}" autocomplete="off" checked=""><label class="btn btn-outline-primary" for="{str(id).lower()}" title="{descrip}">{label}</label>\n'
    
    def axisBar(label, content):
        return f'<br><div class="btn-group" role="group" aria-label="Basic radio toggle button group">{label}:&nbsp;\n{content}</div>\n'

    def buildHtml(grid):
        assetDir = os.path.join(Script.BASEDIR, "assets")
        with open(os.path.join(assetDir, "page.html"), 'r') as referenceHtml:
            html = referenceHtml.read()
        xSelect = ""
        ySelect = ""
        x2Select = WebDataBuilder.radioButtonHtml('x2_axis_selector', f'x2_none', 'None', 'None')
        y2Select = WebDataBuilder.radioButtonHtml('y2_axis_selector', f'y2_none', 'None', 'None')
        content = '<div style="margin: auto; width: fit-content;"><table class="sel_table">\n'
        advancedSettings = ''
        primary = True
        for axis in grid.axes:
            try:
                axisDescrip = cleanForWeb(axis.description or '')
                trClass = "primary" if primary else "secondary"
                content += f'<tr class="{trClass}">\n<td>\n<h4>{axis.title}</h4>\n'
                advancedSettings += f'\n<h4>{axis.title}</h4><div class="timer_box">Auto cycle every <input style="width:30em;" autocomplete="off" type="range" min="0" max="360" value="0" class="form-range timer_range" id="range_tablist_{axis.id}"><label class="form-check-label" for="range_tablist_{axis.id}" id="label_range_tablist_{axis.id}">0 seconds</label></div>\nShow value: '
                content += f'<div class="axis_table_cell">{axisDescrip}</div></td>\n<td><ul class="nav nav-tabs" role="tablist" id="tablist_{axis.id}">\n'
                primary = not primary
                isFirst = axis.default is None
                for val in axis.values:
                    if axis.default is not None:
                        isFirst = str(axis.default) == str(val.key)
                    selected = "true" if isFirst else "false"
                    active = " active" if isFirst else ""
                    isFirst = False
                    descrip = cleanForWeb(val.description or '')
                    content += f'<li class="nav-item" role="presentation"><a class="nav-link{active}" data-bs-toggle="tab" href="#tab_{axis.id}__{val.key}" id="clicktab_{axis.id}__{val.key}" aria-selected="{selected}" role="tab" title="{val.title}: {descrip}">{val.title}</a></li>\n'
                    advancedSettings += f'&nbsp;<input class="form-check-input" type="checkbox" autocomplete="off" id="showval_{axis.id}__{val.key}" checked="true" onchange="javascript:toggleShowVal(\'{axis.id}\', \'{val.key}\')"> <label class="form-check-label" for="showval_{axis.id}__{val.key}" title="Uncheck this to hide \'{val.title}\' from the page.">{val.title}</label>'
                advancedSettings += f'&nbsp;&nbsp;<button class="submit" onclick="javascript:toggleShowAllAxis(\'{axis.id}\')">Toggle All</button>'
                content += '</ul>\n<div class="tab-content">\n'
                isFirst = axis.default is None
                for val in axis.values:
                    if axis.default is not None:
                        isFirst = str(axis.default) == str(val.key)
                    active = " active show" if isFirst else ""
                    isFirst = False
                    descrip = cleanForWeb(val.description or '')
                    content += f'<div class="tab-pane{active}" id="tab_{axis.id}__{val.key}" role="tabpanel"><div class="tabval_subdiv">{descrip}</div></div>\n'
            except Exception as e:
                raise RuntimeError(f"Failed to build HTML for axis '{axis.id}': {e}")
            content += '</div></td></tr>\n'
            xSelect += WebDataBuilder.radioButtonHtml('x_axis_selector', f'x_{axis.id}', axisDescrip, axis.title)
            ySelect += WebDataBuilder.radioButtonHtml('y_axis_selector', f'y_{axis.id}', axisDescrip, axis.title)
            x2Select += WebDataBuilder.radioButtonHtml('x2_axis_selector', f'x2_{axis.id}', axisDescrip, axis.title)
            y2Select += WebDataBuilder.radioButtonHtml('y2_axis_selector', f'y2_{axis.id}', axisDescrip, axis.title)
        content += '</table>\n<div class="axis_selectors">'
        content += WebDataBuilder.axisBar('X Axis', xSelect)
        content += WebDataBuilder.axisBar('Y Axis', ySelect)
        content += WebDataBuilder.axisBar('X Super-Axis', x2Select)
        content += WebDataBuilder.axisBar('Y Super-Axis', y2Select)
        content += '</div></div>\n'
        content += '<div><center><input class="form-check-input" type="checkbox" autocomplete="off" value="" id="autoScaleImages"> <label class="form-check-label" for="autoScaleImages">Auto-scale images to viewport width</label></center></div>'
        content += '<div style="margin: auto; width: fit-content;"><table id="image_table"></table></div>\n'
        html = html.replace("{TITLE}", grid.title).replace("{CLEAN_DESCRIPTION}", cleanForWeb(grid.description)).replace("{DESCRIPTION}", grid.description).replace("{CONTENT}", content).replace("{ADVANCED_SETTINGS}", advancedSettings).replace("{AUTHOR}", grid.author)
        return html

    def EmitWebData(path, grid, publish_gen_metadata, p):
        print("Building final web data...")
        os.makedirs(path, exist_ok=True)
        json = WebDataBuilder.buildJson(grid, publish_gen_metadata, p)
        with open(os.path.join(path, "data.js"), 'w') as f:
            f.write("rawData = " + json)
        assetDir = os.path.join(Script.BASEDIR, "assets")
        for f in ["bootstrap.min.css", "bootstrap.bundle.min.js", "proc.js", "jquery.min.js"]:
            shutil.copyfile(os.path.join(assetDir, f), os.path.join(path, f))
        html = WebDataBuilder.buildHtml(grid)
        with open(os.path.join(path, "index.html"), 'w') as f:
            f.write(html)
        print(f"Web file is now at {path}/index.html")

######################### Script class entrypoint #########################
class Script(scripts.Script):
    BASEDIR = scripts.basedir()
    VALIDATE_REPLACE = True

    def title(self):
        return "Generate Infinite-Axis Grid"

    def show(self, is_img2img):
        return True

    def ui(self, is_img2img):
        help_info = gr.HTML(value=f"<br>Confused/new? View <a style=\"border-bottom: 1px #00ffff dotted;\" href=\"{INF_GRID_README}\">the README</a> for usage instructions.<br><br>")
        do_overwrite = gr.Checkbox(value=False, label="Overwrite existing images (for updating grids)")
        generate_page = gr.Checkbox(value=True, label="Generate infinite-grid webviewer page")
        dry_run = gr.Checkbox(value=False, label="Do a dry run to validate your grid file")
        validate_replace = gr.Checkbox(value=True, label="Validate PromptReplace input")
        publish_gen_metadata = gr.Checkbox(value=True, label="Publish full generation metadata for viewing on-page")
        fast_skip = gr.Checkbox(value=False, label="Use more-performant skipping")
        # Maintain our own refreshable list of yaml files, to avoid all the oddities of other scripts demanding you drag files and whatever
        # Refresh code based roughly on how the base WebUI does refreshing of model files and all
        with gr.Row():
            grid_file = gr.Dropdown(value=None,label="Select grid definition file", choices=getNameList())
            def refresh():
                newChoices = getNameList()
                grid_file.choices = newChoices
                return gr.update(choices=newChoices)
            refresh_button = gr.Button(value=refresh_symbol, elem_id="infinity_grid_refresh_button")
            refresh_button.click(fn=refresh, inputs=[], outputs=[grid_file])
        return [help_info, do_overwrite, generate_page, dry_run, validate_replace, publish_gen_metadata, grid_file, refresh_button, fast_skip]

    def run(self, p, help_info, do_overwrite, generate_page, dry_run, validate_replace, publish_gen_metadata, grid_file, refresh_button, fast_skip):
        # Clean up default params
        p = copy(p)
        p.n_iter = 1
        p.batch_size = 1
        p.do_not_save_samples = True
        p.do_not_save_grid = True
        p.seed = processing.get_fixed_seed(p.seed)
        # Validate to avoid abuse
        if '..' in grid_file or grid_file == "":
            raise RuntimeError(f"Unacceptable filename '{grid_file}'")
        file = os.path.join(os.path.join(Script.BASEDIR, "assets"), grid_file)
        if not os.path.exists(file):
            raise RuntimeError(f"Non-existent file '{grid_file}'")
        # Parse and verify
        with open(file, 'r') as yamlContentText:
            try:
                yamlContent = yaml.safe_load(yamlContentText)
            except yaml.YAMLError as exc:
                raise RuntimeError(f"Invalid YAML in file '{grid_file}': {exc}")
        grid = GridFileHelper()
        grid.parseYaml(yamlContent, grid_file)
        # Now start using it
        folder = os.path.join(p.outpath_grids, grid_file.replace(".yml", ""))
        runner = GridRunner(grid, do_overwrite, folder, p, fast_skip)
        Script.VALIDATE_REPLACE = validate_replace
        runner.preprocess()
        with SettingsFixer():
            result = runner.run(dry_run)
        if generate_page:
            WebDataBuilder.EmitWebData(folder, grid, publish_gen_metadata, p)
        if dry_run:
            print("Infinite Grid dry run succeeded without error")
        if result is None:
            return Processed(p, list())
        return result
