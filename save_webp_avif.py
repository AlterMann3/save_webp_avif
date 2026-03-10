import os
import json
import numpy as np
from datetime import datetime
from PIL import Image

# Check avif plugin
try:
    import pillow_avif  # noqa: F401
    AVIF_SUPPORTED = True
except Exception:
    AVIF_SUPPORTED = False

# Respect CLI metadata disable flag if present
try:
    from comfy.cli_args import args
except Exception:
    class _Args:
        disable_metadata = False
    args = _Args()

class SaveWebpAvif:
    """
    Save node that supports WebP and AVIF.
    - AVIF: subsampling fixed to 4:4:4, speed fixed to 6
    - Metadata (prompt + workflow) is stored in EXIF
    - Filename engine: supports strftime style patterns in filename_prefix (default: CUI(%y%m%d_%H%M))
    """
    RETURN_TYPES = ()
    FUNCTION = "save_images"
    OUTPUT_NODE = True
    CATEGORY = "image"

    type = "output"
    prefix_append = ""

    # Visible choices for format dropdown (keep leading dot for compatibility)
    output_formats = [".webp", ".avif"]

    def __init__(self):
        self.output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "output")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "CUI(%y%m%d_%H%M)"}),
                # Quality is a text box style INT (not a slider), limited to 0-100
                "quality": ("INT", {"default": 96, "min": 0, "max": 100}),
                # Visible selector for formats
                "output_format": (cls.output_formats, {"default": ".avif"}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    # -----------------------------
    # Filename engine (simple + useful)
    # -----------------------------
    def build_filename_from_prefix(self, prefix, timestamp: datetime):
        """
        If prefix contains % (strftime tokens), apply timestamp.strftime.
        Otherwise return prefix unchanged.
        """
        try:
            if "%" in prefix:
                return timestamp.strftime(prefix)
        except Exception:
            # Fallback to raw prefix if formatting fails
            pass
        return prefix

    # -----------------------------
    # Metadata for AVIF (EXIF UserComment 0x9286)
    # -----------------------------
    def get_metadata_exif_avif(self, img, prompt, extra_pnginfo=None):
        """
        Build EXIF metadata for AVIF files using UserComment (0x9286).
        This method works best for AVIF format.
        """
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

        # Create EXIF object and store in UserComment (0x9286)
        exif = img.getexif()
        exif[0x9286] = json.dumps(metadata)
        
        return exif.tobytes()

    # -----------------------------
    # Metadata for WebP (EXIF Make 0x010f + ImageDescription 0x010e)
    # -----------------------------
    def get_metadata_exif_webp(self, img, prompt, extra_pnginfo=None):
        """
        Build EXIF metadata for WebP files using Make (0x010f) and ImageDescription (0x010e).
        This method works best for WebP format and ComfyUI workflow loading.
        """
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

        # Create EXIF object
        exif = img.getexif()
        
        # Store prompt and workflow in separate EXIF tags for ComfyUI compatibility
        # 0x010f: Make - Store prompt here
        # 0x010e: ImageDescription - Store workflow here
        if "prompt" in metadata:
            exif[0x010f] = "Prompt: " + json.dumps(metadata["prompt"])
        if "workflow" in metadata:
            exif[0x010e] = "Workflow: " + json.dumps(metadata["workflow"])

        return exif.tobytes()

    # -----------------------------
    # Save single image helper
    # -----------------------------
    def save_single_image(self, img: Image.Image, path: str, fmt: str, quality: int, prompt, extra_pnginfo):
        """
        fmt: string like ".avif" or ".webp" (leading dot)
        """
        kwargs = {}
        
        # Prepare exif based on format - different methods for AVIF vs WebP
        exif_data = None
        if fmt.lower() == ".avif":
            exif_data = self.get_metadata_exif_avif(img, prompt, extra_pnginfo)
        elif fmt.lower() == ".webp":
            exif_data = self.get_metadata_exif_webp(img, prompt, extra_pnginfo)
        
        if exif_data is not None:
            kwargs["exif"] = exif_data

        # Quality always passed as int
        try:
            q = int(quality)
        except Exception:
            q = 96

        kwargs["quality"] = q

        if fmt.lower() == ".avif":
            # Ensure AVIF plugin is present
            if not AVIF_SUPPORTED:
                raise RuntimeError("AVIF selected but pillow-avif-plugin not available in environment.")
            # Encoder tuning (hardcoded per user's request)
            kwargs["speed"] = 6
            kwargs["subsampling"] = "4:4:4"  # Must be "4:4:4" (not "444")

        elif fmt.lower() == ".webp":
            # WebP: support lossless when quality==100
            if q >= 100:
                kwargs["lossless"] = True

        # Finally save
        img.save(path, **kwargs)

    # -----------------------------
    # Main entry (node)
    # -----------------------------
    def save_images(self,
                    images,
                    filename_prefix="CUI(%y%m%d_%H%M)",
                    quality=96,
                    output_format=".avif",
                    prompt=None,
                    extra_pnginfo=None):

        # Timestamp and filename base
        timestamp = datetime.now()
        filename_base = self.build_filename_from_prefix(filename_prefix, timestamp)

        # Simple output directory (no folder_paths)
        output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "output")
        os.makedirs(output_dir, exist_ok=True)

        results = []

        # Ensure extension without leading dot
        ext = output_format.lstrip(".").lower()

        # Counter starts at 1, 3 digits
        counter = 1

        for image in images:
            # Convert tensor to uint8 image
            arr = 255.0 * image.cpu().numpy()
            pil_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

            # Build filename: prefix + _ + 3-digit counter + extension
            # Example: CUI(260310_0100)_001.avif
            file = f"{filename_base}_{counter:03}.{ext}"
            out_path = os.path.join(output_dir, file)

            # Save with appropriate params
            try:
                self.save_single_image(pil_img, out_path, output_format, quality, prompt, extra_pnginfo)
            except Exception as e:
                # Surface a helpful message in logs but continue
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