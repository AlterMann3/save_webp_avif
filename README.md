# Save WebP / AVIF
Custom node for ComfyUI to save images in **WebP** or **AVIF** format.

- Workflow metadata save/load (drap&drop) supported.
- AVIF subsampling: 4:4:4
- AVIF encoder speed is optimum: 6
- Multiple (batch) images supported.
- Custom filenames and date/time supported. (https://www.man7.org/linux/man-pages/man1/date.1.html)
- Quality 100 = Lossless.

<img src="assets/SaveWebpAvif_ComfyUI.png" width="350">

#
Installation for Portable ComfyUI:
- Install [ComfyUI Manager](https://github.com/Comfy-Org/ComfyUI-Manager) if it's not already installed, via `"install-manager-for-portable-version.bat"` file.
- Edit `"\ComfyUI_windows_portable\ComfyUI\user\__manager\config.ini"` file -> _"security_level = **weak**"_  
- Open `"ComfyUI Manager"` -> click `"Install via Git URL"` -> copy&paste this and confirm:
```
https://github.com/AlterMann3/save_webp_avif
```
- Restart ComfyUI.

#
If AVIF support is missing, run this command from your `"\ComfyUI_windows_portable\python_embeded\"` directory:
```
python.exe -m pip install -U pillow-avif-plugin
```
#

You can find node in: _`Add Node`_->_`image`_->_`💾 Save WebP / AVIF`_
