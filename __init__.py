"""
@author: AlterMann
@title: Save WebP-AVIF
@nickname: Save WebP-AVIF
@description: Custom node to save your images in WebP or AVIF.
"""


from .save_webp_avif import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', "WEB_DIRECTORY"]

from aiohttp import web
from server import PromptServer
from pathlib import Path

if hasattr(PromptServer, "instance"):
  # NOTE: we add an extra static path to avoid comfy mechanism
  # that loads every script in web.
  PromptServer.instance.app.add_routes(
      [web.static("/save_webp_avif", (Path(__file__).parent.absolute() / "assets").as_posix())]
  )

