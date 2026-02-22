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
import asyncio
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
  document: bool = False,
  progress: Optional[Callable[[int, int], Any]] = None
 ) -> bool:
  """
  Sends a local file as media with optional progress tracking.
  """
  if not os.path.exists(file_path):
   raise FileNotFoundError(f"Media file not found: {file_path}")

  filename = os.path.basename(file_path)
  file_size = os.path.getsize(file_path)
  logger.info(f"Preparing media: {filename} ({file_size} bytes)")

  import mimetypes
  mimetype, _ = mimetypes.guess_type(file_path)
  mimetype = mimetype or 'application/octet-stream'

  # WhatsApp-specific typing
  main_type = mimetype.split('/')[0]
  if main_type not in ['image', 'video', 'audio']:
   main_type = 'document'

  # Auto-Document Escalation: Files > 100MB are sent as documents to avoid WA video overhead
  if file_size > 100 * 1024 * 1024:
   logger.info(f"File size ({file_size}) exceeds 100MB. Escalating to document mode.")
   document = True

  final_options = {"quotedMsgId": reply_to} if reply_to else {}
  if main_type == 'document' or document:
   main_type = 'document'
   final_options['asDocument'] = True

  # Prepare the payload
  payload = {
   "to": chat_id,
   "mimetype": mimetype,
   "type": main_type,
   "filename": filename,
   "caption": caption,
   "options": final_options
  }

  # CHUNKED UPLOAD LOGIC (For files > 2MB)
  CHUNK_THRESHOLD = 2 * 1024 * 1024 # 2MB
  if file_size > CHUNK_THRESHOLD:
   import uuid
   upload_id = f"up_{uuid.uuid4().hex[:8]}"
   logger.info(f"Starting chunked upload for {filename} [ID: {upload_id}]")
   
   await self._client.bridge.call("initChunkedUpload", {"id": upload_id, "size": file_size})
   
   chunk_size = 1024 * 1024 # 1MB chunks
   sent_bytes = 0
   with open(file_path, "rb") as f:
    while True:
     chunk_data = f.read(chunk_size)
     if not chunk_data:
      break
     
     chunk_b64 = base64.b64encode(chunk_data).decode()
     await self._client.bridge.call("pushChunk", {"id": upload_id, "data": chunk_b64})
     
     sent_bytes += len(chunk_data)
     if progress:
      try:
       is_coro = asyncio.iscoroutinefunction(progress) or asyncio.iscoroutine(progress)
       if is_coro: await progress(sent_bytes, file_size)
       else: progress(sent_bytes, file_size)
      except: pass
   
   payload["uploadId"] = upload_id
  else:
   # Standard Upload (Small files)
   with open(file_path, "rb") as f:
    payload["data"] = base64.b64encode(f.read()).decode()

  return await self._client.bridge.call("sendMedia", payload, progress=None if "uploadId" in payload else progress)

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
  
 async def send_image(self, chat_id: str, file_path: str, **kwargs) -> Any:
  """Sends an image file."""
  return await self.send_file(chat_id, file_path, **kwargs)

 async def send_video(self, chat_id: str, file_path: str, **kwargs) -> Any:
  """Sends a video file."""
  return await self.send_file(chat_id, file_path, **kwargs)

 async def send_audio(self, chat_id: str, file_path: str, **kwargs) -> Any:
  """Sends an audio file."""
  return await self.send_file(chat_id, file_path, **kwargs)

 async def send_sticker(self, chat_id: str, media: str, reply_to: Optional[str] = None) -> Any:
  """
  Sends a sticker. 
  Args:
   media: File path or Base64 string.
  """
  # Check if it's a file path (avoiding checks on long base64 strings)
  if len(media) < 1000 and os.path.exists(media):
   return await self.send_file(chat_id, media, reply_to=reply_to)
  
  # Assume Base64/Raw data
  return await self._client.bridge.call(
   "sendMedia", 
   {
    "to": chat_id, 
    "data": media, 
    "mimetype": "image/webp", 
    "type": "sticker", 
    "options": {"quotedMsgId": reply_to} if reply_to else {}
   }
  )
