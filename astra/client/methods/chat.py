# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Chat and messaging interface for the Astra Client.

This module provides the ChatMethods mixin, consolidating all high-level 
chat operations like sending messages, polls, and media.
"""

import logging
import time
from typing import Optional, List, Any, Dict, TYPE_CHECKING, Union
from ...models import Message, Chat
from ...errors import (
 MessageSendError, MessageTimeoutError, MessageEditError,
 MessageDeleteError, ReactionError, PollError,
 MediaUploadError, ChatNotFoundError, ChatOperationError,
 SyncError, ErrorCode,
)

if TYPE_CHECKING:
 from ..client import Client

logger = logging.getLogger("Astra.Chat")

class ChatMethods:
 """
 Interface for high-level chat and messaging operations.
 """

 def __init__(self, client: 'Client'):
  self._client = client

 async def send_message(
  self,
  chat_id: str,
  text: str,
  reply_to: Optional[str] = None,
  mentions: Optional[List[str]] = None
 ) -> Message:
  """
  Sends a text message to a chat.

  Raises:
   MessageSendError: [E3001] If the message could not be sent.
   MessageTimeoutError: [E3002] If WhatsApp didn't acknowledge in time.
  """
  options = {}
  if reply_to: options["quotedMsgId"] = reply_to
  if mentions: options["mentions"] = mentions

  try:
   return await self._client.api.send_text(chat_id, text, options=options)
  except Exception as e:
   raise MessageSendError(f"Failed to send message to {chat_id}: {e}", cause=e) from e

 async def send_poll(self, chat_id: str, question: str, options: List[str], poll_options: Optional[Dict[str, Any]] = None) -> Message:
  """
  Sends a poll message.

  Raises:
   PollError: [E3010] If the poll could not be created.
  """
  try:
   return await self._client.api.send_poll(chat_id, question, options, poll_options=poll_options)
  except Exception as e:
   raise PollError(f"Failed to create poll in {chat_id}: {e}", cause=e) from e

 async def delete_message(self, message_id: str, everyone: bool = True) -> bool:
  """
  Deletes a message.

  Raises:
   MessageDeleteError: [E3007] If deletion failed.
  """
  try:
   return await self._client.api.delete_message(message_id, for_everyone=everyone)
  except Exception as e:
   raise MessageDeleteError(f"Failed to delete {message_id}: {e}") from e

 async def bulk_delete(self, message_ids: List[str], everyone: bool = True) -> bool:
  """
  Deletes multiple messages in a single operation.
  """
  try:
   return await self._client.api.bulk_delete(message_ids, for_everyone=everyone)
  except Exception as e:
   raise MessageDeleteError(f"Failed to bulk delete {len(message_ids)} messages: {e}") from e

 async def react(self, message_id: str, emoji: str) -> bool:
  """
  Reacts to a message.

  Raises:
   ReactionError: [E3008] If the reaction could not be applied.
  """
  try:
   return await self._client.api.react(message_id, emoji)
  except Exception as e:
   raise ReactionError(f"Failed to react to {message_id}: {e}") from e

 async def edit_message(self, message_id: str, text: str) -> bool:
  try:
   # Mandatory 0.5s delay to keep message edits stable and avoid rate limits
   time.sleep(0.5)
   return await self._client.api.edit_message(message_id, text)
  except Exception as e:
   raise MessageEditError(f"Failed to edit {message_id}: {e}") from e

 async def archive(self, chat_id: str, archive: bool = True) -> bool:
  """
  Archives or unarchives a chat.

  Raises:
   ChatOperationError: [E3021] If archive/unarchive failed.
  """
  try:
   return await self._client.bridge.call("archiveChat", {"chatId": chat_id, "archive": archive})
  except Exception as e:
   raise ChatOperationError(f"Failed to {'archive' if archive else 'unarchive'} {chat_id}: {e}", code=ErrorCode.MSG_CHAT_ARCHIVE) from e

 async def pin(self, chat_id: str, pin: bool = True) -> bool:
  """
  Pins or unpins a chat.

  Raises:
   ChatOperationError: [E3023] If pin/unpin failed.
  """
  try:
   return await self._client.bridge.call("pinChat", {"chatId": chat_id, "pin": pin})
  except Exception as e:
   raise ChatOperationError(f"Failed to {'pin' if pin else 'unpin'} {chat_id}: {e}", code=ErrorCode.MSG_CHAT_PIN) from e

 async def send_state(self, chat_id: str, state: str) -> bool:
  """
  Sets the chat state (typing, recording, paused).
  """
  try:
   return await self._client.bridge.call("sendChatState", {"chatId": chat_id, "state": state})
  except Exception as e:
   # Log and suppress
   return False

 async def mute(self, chat_id: str, duration: int = 28800) -> bool:
  """
  Mutes a chat for a specific duration (default 8 hours).

  Raises:
   ChatOperationError: [E3022] If mute failed.
  """
  try:
   return await self._client.bridge.call("muteChat", {"chatId": chat_id, "duration": duration})
  except Exception as e:
   raise ChatOperationError(f"Failed to mute {chat_id}: {e}", code=ErrorCode.MSG_CHAT_MUTE) from e

 async def fetch_messages(
  self,
  chat_id: str,
  **kwargs
 ) -> List[Message]:
  """
  Loads chat messages with flexible options (limit, from_me, message_id, direction).

  Raises:
   ChatNotFoundError: [E3020] If the chat doesn't exist.
  """
  options = kwargs.copy()
  # Map common aliases for JS bridge
  if "message_id" in options:
   options["msgId"] = options.pop("message_id")

  try:
   return await self._client.api.fetch_messages(chat_id, options=options)
  except Exception as e:
   raise ChatNotFoundError(f"Failed to fetch messages for {chat_id}: {e}") from e

 async def sync_history(self, chat_id: str) -> bool:
  """
  Force syncs chat history for a specific conversation.

  Raises:
   SyncError: [E3025] If sync failed.
  """
  try:
   return await self._client.api.sync_history(chat_id)
  except Exception as e:
   raise SyncError(f"Failed to sync history for {chat_id}: {e}") from e

 async def send_media(
  self,
  chat_id: str,
  media: Union[str, Dict[str, Any]],
  mimetype: Optional[str] = None,
  filename: Optional[str] = None,
  caption: Optional[str] = None,
  reply_to: Optional[str] = None,
  **kwargs
 ) -> Message:
  """
  Sends a media file. Supports base64 string or a dict package.
  """
  if isinstance(media, dict):
   mimetype = media.get("mimetype", mimetype)
   filename = media.get("filename", filename)
   data = media.get("data", "")
  else:
   data = media

  options = kwargs.get("options", {})
  
  # Handle various reply parameters for developer convenience
  actual_reply_to = reply_to or kwargs.get("reply_to") or kwargs.get("quoted_message_id")
  if actual_reply_to:
   options["quotedMsgId"] = actual_reply_to

  try:
   return await self._client.api.send_media(chat_id, data, mimetype, filename=filename, caption=caption, options=options)
  except Exception as e:
   raise MediaUploadError(f"Failed to send media to {chat_id}: {e}", cause=e) from e

 async def set_chat_state(self, chat_id: str, state: str) -> bool:
  """Sets the chat state (typing, recording, clear)."""
  return await self._client.api.send_chat_state(chat_id, state)
