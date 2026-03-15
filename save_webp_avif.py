import os
import re
import json
import numpy as np
from datetime import datetime
from PIL import Image

# Check AVIF plugin availability
try:
    import pillow_avif  # noqa: F401
    AVIF_SUPPORTED = True
except Exception:
    AVIF_SUPPORTED = False

# Respect CLI metadata disable flag
try:
    from comfy.cli_args import args
except Exception:
    class _Args:
        disable_metadata = False
    args = _Args()

class SaveWebpAvif:
    """Save node for WebP and AVIF with ComfyUI workflow metadata support."""

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"
    type = "output"
    output_formats = [".webp", ".avif"]
    
    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "output")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "CUI(%y%m%d_%H%M)"}),
                "output_format": (cls.output_formats, {"default": ".avif"}),
                "quality": ("INT", {"default": 90, "min": 1, "max": 100}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def build_filename_from_prefix(self, prefix, timestamp):
        """Apply strftime formatting if prefix contains % tokens."""
        if "%" in prefix:
            try:
                return timestamp.strftime(prefix)
            except Exception:
                pass
        return prefix

    def get_latest_counter(self, folder_path, filename_prefix, counter_digits=3, output_format='.avif'):
        """Find highest counter value and return next value to prevent overwriting."""
        counter = 1

        if not os.path.exists(folder_path):
            return counter

        try:
            files = os.listdir(folder_path)
            ext = output_format.lower()
            pattern = rf"{re.escape(filename_prefix)}.*?_(\d{{{counter_digits}}}){re.escape(ext)}"

            counters = []
            for file in files:
                if file.startswith(filename_prefix) and file.endswith(ext):
                    match = re.match(pattern, file)
                    if match:
                        counters.append(int(match.group(1)))

            if counters:
                counter = max(counters) + 1
        except Exception as e:
            print(f"[save_webp_avif] error finding latest counter: {e}")

        return counter

    def get_metadata_exif(self, img, prompt, extra_pnginfo=None):
        """Build EXIF metadata using Make (0x010f) and ImageDescription (0x010e)."""
        try:
            if args.disable_metadata:
                return None
        except Exception:
            pass

        metadata = {}
        if prompt is not None:
            metadata["prompt"] = prompt
        if extra_pnginfo is not None:
            metadata.update(extra_pnginfo)

        if not metadata:
            return None

        exif = img.getexif()

        if "prompt" in metadata:
            exif[0x010f] = "Prompt: " + json.dumps(metadata["prompt"])

        if "workflow" in metadata:
            exif[0x010e] = "Workflow: " + json.dumps(metadata["workflow"])

        return exif.tobytes()

    def save_single_image(self, img, path, fmt, quality, prompt, extra_pnginfo):
        """Save a single image with format-specific settings."""
        kwargs = {}

        exif_data = self.get_metadata_exif(img, prompt, extra_pnginfo)
        if exif_data is not None:
            kwargs["exif"] = exif_data

        kwargs["quality"] = int(quality) if quality else 90

        if fmt.lower() == ".avif":
            if not AVIF_SUPPORTED:
                raise RuntimeError("AVIF selected but pillow-avif-plugin not available.")
            kwargs["speed"] = 6
            kwargs["subsampling"] = "4:4:4"

        elif fmt.lower() == ".webp":
            if kwargs["quality"] >= 100:
                kwargs["lossless"] = True

        img.save(path, **kwargs)

    def save_images(self, images, filename_prefix="CUI(%y%m%d_%H%M)", quality=90,
                    output_format=".avif", prompt=None, extra_pnginfo=None):

        timestamp = datetime.now()
        filename_base = self.build_filename_from_prefix(filename_prefix, timestamp)
        os.makedirs(self.output_dir, exist_ok=True)

        counter = self.get_latest_counter(
            self.output_dir, filename_base, counter_digits=3, output_format=output_format
        )

        results = []
        ext = output_format.lstrip(".").lower()

        for image in images:
            arr = 255.0 * image.cpu().numpy()
            pil_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

            file = f"{filename_base}_{counter:03}.{ext}"
            out_path = os.path.join(self.output_dir, file)

            try:
                self.save_single_image(pil_img, out_path, output_format, quality, prompt, extra_pnginfo)
            except Exception as e:
                print(f"[save_webp_avif] error saving {out_path}: {e}")

            results.append({"filename": file, "subfolder": "", "type": self.type})
            counter += 1

        return {"ui": {"images": results}}

NODE_CLASS_MAPPINGS = {
    "SaveWebpAvif": SaveWebpAvif
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveWebpAvif": "💾 Save WebP / AVIF"
}
