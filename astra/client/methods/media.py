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

 async def download_media(self, message_id: str) -> str:
  """
  Downloads the media attached to a message.
  Returns: Base64 encoded string of the media.
  """
  try:
   result = await self._client.bridge.call("retrieveMedia", message_id)
   if not result:
    raise Exception("Empty result from retrieveMedia")
   
   if isinstance(result, dict):
    # Chunked Transfer Handling
    if "streamId" in result:
     stream_id = result["streamId"]
     total_length = result["length"]
     chunk_size = 1024 * 1024 * 2 # 2MB chunks
     data_parts = []
     
     try:
      for offset in range(0, total_length, chunk_size):
       chunk = await self._client.bridge.call("readMediaChunk", stream_id, offset, chunk_size)
       if chunk:
        data_parts.append(chunk)
       else:
        break
     finally:
      # Clean up cache on browser side
      await self._client.bridge.call("clearMediaCache", stream_id)
      
     return "".join(data_parts)
     
    if "data" in result:
     return result["data"]
     
   return result
  except Exception as e:
   logger.error(f"Download failed for {message_id}: {e}")
   raise e
  
 async def send_image(self, chat_id: str, file_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None) -> Any:
  """Sends an image file."""
  return await self.send_file(chat_id, file_path, caption=caption, reply_to=reply_to)

 async def send_video(self, chat_id: str, file_path: str, caption: Optional[str] = None, reply_to: Optional[str] = None) -> Any:
  """Sends a video file."""
  return await self.send_file(chat_id, file_path, caption=caption, reply_to=reply_to)

 async def send_audio(self, chat_id: str, file_path: str, reply_to: Optional[str] = None) -> Any:
  """Sends an audio file."""
  return await self.send_file(chat_id, file_path, reply_to=reply_to)

 async def send_sticker(self, chat_id: str, media: str, reply_to: Optional[str] = None) -> Any:
  """
  Sends a sticker. 
  Args:
   media: File path or Base64 string.
  """
  # Check if it's a file path
  if os.path.exists(media):
   return await self.send_file(chat_id, media, reply_to=reply_to)
  
  # Assume Base64/Raw data
  return await self._client.bridge.call(
   "sendMedia", 
   {
    "to": chat_id, 
    "data": media, 
    "mimetype": "image/webp", 
    "type": "sticker", # Explicitly set type to sticker
    "options": {"quotedMsgId": reply_to} if reply_to else {}
   }
  )
