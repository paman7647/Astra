# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module represents chat threads in Astra.
A Chat can be a private conversation or a group.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from .user import JID

@dataclass
class Chat:
 """
 Represents a conversational thread on WhatsApp.

 Holds metadata about the chat such as its title, unread message
 count, and synchronization status.
 """
 id: JID
 title: str
 is_group: bool = False
 is_readonly: bool = False
 unread_count: int = 0
 mute_expiration: int = 0
 last_message_timestamp: int = 0
 _client: Any = None # Bound Astra Client

 async def send_message(self, text: str, **kwargs) -> Any:
  """Sends a message directly to this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.send_message(self.id.serialized, text, **kwargs)

 async def send_poll(self, question: str, options: list, **kwargs) -> Any:
  """Sends a poll message directly to this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.send_poll(self.id.serialized, question, options, **kwargs)

 async def react(self, message_id: str, emoji: str) -> bool:
  """Adds a reaction to a message in this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.react(message_id, emoji)

 async def fetch_messages(self, limit: int = 10, **kwargs) -> list:
  """Fetches message history for this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.fetch_messages(self.id.serialized, limit=limit, **kwargs)

 async def sync_history(self) -> bool:
  """Triggers a force sync for this chat's history."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.sync_history(self.id.serialized)

 async def archive(self, archive: bool = True) -> bool:
  """Archives or unarchives this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.archive(self.id.serialized, archive=archive)

 async def pin(self, pin: bool = True) -> bool:
  """Pins or unpins this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.pin(self.id.serialized, pin=pin)

 async def mute(self, duration: int = 28800) -> bool:
  """Mutes this chat."""
  if not self._client: raise RuntimeError("Chat is not bound to a client.")
  return await self._client.chat.mute(self.id.serialized, duration=duration)

 @classmethod
 def from_payload(cls, data: Dict[str, Any], client: Any = None) -> "Chat":
  """
  Hydrates a Chat object from a raw bridge payload.

  Args:
   data: Dictionary containing chat attributes.

  Returns:
   A Chat model instance.

  Example:
   >>> chat = Chat.from_payload({"id": "123@g.us", "name": "Hackers"})
  """
  # Handle complex ID structures if passed as dict
  raw_id = data.get("id", "")
  if isinstance(raw_id, dict):
   raw_id = raw_id.get("_serialized", "")

  return cls(
   id=JID.parse(raw_id),
   title=data.get("name") or data.get("formattedTitle") or "Unknown Thread",
   is_group=data.get("isGroup", False),
   is_readonly=data.get("isReadOnly", False),
   unread_count=data.get("unreadCount", 0),
   mute_expiration=data.get("muteExpiration", 0),
   last_message_timestamp=data.get("t", 0),
   _client=client
  )
