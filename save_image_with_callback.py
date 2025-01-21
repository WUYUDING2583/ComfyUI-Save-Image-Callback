import os
import sys
import json
from PIL import Image
from PIL.PngImagePlugin import PngInfo

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

from comfy.cli_args import args


import folder_paths

class SaveImageWithCallback:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", {"tooltip": "The images to save."}),
                "filename_prefix": (
                    "STRING",
                    {
                        "default": "ComfyUI",
                        "tooltip": "The prefix for the file to save. This may include formatting information such as %date:yyyy-MM-dd% or %Empty Latent Image.width% to include values from nodes.",
                    },
                ),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images_with_callback"

    OUTPUT_NODE = True

    CATEGORY = "image"
    DESCRIPTION = "Saves the input images to your ComfyUI output directory."

    def save_images_with_callback(
        self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None
    ):
        print("============= Save Image With Callback =============")
        filename_prefix += self.prefix_append
        full_output_folder, filename, counter, subfolder, filename_prefix = (
            folder_paths.get_save_image_path(
                filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0]
            )
        )
        results = list()
        for batch_number, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            if not args.disable_metadata:
                metadata = PngInfo()
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for x in extra_pnginfo:
                        metadata.add_text(x, json.dumps(extra_pnginfo[x]))

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            print(f"file: {file}")
            print(f"filename_with_batch_num: {filename_with_batch_num}")
            img.save(
                os.path.join(full_output_folder, file),
                pnginfo=metadata,
                compress_level=self.compress_level,
            )
            results.append(
                {"filename": file, "subfolder": subfolder, "type": self.type}
            )
            if extra_pnginfo and extra_pnginfo.get("callback_data"):
                callback_data = extra_pnginfo.get("callback_data")
                print(f"callback_data: {callback_data}")
                try:
                    import requests

                    webhook_url = callback_data["callback_url"]

                    webhook_data = {
                        "filename": file,
                        "full_path": os.path.join(full_output_folder, file),
                        "type": self.type,
                        "callback_data": callback_data,
                    }

                    requests.post(webhook_url, json=webhook_data)
                except Exception as e:
                    print(f"Failed to send webhook: {str(e)}")

            counter += 1

        return {"ui": {"images": results}}
