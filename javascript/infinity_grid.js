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
    "Save Grid Images As JPEG": "If checked, images in the infinity grid will be simple JPEG files. These use less space, but will be missing metadata. If unchecked, images will be PNG files, which have metadata or other custom settings, at the cost of using much more filespace.",
    "Select grid definition file": "Select the grid definition yaml file, in your '(extension)/assets' folder. Refer to the README for info."
}

ex_titles = Object.assign({}, ex_titles, new_titles);
titles = ex_titles;
