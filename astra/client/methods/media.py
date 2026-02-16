# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the MediaMethods mixin for the Astra Client.
"""

import logging
import base64
import os
from typing import Optional, Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
 from ..client import Client

logger = logging.getLogger("Astra.Media")

class MediaMethods:
 """
 API for Media handling.
 """

 def __init__(self, client: 'Client'):
  self._client = client

 async def send_file(
  self,
  chat_id: str,
  file_path: str,
  caption: Optional[str] = None,
  reply_to: Optional[str] = None,
  progress: Optional[Callable[[int, int], Any]] = None
 ) -> bool:
  """
  Sends a local file as media with optional progress tracking.
  """
  if not os.path.exists(file_path):
   raise FileNotFoundError(f"Media file not found: {file_path}")

  filename = os.path.basename(file_path)
  logger.info(f"Preparing media: {filename}")

  with open(file_path, "rb") as f:
   data = base64.b64encode(f.read()).decode()

  import mimetypes
  mimetype, _ = mimetypes.guess_type(file_path)
  mimetype = mimetype or 'application/octet-stream'

  # WhatsApp-specific typing
  main_type = mimetype.split('/')[0]
  if main_type not in ['image', 'video', 'audio']:
   main_type = 'document'

  final_options = {"quotedMsgId": reply_to} if reply_to else {}
  if main_type == 'document':
   final_options['asDocument'] = True

  return await self._client.bridge.call("sendMedia", {
   "to": chat_id,
   "data": data,
   "mimetype": mimetype,
   "type": main_type,
   "filename": filename,
   "caption": caption,
   "options": final_options
  }, progress=progress)
