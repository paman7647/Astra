# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Primary data model for WhatsApp messages. 

This module defines the Message class, which encapsulates all message data 
and provides a clean interface for interaction and content extraction.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import asyncio
import time
from .user import JID
from .enums import MessageType, MessageAck

@dataclass(kw_only=True)
class Message:
 """
 Represents a complete WhatsApp message record.

 This class manages message metadata, sender identity, status flags, 
 and provides methods for responding to or modifying messages.
 """
 _client: Any = field(repr=False, compare=False, default=None)

 id: str = field(default="")
 chat_id: JID
 sender: Optional[JID] = None
 body: str = ""
 type: MessageType = MessageType.TEXT
 timestamp: int = 0

 from_me: bool = False
 is_forwarded: bool = False
 is_newsletter: bool = False
 is_poll: bool = False
 is_reaction: bool = False
 is_status: bool = False

 ack: MessageAck = MessageAck.SENT
 is_editable: bool = False

 # Name Metadata (Push-Based)
 sender_name: Optional[str] = None
 pushname: Optional[str] = None
 verified_name: Optional[str] = None

 # Enrichment
 quoted_message_id: Optional[str] = None
 quoted_participant: Optional[JID] = None
 quoted_type: Optional[MessageType] = None
 has_quoted_msg: bool = False
 mentioned_jids: List[JID] = field(default_factory=list)
 subtype: Optional[str] = None
 recipients: List[JID] = field(default_factory=list)
 
 # Media Metadata
 mimetype: Optional[str] = None
 size: Optional[int] = None

 @property
 def text(self) -> str:
  """Alias for body for compatibility with EventContext."""
  return self.body

 @property
 def author(self) -> Optional[JID]:
  """Backward compatibility alias for sender."""
  return self.sender

 @property
 def quoted_message(self) -> Optional['Message']:
  """Backward compatibility alias for quoted."""
  return self.quoted

 @property
 def quoted(self) -> Optional['Message']:
  """
  Returns the quoted message object if available.
  Note: This is a synchronous property, it doesn't fetch from server.
  Only works if the quoted message was included in the payload.
  """
  # For now, we return a mock or a reference if we had a cache.
  # But for logic checks like 'if msg.quoted', we just need to know if it exists.
  if self.quoted_message_id:
   # Return a skeleton with participant and basic metadata
   return Message(
    _client=self._client,
    id=self.quoted_message_id,
    chat_id=self.chat_id,
    sender=self.quoted_participant,
    type=self.quoted_type or MessageType.TEXT
   )
  return None

 @property
 def is_media(self) -> bool:
  """True if the message contains media (image, video, audio, etc)."""
  return self.type not in {MessageType.TEXT, MessageType.REVOKED}

 @property
 def is_service(self) -> bool:
  """True if this is a system/service message (e.g. group join/leave)."""
  # Mapping specialized notification types to service flag
  return self.type in {
      MessageType.GROUP_NOTIFICATION,
      MessageType.BROADCAST_NOTIFICATION,
      MessageType.E2E_NOTIFICATION
  }

 @classmethod
 def from_payload(cls, data: Dict[str, Any], client: Any = None) -> "Message":
  """
  Translates a raw JS runtime payload into a typed Message object.

  Args:
   data: The raw dictionary from the bridge.
   client: Optional Astra client instance for action binding.

  Returns:
   A populated Message instance.
  """
  # 1. Identity Normalization
  raw_id = data.get("id", {})
  if isinstance(raw_id, dict):
   serialized_id = raw_id.get("_serialized", "")
   from_me = raw_id.get("fromMe", False)
  else:
   serialized_id = str(raw_id)
   from_me = data.get("fromMe", False)

  # 2. Chat and Sender Extraction
  chat_id_raw = data.get("chatId") or data.get("to") or data.get("from", "")
  if isinstance(chat_id_raw, dict):
   chat_id_raw = chat_id_raw.get("_serialized", "")

  sender_raw = data.get("sender") or data.get("author") or data.get("from", "")
  if isinstance(sender_raw, dict):
   sender_raw = sender_raw.get("_serialized", "")

  # 3. Quoted Message
  quoted_id = data.get("quotedMsgId")
  if isinstance(quoted_id, dict):
   quoted_id = quoted_id.get("_serialized")

  quoted_participant = data.get("quotedParticipant")
  if isinstance(quoted_participant, dict):
   quoted_participant = quoted_participant.get("_serialized")

  # Extract quoted type if available
  quoted_type = None
  quoted_payload = data.get("quotedMsg")
  if quoted_payload and isinstance(quoted_payload, dict):
      quoted_type = MessageType(quoted_payload.get("type", "chat"))
  elif "_data" in data and isinstance(data["_data"], dict):
      q = data["_data"].get("quotedMsg")
      if q:
          quoted_type = MessageType(q.get("type", "chat"))

  return cls(
   _client=client,
   id=serialized_id,
   chat_id=JID.parse(chat_id_raw),
   sender=JID.parse(sender_raw) if sender_raw else None,
   body=data.get("body") or "",
   type=MessageType(data.get("type") or "chat"),
   timestamp=data.get("t") or data.get("timestamp") or 0,
   from_me=from_me,
   is_forwarded=data.get("isForwarded", False),
   is_newsletter=data.get("isNewsletter", False),
   is_poll=data.get("isPoll", False),
   is_reaction=data.get("isReaction", False),
   is_status=data.get("isStatus", False),
   ack=MessageAck(data.get("ack") if data.get("ack") is not None else 0),
   is_editable=data.get("isEditable", False),
   sender_name=data.get("senderName"),
   pushname=data.get("pushname"),
   verified_name=data.get("verifiedName"),
   quoted_message_id=quoted_id,
   quoted_participant=JID.parse(quoted_participant) if quoted_participant else None,
   quoted_type=quoted_type,
   has_quoted_msg=bool(quoted_id or data.get("hasQuotedMsg")),
   mentioned_jids=[JID.parse(m) if isinstance(m, str) else JID.parse(m.get("_serialized", ""))
       for m in (data.get("mentionedJidList") or [])],
   subtype=data.get("subtype"),
   recipients=[JID.parse(r) if isinstance(r, str) else JID.parse(r.get("_serialized", ""))
              for r in (data.get("recipients") or [])],
   mimetype=data.get("mimetype"),
   size=data.get("size") or data.get("filesize")
  )

 async def reply(self, text: str) -> "Message":
  """
  Sends a reply to this specific message.
  """
  if not self._client:
   raise RuntimeError("Message object is not bound to a client.")
  return await self._client.chat.send_message(self.chat_id.serialized, text, reply_to=self.id)

 async def respond(self, text: str) -> "Message":
  """
  Sends a message to the same chat as this message (without quoting).
  """
  if not self._client:
   raise RuntimeError("Message object is not bound to a client.")
  return await self._client.chat.send_message(self.chat_id.serialized, text)

 async def react(self, emoji: str) -> bool:
  """
  Reacts to this message with an emoji.
  """
  if not self._client:
   raise RuntimeError("Message object is not bound to a client.")
  return await self._client.chat.react(self.id, emoji)

 async def edit(self, text: str) -> bool:
  """
  Edits this message.
  """
  if not self._client:
   raise RuntimeError("Message object is not bound to a client.")
  # Give it a small sleep so we don't hit rate limits when spamming edits
  await asyncio.sleep(0.5)
  return await self._client.chat.edit_message(self.id, text)


 async def delete(self, for_everyone: bool = True) -> bool:
  """
  Deletes this message.
  """
  if not self._client:
   raise RuntimeError("Message object is not bound to a client.")
  return await self._client.chat.delete_message(self.id, everyone=for_everyone)

 async def download(self) -> Optional[str]:
  """
  Downloads the media attached to this message and saves it to a temporary file.
  Returns: Absolute path to the saved file or None if download fails or no media is present.
  """
  if not self._client:
   raise RuntimeError("Message object is not bound to a client.")
  if not self.is_media:
   return None
  return await self._client.media.download(self)

 def __repr__(self) -> str:
  return f"<Message id={self.id} from={self.sender or self.chat_id} type={self.type.name}>"
