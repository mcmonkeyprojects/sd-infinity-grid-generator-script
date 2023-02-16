# Stable Diffusion Infinity Grid Generator

![img](github/megagrid_ref.png)

### Concept

Extension for the [AUTOMATIC1111 Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) that generates infinite-dimensional grids.

An "infinite axis grid" is like an X/Y plot grid, but with, well, more axes on it. Of course, monitors are 2D, so this is implemented in practice by generating a webpage that lets you select which two primary axes to display, and then choose the current value for each of the other axes.

### Goals and Use Cases

The primary goal is to let people generate their own fancy grids to explore how different settings affect their renders in a convenient form.

Another goal of this system is to develop educational charts, to provide a universal answer to the classic question of "what does (X) setting do? But what about with (Y)?" - [The MegaGrid](https://sd.mcmonkey.org/megagrid/). There is a built in ability to add description text to fields, for the specific purpose of enhancing educational page output.

### Pros/Cons

The advantage of this design is it allows you to rapidly compare the results of different combinations of settings, without having to wait to for generation times for each specific sub-grid as-you-go - you just run it all once in advance (perhaps overnight for a large run), and then after that browse through it in realtime.

The disadvantage is that time to generate a grid is exponential - if you have 5 samplers, 5 seeds, 5 step counts, 5 CFG scales... that's 5^4, or 625 images. Add another variable with 5 options and now it's 3125 images. You can see how this quickly jumps from a two minute render to a two hour render.

--------------

### Table of Contents

- [Examples](#Examples)
- [Status](#Status)
- [Installation](#Installation)
- [Usage](#Usage)
    - [1: Grid Definition File](#1-grid-definition-file)
    - [2: Grid Content Generation via WebUI](#2-grid-content-generation-via-webui)
    - [3: Using The Output](#3-using-the-output)
    - [Expanding Later](#expanding-later)
- [Credits](#credits)
- [Common Issues](#common-issues)
- [License](#License)

--------------

### Examples

Here's a big MegaGrid using almost every mode option in one, with detailed educational descriptions on every part: https://sd.mcmonkey.org/megagrid/

Here's a very small web demo you can try to test how the output looks and works: https://mcmonkeyprojects.github.io/short_example and you can view the generated asset files for that demo [here](https://github.com/mcmonkeyprojects/mcmonkeyprojects.github.io/tree/master/short_example).

![img](github/simple_ref.png)

--------------

### Status

Current overall project status (as of Feb 2023): **Works well, actively maintained**. Has been generally well tested.

--------------

### Installation

- You must have the [AUTOMATIC1111 Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) already installed and working. Refer to that project's readme for help with that.
- Open the WebUI, go to to the `Extensions` tab
- -EITHER- Option **A**:
    - go to the `Available` tab with
    - click `Load from` (with the default list)
    - Scroll down to find `Infinity Grid Generator`, or use `CTRL+F` to find it
- -OR- Option **B**:
    - Click on `Install from URL`
    - Copy/paste this project's URL into the `URL for extension's git repository` textbox: `https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script`
- Click `Install`
- Restart or reload the WebUI

--------------

### Usage

Usage comes in three main steps:
- [1: Build a grid definition](#1-grid-definition-file)
- [2: Generate its contents](#2-grid-content-generation-via-webui)
- [3: View/use the generated output page](#3-using-the-output)
- You can also [expand your grid later](#expanding-later)

--------------

### 1: Grid Definition File

![img](github/yaml_settings_blur.png)

- Grid information is defined by **YAML files**, in the extension folder under `assets`. Find the `assets/short_example.yml` file to see an example of the full format.

**If you do not want to follow an example file:**
- You can **create new files** in the assets directory (as long as the `.yml` extension stays), or copy/paste an example file and edit it. I recommend you do not edit the actual example file directly to avoid git issues.
- I recommend editing with a **good text editor**, such as *VS Code* or *Notepad++*. Don't use *MS Word* or *Windows Notepad* as those might cause trouble.
- All text inputs allow for **raw HTML**, so, be careful. You can use `&lt;` for `<`, and `&gt;` for `>`, `&#58;` for `:`, and `&amp;` for `&`.
- The file must have key `grid`, with subkey `title` and `description` to define the file data.
    - It must also have `format` as `jpg` or `png`
    - It can optionally also have `params` to specify any default parameters.
- The file can optionally have key `variables` with subkey/value pairs as replacements, for example `(type): waffle` - then later in a param value you can use `a picture of a (type)` to automatically fill the variable. These can be in any format you desire, as they are simple text replacements. They apply to all values, including titles, descriptions, and params (this was added for [valconius in issue #16](https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script/issues/16)).
- The file must have key `axes` to define the list of axes. This is a map-list key - meaning, add subkeys to create a list of each axis.
    - The simplest format for an axis is a setting name as the key and a comma-separated list of values inside.
        - For example, `seed: 1, 2, 3` is a valid and complete axis.
        - If commas may be problematic, you many instead use two pipes `||` to separate values - for example `prompt: 1girl, booru style, commas || 1boy, more commas, etc`. If `||` is used, commas will be ignored for splitting
    - Each axis must have a `title`, and `values`. It can optionally have a `description`.
        - You can also optionally have `default: (value_id)` to set the default selected tab.
        - There are two ways to do a value in the value list:
            - Option 1: just do like `steps=10` ... this will set title to `10`, and param `steps` to value `10`, with no description.
            - Option 2: Add a submapping with key `title`, and optional `description`, and then `params` as a sub map of parameters like `steps: 10`
                - A value with a full format can be set to skip rendering via adding `skip: true`. This is useful for eg if some values are only valid in certain combinations, you can do runs with some skipped. Skipped values will be kept in the HTML output.
                - A value may specify `show: false` to default uncheck the 'Show value' advanced option.

Micro example:
```yml
grid:
    title: Tiny example
    author: someone
    description: This is just to show core format. View the example `.yml` files in assets for better examples.
    format: jpg
axes:
    sampler: Euler, DDIM
    seed: 1, 2, 3
```

- Names and descriptions can always be whatever you want, as HTML text.
- **Settings supported for parameters**:
    - `Sampler`, `Seed`, `Steps`, `CFGscale`, `Model`, `VAE`, `Width`, `Height`, `Prompt`, `NegativePrompt`, `VarSeed`, `VarStrength`, `ClipSkip`, `Denoising`, `ETA`, `SigmaChurn`, `SigmaTmin`, `SigmaTmax`, `SigmaNoise`, `OutWidth`, `OutHeight`, `RestoreFaces`, `CodeFormerWeight`, `PromptReplace`
    - All names are **case insensitive and spacing insensitive**. That means `CFG scale`, `cfgscale`, `CFGSCALE`, etc. are all read as the same.
    - Inputs where possible also similarly insensitive, including model names.
    - Inputs have error checking at the start, to avoid the risk of it working fine until 3 hours into a very big grid run.
    - `OutWidth`/`OutHeight` are optional, and if specified, will rescale images to a specific size when saving. This is useful to save filespace by outputting to a smaller res.
    - `PromptReplace` can be used like `PromptReplace: some_tag = new text here`. Note the `=` symbol to separate the original text with the new text. That will change a prompt of for example `my prompt with some_tag stuff` to `my prompt with new text here stuff`
        - Unlike other modes, the PromptReplace is case-sensitive - if you use capitals in your prompt, you need capitals in your replace matcher.
        - If you want multiple replacements in one value, you can just do `PromptReplace` and `Prompt Replace` and `Prompt    Replace` and etc. as they are all parsed the same.
    - Note that `Model` and `VAE` are **global settings**, and as such you should not have an axis where some values specify one of those params but others don't, as this will cause an unpredictable model selection for the values that lack specificity.
    - `RestoreFaces` has multiple input formats: `true` to enable, `false` to disable, `GFPGan` to use GFPGan, `CodeFormer` to use CodeFormer
- Note that it will be processed from bottom to top
    - so if you have  first `samplers` DDIM and Euler, then `steps` 20 and 10, then `seeds` 1 and 2, it will go in this order:
        - Sampler=DDIM, Steps=20, Seed=1
        - Sampler=DDIM, Steps=20, Seed=**2**
        - Sampler=DDIM, Steps=**10**, Seed=1
        - Sampler=DDIM, Steps=10, Seed=2
        - Sampler=**Euler**, Steps=20, Seed=1
        - Sampler=Euler, Steps=20, Seed=2
        - Sampler=Euler, Steps=10, Seed=1
        - Sampler=Euler, Steps=10, Seed=2
    - So, things that take time to load, like `Model`, should be put near the top, so they don't have to be loaded repeatedly.

#### Supported Extensions
- Dynamic Thresholding (CFG Scale Fix): <https://github.com/mcmonkeyprojects/sd-dynamic-thresholding>
    - Adds options: `DynamicThresholdEnable` (bool: `true` or `false`), `DynamicThresholdMimicScale` (number), `DynamicThresholdThresholdPercentile` (number, 0-100), `DynamicThresholdMimicMode` (any of `Constant`, `Linear Down`, `Cosine Down`, `Half Cosine Down`, `Linear Up`, `Cosine Up`, `Half Cosine Up`, `Power Up`), `DynamicThresholdCfgMode` (same options as mimic mode), `DynamicThresholdMimicScaleMinimum` (number), `DynamicThresholdCfgScaleMinimum` (number), `DynamicThresholdPowerValue` (number)

--------------

### 2: Grid Content Generation via WebUI

![img](github/webui_ref.png)

- Open the WebUI
- Go to the `txt2img` or `img2img` tab
- At the bottom of the page, find the `Script` selection box, and select `Generate Infinite-Axis Grid`
- Select options at will. You can hover your mouse over each option for extra usage information.
- Select your grid definition file from earlier.
    - If it's not there, you might just need to hit the Refresh button on the right side.
    - If it's still not, there double check that your file is in the `assets/` folder of the extension, and that it has a proper `.yml` extension.
- Hit your `Generate` button (the usual big orange one at the top), and wait.
- The output folder will be named based on your `.yml` file's name.

--------------

### 3: Using The Output

![img](github/files_ref.png)

- Find the `index.html` file
    - It's normally in `(your grid output directory)/(filename)/index.html`
        - The example file might output to `outputs/grids/short_example/index.html`
- Open the HTML file in a browser. Enjoy.
- If you want to share the content, just copy/paste the whole folder into a webserver somewhere.
    - Or upload to github and make GitHub.io pages host it for you. [See example here](https://github.com/mcmonkeyprojects/mcmonkeyprojects.github.io)
- You have a few different clickable options:
    - `Show descriptions of axes and values`: if you used descriptions, you can uncheck this box to hide them. Helps save space for direct viewing.
    - `Auto-scale images to viewport width`: this is handy for a few different scenarios
        - A: if your images are small and your screen is big, checking this option makes them bigger
        - B: if your images are so big they're going off the edge, checking this option makes them smaller
        - C: if checked, you can zoom in/out of the page using your browser zoom (CTRL + Mouse Wheel) to change the UI size without affecting the image size
            - if unchecked, you can zoom in/out to change the size of the images.
    - `Advanced Settings`: when clicked, it will open a dropdown with more advanced settings
        - ![img](github/advanced_settings_ref.png)
        - `Auto cycle every (x) seconds`: you can set these to non-zero values to the grid automatically change settings over time. For example, if you set your "Seed" option to "3 seconds", then every 3 seconds the seed will change (cycling between the options you have in order). This was suggested by [itswhateverman in issue #2](https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script/issues/2).
        - `Show value`: you can uncheck any box to hide a value from the grid. Helps if you want to ignore some of the values and get a clean grid of just the ones you care about. This was suggested by [piyarsquare in issue #4](https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script/issues/4).
    - You can also click on any image to view it fullscreen and see its metadata (if included in output). While in this mode, you can use arrow keys to quick navigate between images, or press Escape to close (This suggested by [itswhateverman in issue #5](https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script/issues/5) and [issue #17](https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script/issues/17)).
    - You can also set the `X Super-axis` and `Y Super-axis` to unique axes to get a grid-of-grids!
        - ![img](github/super_axis_demo.png)

--------------

### Expanding Later

If you want to add more content to a grid you already made, you can do that:

- Use the same `yml` file.
- You can add new values to an axis freely.
- If you remove values, they will be excluded from the output but pre-existing generated images won't be removed.
- You can add axes, but you'll have to regenerate all images if so.
    - Probably save as a new filename in that case.
- If you're just adding a new value, make sure to leave `overwriting existing images` off.

----------------------

### Credits

- This design was partially inspired by the "XYZ Plot" script by "xrypgame".
- Sections of code are referenced from the WebUI itself, and its default "X/Y Plot" script.
- Some sections of code were referenced from various other relevant sources, for example the Dreambooth extension by d8ahazard was referenced for a JavaScript code trick (titles override).
- Some sections of code were referenced from, well, random StackOverflow answers and a variety of other googled up documentation and answer sites. I haven't kept track of them, but I'm glad to live in a world where so many developers are happy and eager to help each other learn and grow. So, thank you to all members of the FOSS community!
- Thanks to the authors of all issues labeled as [Completed](https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script/issues?q=label%3ACompleted).
- Thanks to StabilityAI, RunwayML, CompVis for Stable Diffusion, and the researchers whose work was incorporated.
- Thanks to AUTOMATIC1111 and the long list of contributors for the WebUI.

----------------------

### Common Issues

```
  File "stable-diffusion-webui\modules\images.py", line 508, in _atomically_save_image
    image_format = Image.registered_extensions()[extension]
KeyError: '.jpg'
```
If you have this error, just hit generate again. I'm not sure why it happens, it just does at random sometimes on the first time the WebUI starts up. It seems to happen when you use "OutWidth"/"OutHeight" settings and is prevented by running any generation without a custom out-resolution. Might be some required initialization is getting skipped when an image is rescaled?

----------------------

### Licensing pre-note:

This is an open source project, provided entirely freely, for everyone to use and contribute to.

If you make any changes that could benefit the community as a whole, please contribute upstream.

### The short of the license is:

You can do basically whatever you want, except you may not hold any developer liable for what you do with the software.

### The long version of the license follows:

The MIT License (MIT)

Copyright (c) 2022-2023 Alex "mcmonkey" Goodwin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
