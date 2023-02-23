# This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.

import os
import glob
import yaml
import json
import shutil
import math
import re
from copy import copy

######################### Core Variables #########################

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
EXTRA_FOOTER = "..."
EXTRA_ASSETS = []
validModes = {}

######################### Hooks #########################

# hook(SingleGridCall)
gridCallInitHook: callable = None
# hook(SingleGridCall, paramName: str, value: any) -> bool
gridCallParamAddHook: callable = None
# hook(SingleGridCall, paramName: str, dry: bool)
gridCallApplyHook: callable = None
# hook(GridRunner)
gridRunnerPreRunHook: callable = None
# hook(GridRunner)
gridRunnerPreDryHook: callable = None
# hook(GridRunner, PassThroughObject, set: list(SingleGridCall)) -> ResultObject
gridRunnerRunPostDryHook: callable = None
# hook(PassThroughObject) -> dict
webDataGetBaseParamData: callable = None

######################### Utilities #########################
def getNameList():
    fileList = glob.glob(ASSET_DIR + "/*.yml")
    justFileNames = list(map(lambda f: os.path.relpath(f, ASSET_DIR), fileList))
    return justFileNames

def fixDict(d: dict):
    if d is None:
        return None
    if type(d) is not dict:
        raise RuntimeError(f"Value '{d}' is supposed to be submapping but isn't (it's plaintext, a list, or some other incorrect format). Did you typo the formatting?")
    return {str(k).lower(): v for k, v in d.items()}

def cleanForWeb(text: str):
    if text is None:
        return None
    if type(text) is not str:
        raise RuntimeError(f"Value '{text}' is supposed to be text but isn't (it's a datamapping, list, or some other incorrect format). Did you typo the formatting?")
    return text.replace('"', '&quot;')

def cleanId(id: str):
    return re.sub("[^a-z0-9]", "_", id.lower().strip())

def cleanName(name: str):
    return str(name).lower().replace(' ', '').replace('[', '').replace(']', '').strip()

def getBestInList(name: str, list: list):
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

def chooseBetterFileName(rawName: str, fullName: str):
    partialName = os.path.splitext(os.path.basename(fullName))[0]
    if '/' in rawName or '\\' in rawName or '.' in rawName or len(rawName) >= len(partialName):
        return rawName
    return partialName

def fixNum(num):
    if num is None or math.isinf(num) or math.isnan(num):
        return None
    return num

def expandNumericListRanges(inList, numType):
    outList = list()
    for i in range(0, len(inList)):
        rawVal = str(inList[i]).strip()
        if rawVal in ["..", "...", "...."]:
            if i < 2 or i + 1 >= len(inList):
                raise RuntimeError(f"Cannot use ellipses notation at index {i}/{len(inList)} - must have at least 2 values before and 1 after.")
            prior = outList[-1]
            doublePrior = outList[-2]
            after = numType(inList[i + 1])
            step = prior - doublePrior
            if (step < 0) != ((after - prior) < 0):
                raise RuntimeError(f"Ellipses notation failed for step {step} between {prior} and {after} - steps backwards.")
            count = int((after - prior) / step)
            for x in range(1, count):
                outList.append(prior + x * step)
        else:
            outList.append(numType(rawVal))
    return outList

######################### Value Modes #########################

class GridSettingMode:
    """
    Defines a custom parameter input mode for an Infinity Grid Generator.
    'dry' is True if the mode should be processed in dry runs, or False if it should be skipped.
    'type' is 'text', 'integer', 'decimal', or 'boolean'
    'apply' is a function to call taking (passthroughObject, value)
    'min' is for integer/decimal type, optional minimum value
    'max' is for integer/decimal type, optional maximum value
    'clean' is an optional function to call that takes (passthroughObject, value) and returns a cleaned copy of the value, or raises an error if invalid
    'valid_list' is for text type, an optional lambda that returns a list of valid values
    """
    def __init__(self, dry: bool, type: str, apply: callable, min: float = None, max: float = None, valid_list: callable = None, clean: callable = None):
        self.dry = dry
        self.type = type
        self.apply = apply
        self.min = min
        self.max = max
        self.clean = clean
        self.valid_list = valid_list

def registerMode(name: str, mode: GridSettingMode):
    mode.name = name
    validModes[cleanName(name)] = mode

######################### Validation #########################

def validateParams(grid, params: dict):
    for p,v in params.items():
        params[p] = validateSingleParam(p, grid.procVariables(v))

def applyField(name):
    def applier(p, v):
        setattr(p, name, v)
    return applier

def validateSingleParam(p: str, v):
    p = cleanName(p)
    mode = validModes.get(p)
    if mode is None:
        raise RuntimeError(f"Invalid grid parameter '{p}': unknown mode")
    modeType = mode.type
    if modeType == "integer":
        vInt = int(v)
        if vInt is None:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be an integer number")
        min = mode.min
        max = mode.max
        if min is not None and vInt < min:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be at least {min}")
        if max is not None and vInt > max:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must not exceed {max}")
        v = vInt
    elif modeType == "decimal":
        vFloat = float(v)
        if vFloat is None:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be a decimal number")
        min = mode.min
        max = mode.max
        if min is not None and vFloat < min:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be at least {min}")
        if max is not None and vFloat > max:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must not exceed {max}")
        v = vFloat
    elif modeType == "boolean":
        vClean = str(v).lower().strip()
        if vClean == "true":
            v = True
        elif vClean == "false":
            v = False
        else:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': must be either 'true' or 'false'")
    elif modeType == "text" and mode.valid_list is not None:
        validList = mode.valid_list()
        v = getBestInList(cleanName(v), validList)
        if v is None:
            raise RuntimeError(f"Invalid parameter '{p}' as '{v}': not matched to any entry in list {list(validList)}")
    if mode.clean is not None:
        return mode.clean(p, v)
    return v

######################### YAML Parsing and Processing #########################

class AxisValue:
    def __init__(self, axis, grid, key: str, val):
        self.axis = axis
        self.key = cleanId(str(key))
        if any(x.key == self.key for x in axis.values):
            self.key += f"__{len(axis.values)}"
        self.params = list()
        if isinstance(val, str):
            halves = val.split('=', maxsplit=1)
            if len(halves) != 2:
                raise RuntimeError(f"Invalid value '{key}': '{val}': not expected format")
            halves[0] = grid.procVariables(halves[0])
            halves[1] = grid.procVariables(halves[1])
            halves[1] = validateSingleParam(halves[0], halves[1])
            self.title = halves[1]
            self.params = { cleanName(halves[0]): halves[1] }
            self.description = None
            self.skip = False
            self.show = True
        else:
            self.title = grid.procVariables(val.get("title"))
            self.description = grid.procVariables(val.get("description"))
            self.skip = (str(grid.procVariables(val.get("skip")))).lower() == "true"
            self.params = fixDict(val.get("params"))
            self.show = (str(grid.procVariables(val.get("show")))).lower() != "false"
            if self.title is None or self.params is None:
                raise RuntimeError(f"Invalid value '{key}': '{val}': missing title or params")
            validateParams(grid, self.params)
    
    def __str__(self):
        return f"(title={self.title}, description={self.description}, params={self.params})"
    def __unicode__(self):
        return self.__str__()

class Axis:
    def buildFromListStr(self, id, grid, listStr):
        valueList = listStr.split("||" if "||" in listStr else ",")
        mode = validModes.get(cleanName(str(id)))
        if mode is None:
            raise RuntimeError(f"Invalid axis '{mode}': unknown mode")
        if mode.type == "integer":
            valueList = expandNumericListRanges(valueList, int)
        elif mode.type == "decimal":
            valueList = expandNumericListRanges(valueList, float)
        index = 0
        for val in valueList:
            try:
                index += 1
                self.values.append(AxisValue(self, grid, str(index), f"{id}={str(val).strip()}"))
            except Exception as e:
                raise RuntimeError(f"value '{val}' errored: {e}")

    def __init__(self, grid, id: str, obj):
        self.values = list()
        self.id = cleanId(str(id))
        if any(x.id == self.id for x in grid.axes):
            self.id += f"__{len(grid.axes)}"
        if isinstance(obj, str):
            self.title = id
            self.default = None
            self.description = ""
            self.buildFromListStr(id, grid, obj)
        else:
            self.title = grid.procVariables(obj.get("title"))
            self.default = grid.procVariables(obj.get("default"))
            if self.title is None:
                raise RuntimeError("missing title")
            self.description = grid.procVariables(obj.get("description"))
            valuesObj = obj.get("values")
            if valuesObj is None:
                raise RuntimeError("missing values")
            elif isinstance(valuesObj, str):
                self.buildFromListStr(id, grid, valuesObj)
            else:
                for key, val in valuesObj.items():
                    try:
                        self.values.append(AxisValue(self, grid, key, val))
                    except Exception as e:
                        raise RuntimeError(f"value '{key}' errored: {e}")

class GridFileHelper:
    def procVariables(self, text):
        if text is None:
            return None
        text = str(text)
        for key, val in self.variables.items():
            text = text.replace(key, val)
        return text

    def parseYaml(self, yamlContent: dict, grid_file: str):
        self.variables = dict()
        self.axes = list()
        yamlContent = fixDict(yamlContent)
        varsObj = fixDict(yamlContent.get("variables"))
        if varsObj is not None:
            for key, val in varsObj.items():
                self.variables[str(key).lower()] = str(val)
        gridObj = fixDict(yamlContent.get("grid"))
        if gridObj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'grid' root key")
        self.title = self.procVariables(gridObj.get("title"))
        self.description = self.procVariables(gridObj.get("description"))
        self.author = self.procVariables(gridObj.get("author"))
        self.format = self.procVariables(gridObj.get("format"))
        if self.title is None or self.description is None or self.author is None or self.format is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing grid title, author, format, or description in grid obj {gridObj}")
        self.params = fixDict(gridObj.get("params"))
        if self.params is not None:
            validateParams(self, self.params)
        axesObj = fixDict(yamlContent.get("axes"))
        if axesObj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'axes' root key")
        for id, axisObj in axesObj.items():
            try:
                self.axes.append(Axis(self, id, axisObj if isinstance(axisObj, str) else fixDict(axisObj)))
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
    def __init__(self, values: list):
        self.values = values
        self.skip = False
        for val in values:
            if val.skip:
                self.skip = True
        if gridCallInitHook is not None:
            gridCallInitHook(self)

    def flattenParams(self, grid: GridFileHelper):
        self.params = grid.params.copy() if grid.params is not None else dict()
        for val in self.values:
            for p, v in val.params.items():
                if gridCallParamAddHook is None or not gridCallParamAddHook(self, p, v):
                    self.params[p] = v

    def applyTo(self, p, dry: bool):
        for name, val in self.params.items():
            mode = validModes[cleanName(name)]
            if not dry or mode.dry:
                mode.apply(p, val)
        if gridCallApplyHook is not None:
            gridCallApplyHook(self, p, dry)

class GridRunner:
    def __init__(self, grid: GridFileHelper, doOverwrite: bool, basePath: str, p, fast_skip: bool):
        self.grid = grid
        self.totalRun = 0
        self.totalSkip = 0
        self.totalSteps = 0
        self.doOverwrite = doOverwrite
        self.basePath = basePath
        self.fast_skip = fast_skip
        self.p = p

    def buildValueSetList(self, axisList: list):
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

    def run(self, dry: bool):
        if gridRunnerPreRunHook is not None:
            gridRunnerPreRunHook(self)
        iteration = 0
        last = None
        for set in self.valueSets:
            if set.doSkip:
                continue
            iteration += 1
            if not dry:
                print(f'On {iteration}/{self.totalRun} ... Set: {set.data}, file {set.filepath}')
            p = copy(self.p)
            if gridRunnerPreDryHook is not None:
                gridRunnerPreDryHook(self)
            set.applyTo(p, dry)
            if dry:
                continue
            last = gridRunnerRunPostDryHook(self, p, set)
        return last

######################### Web Data Builders #########################

class WebDataBuilder():
    def buildJson(grid, publish_gen_metadata, p):
        result = {}
        result['title'] = grid.title
        result['description'] = grid.description
        result['ext'] = grid.format
        if publish_gen_metadata:
            result['metadata'] = None if webDataGetBaseParamData is None else webDataGetBaseParamData(p)
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
        with open(os.path.join(ASSET_DIR, "page.html"), 'r') as referenceHtml:
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
        html = html.replace("{TITLE}", grid.title).replace("{CLEAN_DESCRIPTION}", cleanForWeb(grid.description)).replace("{DESCRIPTION}", grid.description).replace("{CONTENT}", content).replace("{ADVANCED_SETTINGS}", advancedSettings).replace("{AUTHOR}", grid.author).replace("{EXTRA_FOOTER}", EXTRA_FOOTER)
        return html

    def EmitWebData(path, grid, publish_gen_metadata, p):
        print("Building final web data...")
        os.makedirs(path, exist_ok=True)
        json = WebDataBuilder.buildJson(grid, publish_gen_metadata, p)
        with open(os.path.join(path, "data.js"), 'w') as f:
            f.write("rawData = " + json)
        for f in ["bootstrap.min.css", "bootstrap.bundle.min.js", "proc.js", "jquery.min.js"] + EXTRA_ASSETS:
            shutil.copyfile(os.path.join(ASSET_DIR, f), os.path.join(path, f))
        html = WebDataBuilder.buildHtml(grid)
        with open(os.path.join(path, "index.html"), 'w') as f:
            f.write(html)
        print(f"Web file is now at {path}/index.html")

######################### Main Runner Function #########################

def runGridGen(passThroughObj, inputFile: str, outputFolderBase: str, outputFolderName: str = None, doOverwrite: bool = False, fastSkip: bool = False, generatePage: bool = True, publishGenMetadata: bool = True, dryRun: bool = False, manualPairs: list = None):
    grid = GridFileHelper()
    if manualPairs is None:
        fullInputPath = os.path.join(ASSET_DIR, inputFile)
        if not os.path.exists(fullInputPath):
            raise RuntimeError(f"Non-existent file '{inputFile}'")
        # Parse and verify
        with open(fullInputPath, 'r') as yamlContentText:
            try:
                yamlContent = yaml.safe_load(yamlContentText)
            except yaml.YAMLError as exc:
                raise RuntimeError(f"Invalid YAML in file '{inputFile}': {exc}")
        grid.parseYaml(yamlContent, inputFile)
    else:
        grid.title = outputFolderName
        grid.description = ""
        grid.variables = dict()
        grid.author = "Unspecified"
        grid.format = "png"
        grid.axes = list()
        grid.params = None
        for i in range(0, int(len(manualPairs) / 2)):
            key = manualPairs[i * 2]
            if isinstance(key, str) and key != "":
                try:
                    grid.axes.append(Axis(grid, key, manualPairs[i * 2 + 1]))
                except Exception as e:
                    raise RuntimeError(f"Invalid axis {(i + 1)} '{key}': errored: {e}")
    # Now start using it
    if outputFolderName.strip() == "":
        outputFolderName = inputFile.replace(".yml", "")
    folder = os.path.join(outputFolderBase, outputFolderName)
    runner = GridRunner(grid, doOverwrite, folder, passThroughObj, fastSkip)
    runner.preprocess()
    if generatePage:
        WebDataBuilder.EmitWebData(folder, grid, publishGenMetadata, passThroughObj)
    result = runner.run(dryRun)
    if dryRun:
        print("Infinite Grid dry run succeeded without error")
    return result
