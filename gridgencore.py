# This file is part of Infinity Grid Generator, view the README.md at https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script for more information.

import os, glob, yaml, json, shutil, math, re, time
from copy import copy
from PIL import Image
from git import Repo
from yamlinclude import YamlIncludeConstructor

######################### Core Variables #########################

ASSET_DIR = os.path.dirname(__file__) + "/assets"
EXTRA_FOOTER = "..."
EXTRA_ASSETS = []
VERSION = None
valid_modes = {}
IMAGES_CACHE = None

######################### Hooks #########################

# hook(SingleGridCall)
grid_call_init_hook: callable = None
# hook(SingleGridCall, param_name: str, value: any) -> bool
grid_call_param_add_hook: callable = None
# hook(SingleGridCall, param_name: str, dry: bool)
grid_call_apply_hook: callable = None
# hook(GridRunner)
grid_runner_pre_run_hook: callable = None
# hook(GridRunner)
grid_runner_pre_dry_hook: callable = None
# hook(GridRunner, PassThroughObject, set: SingleGridCall) -> ResultObject
grid_runner_post_dry_hook: callable = None
# hook(GridRunner, SingleGridCall) -> int
grid_runner_count_steps: callable = None
# hook(PassThroughObject) -> dict
webdata_get_base_param_data: callable = None

######################### Utilities #########################

def escape_html(text: str):
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def clean_file_path(fn: str):
    fn = fn.replace('\\', '/')
    while '//' in fn:
        fn = fn.replace('//', '/')
    return fn

def get_version():
    global VERSION
    if VERSION is not None:
        return VERSION
    try:
        repo = Repo(os.path.dirname(__file__))
        VERSION = repo.head.commit.hexsha[:8]
    except Exception:
        VERSION = "Unknown"
    return VERSION

def list_image_files():
    global IMAGES_CACHE
    if IMAGES_CACHE is not None:
        return IMAGES_CACHE
    image_dir = clean_file_path(ASSET_DIR + "/images")
    IMAGES_CACHE = list()
    for path, _, files in os.walk(image_dir):
        for name in files:
            _, ext = os.path.splitext(name)
            if ext in [".jpg", ".png", ".webp"]:
                fn = path + "/" + name
                fn = clean_file_path(fn).replace(image_dir, '')
                while fn.startswith('/'):
                    fn = fn[1:]
                IMAGES_CACHE.append(fn)
    return IMAGES_CACHE

def clear_caches():
    global IMAGES_CACHE
    IMAGES_CACHE = None

def get_name_list():
    file_list = glob.glob(ASSET_DIR + "/*.yml")
    just_file_names = sorted(list(map(lambda f: os.path.relpath(f, ASSET_DIR), file_list)))
    return just_file_names

def fix_dict(d: dict):
    if d is None:
        return None
    if type(d) is not dict:
        raise RuntimeError(f"Value '{d}' is supposed to be submapping but isn't (it's plaintext, a list, or some other incorrect format). Did you typo the formatting?")
    return {str(k).lower(): v for k, v in d.items()}

def clean_for_web(text: str):
    if text is None:
        return None
    if type(text) is not str:
        raise RuntimeError(f"Value '{text}' is supposed to be text but isn't (it's a datamapping, list, or some other incorrect format). Did you typo the formatting?")
    return text.replace('"', '&quot;')

def clean_id(id: str):
    return re.sub("[^a-z0-9]", "_", id.lower().strip())

def clean_mode(id: str):
    return re.sub("[^a-z]", "", id.lower().strip())

def clean_name(name: str):
    return str(name).lower().replace(' ', '').replace('[', '').replace(']', '').strip()

def get_best_in_list(name: str, list: list):
    backup = None
    best_len = 999
    name = clean_name(name)
    for list_val in list:
        list_val_clean = clean_name(list_val)
        if list_val_clean == name:
            return list_val
        if name in list_val_clean:
            if len(list_val_clean) < best_len:
                backup = list_val
                best_len = len(list_val_clean)
    return backup

def choose_better_file_name(raw_name: str, full_name: str):
    partial_name = os.path.splitext(os.path.basename(full_name))[0]
    if '/' in raw_name or '\\' in raw_name or '.' in raw_name or len(raw_name) >= len(partial_name):
        return raw_name
    return partial_name

def fix_num(num):
    if num is None or math.isinf(num) or math.isnan(num):
        return None
    return num

def expand_numeric_list_ranges(in_list, num_type):
    out_list = list()
    for i in range(0, len(in_list)):
        raw_val = str(in_list[i]).strip()
        if raw_val in ["..", "...", "...."]:
            if i < 2 or i + 1 >= len(in_list):
                raise RuntimeError(f"Cannot use ellipses notation at index {i}/{len(in_list)} - must have at least 2 values before and 1 after.")
            prior = out_list[-1]
            double_prior = out_list[-2]
            after = num_type(in_list[i + 1])
            step = prior - double_prior
            if (step < 0) != ((after - prior) < 0):
                raise RuntimeError(f"Ellipses notation failed for step {step} between {prior} and {after} - steps backwards.")
            count = int((after - prior) / step)
            for x in range(1, count):
                out_list.append(prior + x * step)
        else:
            out_list.append(num_type(raw_val))
    return out_list

######################### Value Modes #########################

class GridSettingMode:
    """
    Defines a custom parameter input mode for an Infinity Grid Generator.
    'dry' is True if the mode should be processed in dry runs, or False if it should be skipped.
    'type' is 'text', 'integer', 'decimal', or 'boolean'
    'apply' is a function to call taking (passthroughObject, value)
    'min' is for integer/decimal type, optional minimum value
    'max' is for integer/decimal type, optional maximum value
    'valid_list' is for text type, an optional lambda that returns a list of valid values
    'clean' is an optional function to call that takes (passthroughObject, value) and returns a cleaned copy of the value, or raises an error if invalid
    'parse_list' is an optional function to call that takes a List and returns a List, to apply any special pre-processing for list-format inputs.
    """
    def __init__(self, dry: bool, type: str, apply: callable, min: float = None, max: float = None, valid_list: callable = None, clean: callable = None, parse_list: callable = None):
        self.dry = dry
        self.type = type
        self.apply = apply
        self.min = min
        self.max = max
        self.clean = clean
        self.valid_list = valid_list
        self.parse_list = parse_list

def registerMode(name: str, mode: GridSettingMode):
    mode.name = name
    valid_modes[clean_name(name)] = mode

######################### Validation #########################

def validate_params(grid, params: dict):
    for p,v in params.items():
        params[p] = validate_single_param(p, grid.proc_variables(v))

def apply_field(name: str):
    def applier(p, v):
        setattr(p, name, v)
    return applier

def apply_field_as_image_data(name: str):
    def applier(p, v):
        file_name = get_best_in_list(v, list_image_files())
        if file_name is None:
            raise RuntimeError("Invalid parameter '{p}' as '{v}': image file does not exist")
        path = ASSET_DIR + "/images/" + file_name
        image = Image.open(path)
        setattr(p, name, image)
    return applier

def validate_single_param(p: str, v):
    orig_v = v
    p = clean_mode(p)
    mode = valid_modes.get(p)
    if mode is None:
        raise RuntimeError(f"Invalid grid parameter '{p}': unknown mode")
    mode_type = mode.type
    if mode_type == "integer":
        v_int = int(v)
        if v_int is None:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must be an integer number")
        min = mode.min
        max = mode.max
        if min is not None and v_int < min:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must be at least {min}")
        if max is not None and v_int > max:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must not exceed {max}")
        v = v_int
    elif mode_type == "decimal":
        v_float = float(v)
        if v_float is None:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must be a decimal number")
        min = mode.min
        max = mode.max
        if min is not None and v_float < min:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must be at least {min}")
        if max is not None and v_float > max:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must not exceed {max}")
        v = v_float
    elif mode_type == "boolean":
        v_clean = str(v).lower().strip()
        if v_clean == "true":
            v = True
        elif v_clean == "false":
            v = False
        else:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': must be either 'true' or 'false'")
    elif mode_type == "text" and mode.valid_list is not None:
        valid_list = mode.valid_list()
        v = get_best_in_list(clean_name(v), valid_list)
        if v is None:
            raise RuntimeError(f"Invalid parameter '{p}' as '{orig_v}': not matched to any entry in list {list(valid_list)}")
    if mode.clean is not None:
        return mode.clean(p, v)
    return v

######################### YAML Parsing and Processing #########################

class GridYamlLoader(yaml.SafeLoader):
    pass
YamlIncludeConstructor.add_to_loader_class(loader_class=GridYamlLoader, base_dir=ASSET_DIR)

class AxisValue:
    def __init__(self, axis, grid, key: str, val):
        self.axis = axis
        self.key = clean_id(str(key))
        if any(x.key == self.key for x in axis.values):
            self.key += f"__{len(axis.values)}"
        self.params = list()
        if isinstance(val, str):
            halves = val.split('=', maxsplit=1)
            if len(halves) != 2:
                raise RuntimeError(f"Invalid value '{key}': '{val}': not expected format")
            self.skip = False
            halves[0] = grid.proc_variables(halves[0])
            halves[1] = grid.proc_variables(halves[1])
            try:
                halves[1] = validate_single_param(halves[0], halves[1])
            except RuntimeError:
                if grid.skip_invalid:
                    self.skip = True
                else:
                    raise
            self.title = halves[1]
            self.params = { clean_mode(halves[0]): halves[1] }
            self.description = None
            self.show = True
            self.path = clean_name(self.key)
        else:
            self.title = grid.proc_variables(val.get("title"))
            self.description = grid.proc_variables(val.get("description"))
            self.skip = (str(grid.proc_variables(val.get("skip")))).lower() == "true"
            self.params = fix_dict(val.get("params"))
            self.show = (str(grid.proc_variables(val.get("show")))).lower() != "false"
            self.path = str(val.get("path") or clean_name(self.key))
            if self.title is None or self.params is None:
                raise RuntimeError(f"Invalid value '{key}': '{val}': missing title or params")
            if not self.skip:
                try:
                    validate_params(grid, self.params)
                except RuntimeError:
                    if grid.skip_invalid:
                        self.skip = True
                    else:
                        raise
    
    def __str__(self):
        return f"(title={self.title}, description={self.description}, params={self.params})"
    def __unicode__(self):
        return self.__str__()

class Axis:
    def build_from_list_str(self, id, grid, list_str):
        is_split_by_double_pipe = "||" in list_str
        values_list = list_str.split("||" if is_split_by_double_pipe else ",")
        self.mode_name = clean_name(str(id))
        self.mode = valid_modes.get(clean_mode(self.mode_name))
        if self.mode is None:
            raise RuntimeError(f"Invalid axis mode '{self.mode}' from '{id}': unknown mode")
        if self.mode.type == "integer":
            values_list = expand_numeric_list_ranges(values_list, int)
        elif self.mode.type == "decimal":
            values_list = expand_numeric_list_ranges(values_list, float)
        index = 0
        if self.mode.parse_list is not None:
            if self.mode_name.contains("promptreplace"):
                values_list = self.mode.parse_list(values_list, self.mode_name)
            else:
                values_list = self.mode.parse_list(values_list)
        for val in values_list:
            try:
                if isinstance(val, dict):
                    self.values.append(AxisValue(self, grid, str(index), val))
                    continue
                val = str(val).strip()
                index += 1
                if is_split_by_double_pipe and val == "" and index == len(values_list):
                    continue
                self.values.append(AxisValue(self, grid, str(index), f"{id}={val}"))
            except Exception as e:
                raise RuntimeError(f"value '{val}' errored: {e}")

    def __init__(self, grid, id: str, obj):
        self.raw_id = id
        self.values = list()
        self.id = clean_id(str(id))
        if any(x.id == self.id for x in grid.axes):
            self.id += f"__{len(grid.axes)}"
        if isinstance(obj, str):
            self.title = id
            self.default = None
            self.description = ""
            self.build_from_list_str(id, grid, obj)
        else:
            self.title = grid.proc_variables(obj.get("title"))
            self.default = grid.proc_variables(obj.get("default"))
            if self.title is None:
                raise RuntimeError("missing title")
            self.description = grid.proc_variables(obj.get("description"))
            values_obj = obj.get("values")
            if values_obj is None:
                raise RuntimeError("missing values")
            elif isinstance(values_obj, str):
                self.build_from_list_str(id, grid, values_obj)
            else:
                for key, val in values_obj.items():
                    try:
                        self.values.append(AxisValue(self, grid, key, val))
                    except Exception as e:
                        raise RuntimeError(f"value '{key}' errored: {e}")

class GridFileHelper:
    def proc_variables(self, text):
        if text is None:
            return None
        text = str(text)
        for key, val in self.variables.items():
            text = text.replace(key, val)
        return text
    
    def read_grid_direct(self, key: str):
        return self.grid_obj.get(key)
    
    def read_str_from_grid(self, key: str):
        return self.proc_variables(self.read_grid_direct(key))

    def parse_yaml(self, yaml_content: dict, grid_file: str):
        self.variables = dict()
        self.axes = list()
        yaml_content = fix_dict(yaml_content)
        vars_obj = fix_dict(yaml_content.get("variables"))
        if vars_obj is not None:
            for key, val in vars_obj.items():
                self.variables[str(key).lower()] = str(val)
        self.grid_obj = fix_dict(yaml_content.get("grid"))
        if self.grid_obj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'grid' root key")
        self.title = self.read_str_from_grid("title")
        self.description = self.read_str_from_grid("description")
        self.stylesheet = self.read_str_from_grid("stylesheet") or ''
        self.author = self.read_str_from_grid("author")
        self.format = self.read_str_from_grid("format")
        self.out_path = self.grid_obj.get("outpath")
        self.skip_invalid = self.read_grid_direct("skip_invalid") or getattr(self, 'skip_invalid', False)
        if self.title is None or self.description is None or self.author is None or self.format is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing grid title, author, format, or description in grid obj {self.grid_obj}")
        self.params = fix_dict(self.grid_obj.get("params"))
        if self.params is not None:
            validate_params(self, self.params)
        axes_obj = fix_dict(yaml_content.get("axes"))
        if axes_obj is None:
            raise RuntimeError(f"Invalid file {grid_file}: missing basic 'axes' root key")
        for id, axis_obj in axes_obj.items():
            try:
                self.axes.append(Axis(self, id, axis_obj if isinstance(axis_obj, str) else fix_dict(axis_obj)))
            except Exception as e:
                raise RuntimeError(f"Invalid axis '{id}': errored: {e}")
        total_count = 1
        for axis in self.axes:
            total_count *= len(axis.values)
        if total_count <= 0:
            raise RuntimeError(f"Invalid file {grid_file}: something went wrong ... is an axis empty? total count is {total_count} for {len(self.axes)} axes")
        clean_desc = self.description.replace('\n', ' ')
        print(f"Loaded grid file, title '{self.title}', description '{clean_desc}', with {len(self.axes)} axes... combines to {total_count} total images")
        return self

######################### Actual Execution Logic #########################

class SingleGridCall:
    def __init__(self, values: list):
        self.values = values
        self.skip = False
        for val in values:
            if val.skip:
                self.skip = True
        if grid_call_init_hook is not None:
            grid_call_init_hook(self)

    def flatten_params(self, grid: GridFileHelper):
        self.grid = grid
        self.params = grid.params.copy() if grid.params is not None else dict()
        for val in self.values:
            for p, v in val.params.items():
                if grid_call_param_add_hook is None or not grid_call_param_add_hook(self, p, v):
                    self.params[p] = v

    def apply_to(self, p, dry: bool):
        for name, val in self.params.items():
            mode = valid_modes[clean_mode(name)]
            if not dry or mode.dry:
                mode.apply(p, val)
        if grid_call_apply_hook is not None:
            grid_call_apply_hook(self, p, dry)

class GridRunner:
    def __init__(self, grid: GridFileHelper, do_overwrite: bool, base_path: str, p, fast_skip: bool):
        self.grid = grid
        self.total_run = 0
        self.total_skip = 0
        self.total_steps = 0
        self.do_overwrite = do_overwrite
        self.base_path = base_path
        self.fast_skip = fast_skip
        self.p = p
        grid.min_width = None
        grid.min_height = None
        grid.initial_p = p
        self.last_update = []

    def update_live_file(self, new_file: str):
        t_now = time.time()
        self.last_update = [x for x in self.last_update if t_now - x['t'] < 20]
        self.last_update.append({'f': new_file, 't': t_now})
        with open(self.base_path + '/last.js', 'w', encoding="utf-8") as f:
            update_str = '", "'.join([x['f'] for x in self.last_update])
            f.write(f'window.lastUpdated = ["{update_str}"]')

    def build_value_set_list(self, axis_list: list):
        result = list()
        if len(axis_list) == 0:
            return result
        cur_axis = axis_list[0]
        if len(axis_list) == 1:
            for val in cur_axis.values:
                if not val.skip or not self.fast_skip:
                    new_list = list()
                    new_list.append(val)
                    result.append(SingleGridCall(new_list))
            return result
        next_axis_list = axis_list[1::]
        for obj in self.build_value_set_list(next_axis_list):
            for val in cur_axis.values:
                if not val.skip or not self.fast_skip:
                    new_list = obj.values.copy()
                    new_list.append(val)
                    result.append(SingleGridCall(new_list))
        return result

    def preprocess(self):
        self.value_sets = self.build_value_set_list(list(reversed(self.grid.axes)))
        print(f'Have {len(self.value_sets)} unique value sets, will go into {self.base_path}')
        for set in self.value_sets:
            set.filepath = self.base_path + '/' + '/'.join(list(map(lambda v: v.path, set.values)))
            set.data = ', '.join(list(map(lambda v: f"{v.axis.title}={v.title}", set.values)))
            set.flatten_params(self.grid)
            set.do_skip = set.skip or (not self.do_overwrite and os.path.exists(set.filepath + "." + self.grid.format))
            if set.do_skip:
                self.total_skip += 1
            else:
                self.total_run += 1
                self.total_steps += grid_runner_count_steps(self, set) if grid_runner_count_steps is not None else 1
        print(f"Skipped {self.total_skip} files, will run {self.total_run} files, for {self.total_steps} total steps")

    def run(self, dry: bool):
        if grid_runner_pre_run_hook is not None:
            grid_runner_pre_run_hook(self)
        iteration = 0
        last = None
        for set in self.value_sets:
            if set.do_skip:
                continue
            iteration += 1
            if not dry:
                print(f'On {iteration}/{self.total_run} ... Set: {set.data}, file {set.filepath}')
            p = copy(self.p)
            if grid_runner_pre_dry_hook is not None:
                grid_runner_pre_dry_hook(self)
            set.apply_to(p, dry)
            if dry:
                continue
            try:
                last = grid_runner_post_dry_hook(self, p, set)
            except FileNotFoundError as e:
                if e.strerror == 'The filename or extension is too long' and hasattr(e, 'winerror') and e.winerror == 206:
                    print(f"\n\n\nOS Error: {e.strerror} - see this article to fix that: https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/The-Windows-10-default-path-length-limitation-MAX-PATH-is-256-characters.html \n\n\n")
                raise e
            self.update_live_file(set.filepath + "." + self.grid.format)
        return last

######################### Web Data Builders #########################

class WebDataBuilder():
    def build_json(grid: GridFileHelper, publish_gen_metadata: bool, p, dry_run: bool):
        def get_axis(axis: str):
            id = grid.read_str_from_grid(axis)
            if id is None:
                return ''
            id = str(id).lower()
            if id == 'none':
                return 'none'
            possible = [x.id for x in grid.axes if x.raw_id == id]
            if len(possible) == 0:
                raise RuntimeError(f"Cannot find axis '{id}' for axis default '{axis}'... valid: {[x.raw_id for x in grid.axes]}")
            return possible[0]
        show_descrip = grid.read_grid_direct('show descriptions')
        result = {
            'title': grid.title,
            'description': grid.description,
            'ext': grid.format,
            'min_width': grid.min_width,
            'min_height': grid.min_height,
            'defaults': {
                'show_descriptions': True if show_descrip is None else show_descrip,
                'autoscale': grid.read_grid_direct('autoscale') or False,
                'sticky': grid.read_grid_direct('sticky') or False,
                'sticky_labels': grid.read_grid_direct('sticky labels') or False,
                'x': get_axis('x axis'),
                'y': get_axis('y axis'),
                'x2': get_axis('x super axis'),
                'y2': get_axis('y super axis')
            }
        }
        if not dry_run:
            result['will_run'] = True
        if publish_gen_metadata:
            result['metadata'] = None if webdata_get_base_param_data is None else webdata_get_base_param_data(p)
        axes = list()
        for axis in grid.axes:
            j_axis = {
                'id': str(axis.id).lower(),
                'title': axis.title,
                'description': axis.description or ""
            }
            exported_paths = {}
            values = list()
            for val in axis.values:
                if val.path in exported_paths:
                    continue
                exported_paths[val.path] = val
                j_val = {
                    'key': str(val.key).lower(),
                    'path': str(val.path),
                    'title': val.title,
                    'description': val.description or "",
                    'show': val.show
                }
                if publish_gen_metadata:
                    j_val['params'] = val.params
                values.append(j_val)
            j_axis['values'] = values
            axes.append(j_axis)
        result['axes'] = axes
        return json.dumps(result)

    def radio_button_html(name, id, descrip, label):
        return f'<input type="radio" class="btn-check" name="{name}" id="{str(id).lower()}" autocomplete="off" checked=""><label class="btn btn-outline-primary" for="{str(id).lower()}" title="{descrip}">{escape_html(label)}</label>\n'

    def axis_bar(label, content):
        return f'<br><div class="btn-group" role="group" aria-label="Basic radio toggle button group">{label}:&nbsp;\n{content}</div>\n'

    def build_html(grid):
        with open(ASSET_DIR + "/page.html", 'r', encoding="utf-8") as reference_html:
            html = reference_html.read()
        x_select = ""
        y_select = ""
        x2Select = WebDataBuilder.radio_button_html('x2_axis_selector', f'x2_none', 'None', 'None')
        y2Select = WebDataBuilder.radio_button_html('y2_axis_selector', f'y2_none', 'None', 'None')
        content = '<div style="margin: auto; width: fit-content;"><table class="sel_table">\n'
        advanced_settings = ''
        primary = True
        for axis in grid.axes:
            try:
                axis_descrip = clean_for_web(axis.description or '')
                tr_class = "primary" if primary else "secondary"
                content += f'<tr class="{tr_class}">\n<td>\n<h4>{escape_html(axis.title)}</h4>\n'
                advanced_settings += f'\n<h4>{axis.title}</h4><div class="timer_box">Auto cycle every <input style="width:30em;" autocomplete="off" type="range" min="0" max="360" value="0" class="form-range timer_range" id="range_tablist_{axis.id}"><label class="form-check-label" for="range_tablist_{axis.id}" id="label_range_tablist_{axis.id}">0 seconds</label></div>\nShow value: '
                axis_class = "axis_table_cell"
                if len(axis_descrip.strip()) == 0:
                    axis_class += " emptytab"
                content += f'<div class="{axis_class}">{axis_descrip}</div></td>\n<td><ul class="nav nav-tabs" role="tablist" id="tablist_{axis.id}">\n'
                primary = not primary
                is_first = axis.default is None
                exported_paths = {}
                for val in axis.values:
                    if val.path in exported_paths:
                        continue
                    exported_paths[val.path] = val
                    if axis.default is not None:
                        is_first = str(axis.default) == str(val.key)
                    selected = "true" if is_first else "false"
                    active = " active" if is_first else ""
                    is_first = False
                    descrip = clean_for_web(val.description or '')
                    content += f'<li class="nav-item" role="presentation"><a class="nav-link{active}" data-bs-toggle="tab" href="#tab_{axis.id}__{val.key}" id="clicktab_{axis.id}__{val.key}" aria-selected="{selected}" role="tab" title="{escape_html(val.title)}: {descrip}">{escape_html(val.title)}</a></li>\n'
                    advanced_settings += f'&nbsp;<input class="form-check-input" type="checkbox" autocomplete="off" id="showval_{axis.id}__{val.key}" checked="true" onchange="javascript:toggleShowVal(\'{axis.id}\', \'{val.key}\')"> <label class="form-check-label" for="showval_{axis.id}__{val.key}" title="Uncheck this to hide \'{escape_html(val.title)}\' from the page.">{escape_html(val.title)}</label>'
                advanced_settings += f'&nbsp;&nbsp;<button class="submit" onclick="javascript:toggleShowAllAxis(\'{axis.id}\')">Toggle All</button>'
                content += '</ul>\n<div class="tab-content">\n'
                is_first = axis.default is None
                for val in axis.values:
                    if axis.default is not None:
                        is_first = str(axis.default) == str(val.key)
                    active = " active show" if is_first else ""
                    is_first = False
                    descrip = clean_for_web(val.description or '')
                    if len(descrip.strip()) == 0:
                        active += " emptytab"
                    content += f'<div class="tab-pane{active}" id="tab_{axis.id}__{val.key}" role="tabpanel"><div class="tabval_subdiv">{descrip}</div></div>\n'
            except Exception as e:
                raise RuntimeError(f"Failed to build HTML for axis '{axis.id}': {e}")
            content += '</div></td></tr>\n'
            x_select += WebDataBuilder.radio_button_html('x_axis_selector', f'x_{axis.id}', axis_descrip, axis.title)
            y_select += WebDataBuilder.radio_button_html('y_axis_selector', f'y_{axis.id}', axis_descrip, axis.title)
            x2Select += WebDataBuilder.radio_button_html('x2_axis_selector', f'x2_{axis.id}', axis_descrip, axis.title)
            y2Select += WebDataBuilder.radio_button_html('y2_axis_selector', f'y2_{axis.id}', axis_descrip, axis.title)
        content += '</table>\n<div class="axis_selectors">'
        content += WebDataBuilder.axis_bar('X Axis', x_select)
        content += WebDataBuilder.axis_bar('Y Axis', y_select)
        content += WebDataBuilder.axis_bar('X Super-Axis', x2Select)
        content += WebDataBuilder.axis_bar('Y Super-Axis', y2Select)
        content += '</div></div>\n'
        html = html.replace("{TITLE}", grid.title).replace("{CLEAN_DESCRIPTION}", clean_for_web(grid.description)).replace("{DESCRIPTION}", grid.description).replace("{CONTENT}", content).replace("{ADVANCED_SETTINGS}", advanced_settings).replace("{AUTHOR}", grid.author).replace("{EXTRA_FOOTER}", EXTRA_FOOTER).replace("{VERSION}", get_version())
        return html

    def emit_web_data(path: str, grid, publish_gen_metadata: bool, p, yaml_content: dict, dry_run: bool):
        print("Building final web data...")
        os.makedirs(path, exist_ok=True)
        json = WebDataBuilder.build_json(grid, publish_gen_metadata, p, dry_run)
        if not dry_run:
            with open(path + '/last.js', 'w', encoding="utf-8") as f:
                f.write("window.lastUpdated = []")
        with open(path + "/data.js", 'w', encoding="utf-8") as f:
            f.write("rawData = " + json)
        with open(path + "/config.yml", 'w', encoding="utf-8") as f:
            yaml.dump(yaml_content, f, sort_keys=False, default_flow_style=False, width=1000)
        for f in ["bootstrap.min.css", "jsgif.js", "bootstrap.bundle.min.js", "proc.js", "jquery.min.js", "styles.css", "placeholder.png"] + EXTRA_ASSETS:
            shutil.copyfile(ASSET_DIR + "/" + f, path + "/" + f)
        with open(ASSET_DIR + "/styles-user.css", 'r', encoding="utf-8") as style:
            with open(path + "/styles-user.css", 'w', encoding="utf-8") as f:
                f.write(style.read() + '\n' + (grid.stylesheet or ''))
        html = WebDataBuilder.build_html(grid)
        with open(path + "/index.html", 'w', encoding="utf-8") as f:
            f.write(html)
        print(f"Web file is now at {path}/index.html")
        return json

######################### Main Runner Function #########################

def run_grid_gen(pass_through_obj, input_file: str, output_folder_base: str, output_folder_name: str = None, do_overwrite: bool = False,
               fast_skip: bool = False, generate_page: bool = True, publish_gen_metadata: bool = True, dry_run: bool = False, manual_pairs: list = None, allow_includes: bool = True, skip_invalid: bool = False):
    grid = GridFileHelper()
    grid.stylesheet = ''
    grid.skip_invalid = skip_invalid
    yaml_content = None
    if manual_pairs is None:
        full_input_path = ASSET_DIR + "/" + input_file
        if not os.path.exists(full_input_path):
            raise RuntimeError(f"Non-existent file '{input_file}'")
        # Parse and verify
        with open(full_input_path, 'r', encoding="utf-8") as yaml_content_text:
            try:
                if allow_includes:
                    yaml_content = yaml.load(yaml_content_text, Loader=GridYamlLoader)
                else:
                    yaml_content = yaml.safe_load(yaml_content_text)
            except yaml.YAMLError as exc:
                raise RuntimeError(f"Invalid YAML in file '{input_file}': {exc}")
        grid.parse_yaml(yaml_content, input_file)
    else:
        grid.title = output_folder_name
        grid.description = ""
        grid.variables = dict()
        grid.author = "Unspecified"
        grid.format = "png"
        grid.axes = list()
        grid.params = None
        grid.grid_obj = {}
        yaml_content = {
            'grid': {
                'title': grid.title,
                'description': grid.description,
                'format': grid.format,
                'author': grid.author
            },
            'axes': {}
        }
        for i in range(0, int(len(manual_pairs) / 2)):
            key = manual_pairs[i * 2]
            if isinstance(key, str) and key.strip() != "":
                try:
                    val = manual_pairs[i * 2 + 1]
                    grid.axes.append(Axis(grid, key, val))
                    yaml_key = key
                    duplicates = 1
                    while yaml_key in yaml_content['axes']:
                        duplicates += 1
                        yaml_key = f"{key} {duplicates}"
                    yaml_content['axes'][yaml_key] = val
                except Exception as e:
                    raise RuntimeError(f"Invalid axis {(i + 1)} '{key}': errored: {e}")
    # Now start using it
    if output_folder_name.strip() == "":
        if grid.out_path is None:
            output_folder_name = input_file.replace(".yml", "")
        else:
            output_folder_name = grid.out_path.strip()
    if os.path.isabs(output_folder_name):
        folder = output_folder_name
    else:
        folder = output_folder_base + "/" + output_folder_name
    runner = GridRunner(grid, do_overwrite, folder, pass_through_obj, fast_skip)
    runner.preprocess()
    if generate_page:
        json = WebDataBuilder.emit_web_data(folder, grid, publish_gen_metadata, pass_through_obj, yaml_content, dry_run)
    result = runner.run(dry_run)
    if dry_run:
        print("Infinite Grid dry run succeeded without error")
    else:
        json = json.replace('"will_run": true, ', '')
        with open(folder + "/data.js", 'w', encoding="utf-8") as f:
            f.write("rawData = " + json)
        os.remove(folder + "/last.js")
    return result
