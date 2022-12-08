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

from modules import images
from modules.processing import process_images, Processed
from modules.processing import Processed
from modules.shared import opts, cmd_opts, state

refresh_symbol = '\U0001f504'  # 🔄
INF_GRID_README = "https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script"

class GridFileHelper:
    
    def getNameList():
        relPath = os.path.join(Script.BASEDIR, "assets")
        fileList = glob.glob(relPath + "/*.yml")
        justFileNames = list(map(lambda f: os.path.relpath(f, relPath), fileList))
        print(f"rel {relPath} files {fileList} justName {justFileNames}")
        return justFileNames

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
            grid_file = gr.Dropdown(value=None,label="Select grid definition file", choices=GridFileHelper.getNameList())
            def refresh():
                newChoices = GridFileHelper.getNameList()
                grid_file.choices = newChoices
                return gr.update(choices=newChoices)
            refresh_button = gr.Button(value=refresh_symbol, elem_id="infinity_grid_refresh_button")
            refresh_button.click(fn=refresh, inputs=[], outputs=[grid_file])
        # TODO
        return [help_info, use_jpg, do_overwrite, grid_file, refresh_button]

    def run(self, p, help_info, use_jpg, do_overwrite, grid_file, refresh_button):
        # TODO
        proc = process_images(p)
        return proc
