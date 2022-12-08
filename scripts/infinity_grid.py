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

import modules.scripts as scripts
import gradio as gr
import os
import glob
import yaml

from modules import images, shared, sd_models, sd_vae, sd_samplers
from modules.hypernetworks import hypernetwork
from modules.processing import process_images, Processed
from modules.shared import opts, cmd_opts, state

refresh_symbol = '\U0001f504'  # 🔄
INF_GRID_README = "https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script"

def getNameList():
    relPath = os.path.join(Script.BASEDIR, "assets")
    fileList = glob.glob(relPath + "/*.yml")
    justFileNames = list(map(lambda f: os.path.relpath(f, relPath), fileList))
    return justFileNames

def fixDict(d):
    if d is None:
        return None
    return {k.lower(): v for k, v in d.items()}

def cleanName(name):
    return name.lower().replace(' ', '')

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
    return getBestInList(name, sd_samplers.samplers_map.keys())

validModes = {
    "sampler": { "type": "text" },
    "seed": { "type": "integer" },
    "steps": { "type": "integer", "min": 0, "max": 200 },
    "cfgscale": { "type": "decimal", "min": 0, "max": 50 },
    "model": { "type": "text" },
    "vae": { "type": "text" },
    "width": { "type": "integer" },
    "height": { "type": "integer" },
    "hypernetwork": { "type": "text" },
    "hypernetworkstrength": { "type": "decimal", "min": 0, "max": 1 },
    "prompt": { "type": "text" },
    "negativeprompt": { "type": "text" },
    "varseed": { "type": "integer" },
    "varstrength": { "type": "decimal", "min": 0, "max": 1 },
    "clipskip": { "type": "integer", "min": 1, "max": 12 },
    "denoising": { "type": "decimal", "min": 0, "max": 1 },
    "eta": { "type": "decimal", "min": 0, "max": 1 },
    "sigmachurn": { "type": "decimal", "min": 0, "max": 1 },
    "sigmatmin": { "type": "decimal", "min": 0, "max": 1 },
    "sigmanoise": { "type": "decimal", "min": 0, "max": 1 },
    "etanoiseseeddelta": { "type": "integer" }
}

class GridFileHelper:

    gridTitle = None
    gridDescription = None

    def validateParams(params):
        for p,v in params.items():
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
            if modeType == "decimal":
                vFloat = float(v)
                if vFloat is None:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be a decimal number")
                min = mode.get("min")
                max = mode.get("max")
                if min is not None and vFloat < min:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be at least {min}")
                if max is not None and vFloat > max:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must not exceed {max}")
            if p == "model":
                if getModelFor(v) is None:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': model name unrecognized")
            if p == "hypernetwork":
                hnName = cleanName(v)
                if hnName != "none" and getHypernetworkFor(hnName) is None:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': hypernetwork name unrecognized")
            if p == "vae":
                vaeName = cleanName(v)
                if vaeName != "none" and vaeName != "auto" and getVaeFor(hnName) is None:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': VAE name unrecognized")
            if p == "sampler":
                if getSamplerFor(cleanName(v)) is None:
                    raise RuntimeError(f"Invalid parameter '{p}' as '{v}': sampler name unrecognized")
    def parseYaml(self, yamlContent, grid_file):
        yamlContent = fixDict(yamlContent)
        gridObj = fixDict(yamlContent.get("grid"))
        if gridObj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'grid' root key")
        gridTitle = gridObj.get("title")
        gridDescription = gridObj.get("description")
        if gridTitle is None or gridDescription is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing grid title or description in grid obj {gridObj}")
        gridParams = fixDict(gridObj.get("params"))
        if gridParams is not None:
            GridFileHelper.validateParams(gridParams)
        cleanDesc = gridDescription.replace('\n', ' ')
        print(f"Loaded grid file, title '{gridTitle}', description '{cleanDesc}'")
        return self

class Script(scripts.Script):

    BASEDIR = scripts.basedir()

    def title(self):
        return "Generate Infinite-Axis Grid"

    def show(self, is_img2img):
        return True

    def ui(self, is_img2img):
        help_info = gr.HTML(value=f"<br>Confused/new? View <a style=\"border-bottom: 1px #00ffff dotted;\" href=\"{INF_GRID_README}\">the README</a> for usage instructions.<br><br>")
        use_jpg = gr.Checkbox(value=True, label="Save Grid Images As JPEG")
        do_overwrite = gr.Checkbox(value=False, label="Overwrite existing images (for updating grids)")
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
        # TODO
        return [help_info, use_jpg, do_overwrite, grid_file, refresh_button]

    def run(self, p, help_info, use_jpg, do_overwrite, grid_file, refresh_button):
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
        helper = GridFileHelper()
        helper.parseYaml(yamlContent, grid_file)
        print("Starting...")
        # TODO
        proc = process_images(p)
        return proc
