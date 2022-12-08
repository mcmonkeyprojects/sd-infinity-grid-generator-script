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

INF_GRID_README = "https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script"

class GridFileHelper:
    
    def getNameList():
        return glob.glob(scripts.basedir() + "/assets/*.yml")

class Script(scripts.Script):

    def title(self):
        return "Generate Infinite-Axis Grid"

    def show(self, is_img2img):
        return True


    def ui(self, is_img2img):
        help_info = gr.Label(label=f"Confused/new? View <a href=\"{INF_GRID_README}\">the README</a> for usage instructions.")
        use_jpg = gr.Checkbox(value=True, label="Save Grid Images As JPEG")
        grid_file = gr.Dropdown(value=None,label="Select grid definition file", choices=GridFileHelper.getNameList())
        # TODO
        return [help_info, use_jpg, grid_file]


    def run(self, p, use_jpg, grid_file):
        # TODO
        proc = process_images(p)
        return proc
