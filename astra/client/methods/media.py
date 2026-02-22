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

logger = logging.getLogger("Media")

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
  logger.debug(f"Preparing media: {filename} ({file_size} bytes)")

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
   logger.info(f"Uploading {filename}...")
   
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
   logger.info(f"Download failed for {message_id}: {e}")
   raise e

 async def download(self, message_id: Any) -> Optional[str]:
  """
  Downloads media and saves it to a temporary file.
  Returns: Absolute path to the saved file.
  """
  try:
   from ...models.message import Message
   
   # 1. Normalize Message ID
   mid = message_id.id if isinstance(message_id, Message) else str(message_id)
   
   # 2. Get Media Data (Base64 or Chunked)
   data_b64 = None
   try:
    data_b64 = await self.download_media(mid)
   except Exception as e:
    logger.warning(f"JS retrieveMedia failed for {mid}, attempting UI Fallback: {e}")

   import tempfile
   import uuid
   temp_dir = os.path.join(os.getcwd(), "temp")
   os.makedirs(temp_dir, exist_ok=True)

   if data_b64:
    # 3. Save to Temp File
    ext = "media"
    if isinstance(message_id, Message):
     mtype = str(message_id.type).split('.')[-1].lower()
     if mtype == 'image': ext = 'jpg'
     elif mtype == 'video': ext = 'mp4'
     elif mtype == 'audio': ext = 'mp3'
     elif mtype == 'sticker': ext = 'webp'
    
    file_path = os.path.join(temp_dir, f"astra_{uuid.uuid4().hex[:8]}.{ext}")
    
    with open(file_path, "wb") as f:
     f.write(base64.b64decode(data_b64))
    
    logger.info(f"Media saved via JS Cache: {file_path}")
    return os.path.abspath(file_path)

   # =========================================================
   # UI PLAYWRIGHT FALLBACK
   # =========================================================
   logger.info(f"Attempting Playwright UI Download Fallback for {mid}")
   page = self._client.bridge._page
   short_id = mid.split('_')[-1] if '_' in mid else mid

   # Scroll message into view
   await page.evaluate('''async (msgId) => {
    const Store = window.Astra?.initializeEngine();
    if (!Store) return;
    const msg = Store.Msg?.get(msgId);
    if (msg && Store.Cmd?.scrollToMessage) {
     Store.Cmd.scrollToMessage(msg);
     await new Promise(r => setTimeout(r, 800));
    }
   }''', mid)

   msg_loc = page.locator(f'div[data-id="{mid}"]').first
   if await msg_loc.count() == 0:
    msg_loc = page.locator(f'div[data-id*="{short_id}"]').first

   if await msg_loc.count() > 0:
    # Strategy A: Right-Click -> "Download" Context Menu
    await msg_loc.click(button='right')
    await asyncio.sleep(0.5)
    
    dl_option = page.get_by_text("Download", exact=True).locator("visible=true").last
    if await dl_option.count() > 0:
     logger.debug("Found 'Download' in context menu, clicking...")
     async with page.expect_download(timeout=15000) as download_info:
      await dl_option.click()
     
     download = await download_info.value
     file_path = os.path.join(temp_dir, f"astra_dl_{uuid.uuid4().hex[:8]}_{download.suggested_filename}")
     await download.save_as(file_path)
     logger.info(f"Successfully downloaded via UI Context Menu: {file_path}")
     return os.path.abspath(file_path)
    
    # Strategy B: Open Media Viewer -> Click "Download" icon
    await page.keyboard.press("Escape") # Close context menu
    await asyncio.sleep(0.5)
    
    logger.debug("Trying Media Viewer approach...")
    img_loc = msg_loc.locator('img, video').first
    if await img_loc.count() > 0:
     # Click with left button to open Image/Video Viewer
     await img_loc.click()
     await asyncio.sleep(1.0)
     
     viewer_dl = page.locator('div[role="button"][title="Download"]').first
     if await viewer_dl.count() == 0:
      viewer_dl = page.locator('span[data-icon="download"]').first
     
     if await viewer_dl.count() > 0:
      logger.debug("Found 'Download' icon in viewer, clicking...")
      async with page.expect_download(timeout=15000) as download_info:
       await viewer_dl.click()
      
      download = await download_info.value
      file_path = os.path.join(temp_dir, f"astra_dl_{uuid.uuid4().hex[:8]}_{download.suggested_filename}")
      await download.save_as(file_path)
      
      await page.keyboard.press("Escape") # Close viewer
      logger.info(f"Successfully downloaded via Media Viewer: {file_path}")
      return os.path.abspath(file_path)
     else:
      await page.keyboard.press("Escape") # Close viewer if no download button

   logger.error(f"UI Download Fallback completely exhausted for {mid}.")
   return None

  except Exception as e:
   logger.error(f"Media download/save failed: {e}")
   return None
  
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
