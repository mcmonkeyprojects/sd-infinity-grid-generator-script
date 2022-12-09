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
from copy import copy
from modules import images, shared, sd_models, sd_vae, sd_samplers, scripts
from modules.processing import process_images, Processed
from modules.shared import opts, cmd_opts, state
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
    return {str(k).lower(): v for k, v in d.items()}

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
    sd_models.reload_model_weights(shared.sd_model, getModelFor(v))
    p.sd_model = shared.sd_model
def applyVae(p, v):
    vaeName = cleanName(v)
    if vaeName not in ["auto", "none"]:
        vaeName = getVaeFor(vaeName)
    sd_vae.reload_vae_weights(None, vaeName)
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
    hypernetwork.apply_strength = float(v)
def applyPrompt(p, v):
    p.prompt = v
def applyNegativePrompt(p, v):
    p.negative_prompt = v
def applyVarSeed(p, v):
    p.subseed = int(v)
def applyVarSeedStrength(p, v):
    p.subseed_strength = int(v)
def applyClipSkip(p, v):
    opts.data["CLIP_stop_at_last_layers"] = int(v)
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
    "promptreplace": { "dry": True, "type": "text", "apply": applyPromptReplace }
}

######################### Validation #########################
def validateParams(params):
    for p,v in params.items():
        validateSingleParam(p, v)

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
        elif p == "model":
            if getModelFor(v) is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': model name unrecognized")
        elif p == "hypernetwork":
            hnName = cleanName(v)
            if hnName != "none" and getHypernetworkFor(hnName) is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': hypernetwork name unrecognized")
        elif p == "vae":
            vaeName = cleanName(v)
            if vaeName != "none" and vaeName != "auto" and getVaeFor(hnName) is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': VAE name unrecognized")
        elif p == "sampler":
            if getSamplerFor(cleanName(v)) is None:
                raise RuntimeError(f"Invalid parameter '{p}' as '{v}': sampler name unrecognized")

######################### YAML Parsing and Processing #########################
class AxisValue:
    def parseObj(self, axis, key, val):
        self.axis = axis
        self.key = key
        self.params = list()
        if isinstance(val, str):
            halves = val.split('=', maxsplit=1)
            if len(halves) != 2:
                raise RuntimeError(f"Invalid value '{key}': '{val}': not expected format")
            validateSingleParam(halves[0], halves[1])
            self.title = halves[1]
            self.params = { cleanName(halves[0]): halves[1] }
            self.description = None
        else:
            self.title = val.get("title")
            self.description = val.get("description")
            self.params = fixDict(val.get("params"))
            if self.title is None or self.params is None:
                raise RuntimeError(f"Invalid value '{key}': '{val}': missing title or params")
            validateParams(self.params)
        return self
    
    def __str__(self):
        return f"(title={self.title}, description={self.description}, params={self.params})"
    def __unicode__(self):
        return self.__str__()

class Axis:
    def parseObj(self, id, obj):
        self.values = list()
        self.id = id
        self.title = obj.get("title")
        if self.title is None:
            raise RuntimeError(f"Invalid axis '{id}': missing title")
        self.description = obj.get("description")
        valuesObj = obj.get("values")
        if valuesObj is None:
            raise RuntimeError(f"Invalid axis '{id}': missing values")
        for key, val in valuesObj.items():
            self.values.append(AxisValue().parseObj(self, key, val))
        return self

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
            self.axes.append(Axis().parseObj(id, fixDict(axisObj)))
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
    def __init__(self, grid, doOverwrite, basePath, p):
        self.grid = grid
        self.totalRun = 0
        self.totalSkip = 0
        self.totalSteps = 0
        self.doOverwrite = doOverwrite
        self.basePath = basePath
        self.p = p

    def buildValueSetList(axisList):
        result = list()
        if len(axisList) == 0:
            return result
        curAxis = axisList[0]
        if len(axisList) == 1:
            for val in curAxis.values:
                newList = list()
                newList.append(val)
                result.append(SingleGridCall(newList))
            return result
        nextAxisList = axisList[1::]
        for obj in GridRunner.buildValueSetList(nextAxisList):
            for val in curAxis.values:
                newList = obj.values.copy()
                newList.append(val)
                result.append(SingleGridCall(newList))
        return result

    def preprocess(self):
        self.valueSets = GridRunner.buildValueSetList(list(reversed(self.grid.axes)))
        print(f'Have {len(self.valueSets)} unique value sets, will go into {self.basePath}')
        for set in self.valueSets:
            set.filepath = os.path.join(self.basePath, '/'.join(list(map(lambda v: cleanName(v.key), set.values))))
            set.data = ', '.join(list(map(lambda v: f"{v.axis.title}={v.title}", set.values)))
            set.flattenParams(self.grid)
            set.doSkip = not self.doOverwrite and os.path.exists(set.filepath + "." + self.grid.format)
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
            set.applyTo(p, dry)
            if dry:
                continue
            processed = process_images(p)
            if len(processed.images) != 1:
                raise RuntimeError(f"Something went wrong! Image gen '{set.data}' produced {len(processed.images)} images, which is wrong")
            os.makedirs(os.path.dirname(set.filepath), exist_ok=True)
            if hasattr(p, 'inf_grid_out_width') and hasattr(p, 'inf_grid_out_height'):
                processed.images[0] = processed.images[0].resize((p.inf_grid_out_width, p.inf_grid_out_height), resample=images.LANCZOS)
            images.save_image(processed.images[0], path=os.path.dirname(set.filepath), basename="", forced_filename=os.path.basename(set.filepath), save_to_dirs=False, extension=self.grid.format, p=p, prompt=p.prompt, seed=processed.seed)
            last = processed
        return last

class SettingsFixer():
    def __enter__(self):
        self.CLIP_stop_at_last_layers = opts.CLIP_stop_at_last_layers
        self.hypernetwork = opts.sd_hypernetwork
        self.model = shared.sd_model

    def __exit__(self, exc_type, exc_value, tb):
        sd_models.reload_model_weights(self.model)
        hypernetwork.load_hypernetwork(self.hypernetwork)
        hypernetwork.apply_strength()
        opts.data["CLIP_stop_at_last_layers"] = self.CLIP_stop_at_last_layers

######################### Web Data Builders #########################
class WebDataBuilder():
    def buildJson(grid):
        result = {}
        result['title'] = grid.title
        result['description'] = grid.description
        result['ext'] = grid.format
        axes = list()
        for axis in grid.axes:
            jAxis = {}
            jAxis['id'] = axis.id
            jAxis['title'] = axis.title
            jAxis['description'] = axis.description or ""
            values = list()
            for val in axis.values:
                jVal = {}
                jVal['key'] = val.key
                jVal['title'] = val.title
                jVal['description'] = val.description or ""
                values.append(jVal)
            jAxis['values'] = values
            axes.append(jAxis)
        result['axes'] = axes
        return json.dumps(result)

    def buildHtml(grid):
        assetDir = os.path.join(Script.BASEDIR, "assets")
        with open(os.path.join(assetDir, "page.html"), 'r') as referenceHtml:
            html = referenceHtml.read()
        xSelect = ""
        ySelect = ""
        content = '<div style="margin: auto; width: fit-content;"><table class="sel_table">\n'
        primary = True
        for axis in grid.axes:
            axisDescrip = axis.description or ''
            trClass = "primary" if primary else "secondary"
            content += f'<tr class="{trClass}">\n<td>\n<h4>{axis.title}</h4>\n{axisDescrip}</td>\n<td><ul class="nav nav-tabs" role="tablist">\n'
            primary = not primary
            isFirst = True
            for val in axis.values:
                selected = "true" if isFirst else "false"
                active = " active" if isFirst else ""
                isFirst = False
                descrip = val.description or ''
                content += f'<li class="nav-item" role="presentation"><a class="nav-link{active}" data-bs-toggle="tab" href="#tab_{axis.id}__{val.key}" id="clicktab_{axis.id}__{val.key}" aria-selected="{selected}" role="tab" title="{val.title}: {descrip}">{val.title}</a></li>\n'
            content += '</ul>\n<div class="tab-content">\n'
            isFirst = True
            for val in axis.values:
                active = " active show" if isFirst else ""
                isFirst = False
                descrip = val.description or ''
                content += f'<div class="tab-pane{active}" id="tab_{axis.id}__{val.key}" role="tabpanel">{descrip}</div>\n'
            content += '</div></td></tr>\n'
            xSelect += f'<input type="radio" class="btn-check" name="x_axis_selector" id="x_{axis.id}" autocomplete="off" checked=""><label class="btn btn-outline-primary" for="x_{axis.id}" title="{axisDescrip}">{axis.title}</label>\n'
            ySelect += f'<input type="radio" class="btn-check" name="y_axis_selector" id="y_{axis.id}" autocomplete="off" checked=""><label class="btn btn-outline-primary" for="y_{axis.id}" title="{axisDescrip}">{axis.title}</label>\n'
        content += '</table>\n'
        content += f'<center><br><div class="btn-group" role="group" aria-label="Basic radio toggle button group">X Axis:&nbsp;\n{xSelect}</div>\n'
        content += f'<br><div class="btn-group" role="group" aria-label="Basic radio toggle button group">Y Axis:&nbsp;\n{ySelect}</div></center></div>\n'
        content += '<div style="margin: auto; width: fit-content;"><table id="image_table"></table></div>\n'
        html = html.replace("{TITLE}", grid.title).replace("{DESCRIPTION}", grid.description).replace("{CONTENT}", content).replace("{AUTHOR}", grid.author)
        return html

    def EmitWebData(path, grid):
        print("Building final web data...")
        json = WebDataBuilder.buildJson(grid)
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
        dry_run = gr.Checkbox(value=False, label="Do a dry run to validate your grid file")
        validate_replace = gr.Checkbox(value=True, label="Validate PromptReplace input")
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
        return [help_info, do_overwrite, dry_run, validate_replace, grid_file, refresh_button]

    def run(self, p, help_info, do_overwrite, dry_run, validate_replace, grid_file, refresh_button):
        # Clean up default params
        p = copy(p)
        p.n_iter = 1
        p.batch_size = 1
        p.do_not_save_samples = True
        p.do_not_save_grid = True
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
        runner = GridRunner(grid, do_overwrite, folder, p)
        Script.VALIDATE_REPLACE = validate_replace
        runner.preprocess()
        with SettingsFixer():
            result = runner.run(dry_run)
        if dry_run:
            print("Infinite Grid dry run succeeded without error")
            return Processed(p, list())
        WebDataBuilder.EmitWebData(folder, grid)
        if result is None:
            return Processed(p, list())
        return result
