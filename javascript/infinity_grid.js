/**
 * Stable Diffusion Infinity Grid Generator
 *
 * Author: Alex 'mcmonkey' Goodwin
 *
 * GitHub URL: https://github.com/mcmonkeyprojects/sd-infinity-grid-generator-script
 * Created: 2022/12/08
 * Last updated: 2022/12/08
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
    "Publish full generation metadata for viewing on-page": "If checked, any/all image metadata will be stored in the webpage's files, and the internal values of each axis. This is useful for viewing, but if you're sharing a generation where some details are private (eg exact prompt text) you'll want to uncheck this.",
    "Validate PromptReplace input": "If unchecked, will allow useless PromptReplace settings to be ignored. If checked, will error if the replace won't do anything."
}

ex_titles = Object.assign({}, ex_titles, new_titles);
titles = ex_titles;
