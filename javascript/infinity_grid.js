/**
 * Stable Diffusion Infinity Grid Generator
 *
 * Author: Alex 'mcmonkey' Goodwin
 *
 * GitHub URL: https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script
 * Created: 2022/12/08
 * Last updated: 2023/02/19
 *
 * For usage help, view the README.md file in the extension root, or via the GitHub page.
 *
 */

// Title injection code referenced from d8ahazard's Dreambooth extension
ex_titles = titles;

new_titles = {
    "Select grid definition file": "Select the grid definition yaml file, in your '(extension)/assets' folder. Refer to the README for info.",
    "Overwrite existing images (for updating grids)": "If checked, any existing image files will be overwritten - this is useful if you want to redo the grid with completely different base settings. If unchecked, if an image already exists, it will be skipped - this is useful for adding new options to an existing grid.",
    "Generate infinite-grid webviewer page": "If checked, generate the webviewer page. If unchecked, won't generate. You can uncheck this for dryruns that don't need it, or to avoid overwriting customized pages.",
    "Do a dry run to validate your grid file": "If checked, no images will be rendered - it will just validate your YAML and all its content. Check the WebUI's console for any messages.",
    "Publish full generation metadata for viewing on-page": "If checked, any/all image metadata will be stored in the webpage's files, and the internal values of each axis. This is useful for viewing, but if you're sharing a generation where some details are private (eg exact prompt text) you'll want to uncheck this. Note that this doesn't change whether metadata gets stored in images or not, edit your Settings tab to configure that.",
    "Use more-performant skipping": "Only matters if you have 'skip: true' on any values - if checked, uses a method of skipping that improves performance but prevents validation of the skipped options.",
    "Validate PromptReplace input": "If unchecked, will allow useless PromptReplace settings to be ignored. If checked, will error if the replace won't do anything."
}

for (var i = 1; i <= 16; i++) {
    new_titles[`Axis ${i} Mode`] = "Select the desired mode / setting - ie what value it is that should be changing, for this axis. You have as many axes as you need, just select modes and more will be added as you go.";
    new_titles[`Axis ${i} Value`] = "Fill in values applicable to the mode, separated by commas. If it's a numeric mode, you can do for example '1, 2, 3'.";
}

ex_titles = Object.assign({}, ex_titles, new_titles);
titles = ex_titles;
