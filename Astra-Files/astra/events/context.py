# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the EventContext class, which is passed to
event handlers to provide easy access to event data and actions.
"""

from typing import Any, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
 from ..client.client import Client

class EventContext:
 """
 The context of a WhatsApp event.

 Provides a high-level API for interacting with the message or
 chat that triggered the event.
 """

 def __init__(
  self,
  client: 'Client',
  event: Any,
  command: Optional[str] = None,
  args: Optional[List[str]] = None,
  prefix: Optional[str] = None
 ):
  """
  Initialize the event context.

  Args:
   client: The Astra client instance.
   event: The raw event or Message object.
   command: The command name (if applicable).
   args: Command arguments (if applicable).
   prefix: The command prefix used (if applicable).
  """
  self._client = client
  self._event = event

  # Command Metadata
  self.prefix = prefix
  self.command = command
  self.args = args or []

  # Hydrate attributes from the event payload
  self.text = self._extract_text(event)
  self.chat_id = self._extract_id(event, ['chat_id', 'from', 'to', 'chatId'])
  self.sender_id = self._extract_id(event, ['sender', 'author', 'from'])
  self.message_id = self._extract_id(event, ['id', 'msg_id'])

  # Normalization
  self.from_me = bool(self._extract_bool(event, ['from_me', 'fromMe']))
  self.type = str(getattr(event, 'type', 'chat'))
  self.is_media = bool(getattr(event, 'hasMedia', False) or self.type in ['image', 'video', 'audio', 'document', 'sticker', 'ptt'])

  # Group detection
  self.is_group = "@g.us" in (self.chat_id or "")

 async def reply(self, text: str) -> Any:
  """
  Sends a reply quoting this message.
  """
  return await self._client.send_message(
   to=self.chat_id,
   text=text,
   reply_to=self.message_id
  )

 async def react(self, emoji: str) -> bool:
  """
  Reacts to this message with an emoji.
  """
  return await self._client.react(self.chat_id, self.message_id, emoji)

 async def edit(self, text: str) -> bool:
  """
  Edits this message (if sent by the bot).
  """
  return await self._client.api.edit_message(self.message_id, text)

 async def delete(self, everyone: bool = True) -> bool:
  """
  Deletes this message.
  """
  return await self._client.api.delete_message(self.message_id, for_everyone=everyone)

 async def respond(self, text: str, **kwargs) -> Any:
  """
  # Response logic.
  Edits the message if it's outgoing (from bot), otherwise replies.
  Now includes robust fallback for self-chats and bridge failures.
  """
  try:
   if self.from_me:
    return await self.edit(text)
   return await self.reply(text)
  except Exception as e:
   # Fallback to direct send_message if edit/reply fails
   # (Common in self-chats or restricted permissions)
   return await self._client.chat.send_message(self.chat_id, text, **kwargs)

 # --- Internal Helpers ---

 def _extract_text(self, obj: Any) -> str:
  """Extracts text from various payload structures."""
  if hasattr(obj, 'body'): return obj.body
  if hasattr(obj, 'text'): return obj.text
  if isinstance(obj, dict):
   return obj.get('body', obj.get('text', ""))
  return str(obj) if obj else ""

 def _extract_id(self, obj: Any, keys: List[str]) -> Optional[str]:
  """Gracefully extracts serialized JIDs from complex objects or dicts."""
  for key in keys:
   val = getattr(obj, key, None) if not isinstance(obj, dict) else obj.get(key)
   if val:
    # If it's a JID/Identity object
    if hasattr(val, 'serialized'): return val.serialized
    # If it's a JS serialized object { _serialized: "..." }
    if isinstance(val, dict): return val.get('_serialized', val.get('id', ''))
    return str(val)
  return None

 @property
 def body(self) -> str:
  """Alias for text for compatibility with Message model."""
  return self.text

 def _extract_bool(self, obj: Any, keys: List[str]) -> bool:
  """Gracefully extracts boolean values from various payload structures."""
  for key in keys:
   val = getattr(obj, key, None) if not isinstance(obj, dict) else obj.get(key)
   if val is not None:
    return bool(val)
  return False

 def __getattr__(self, name: str) -> Any:
  """Proxies missing attributes to the underlying event object."""
  if hasattr(self, '_event'):
   return getattr(self._event, name)
  raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

 def __repr__(self) -> str:
  ident = f" cmd={self.command}" if self.command else ""
  return f"<EventContext chat={self.chat_id}{ident}>"
