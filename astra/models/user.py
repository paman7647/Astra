# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module defines the identity and user representation in Astra.
It encapsulates WhatsApp JIDs and contact metadata.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass(frozen=True)
class JID:
 """
 Represents a WhatsApp Jabber ID (JID).

 A JID uniquely identifies a user, group, or newsletter on WhatsApp.
 Example: '1234567890@c.us' (User) or '1234567890@g.us' (Group).
 """
 user: str
 server: str
 serialized: str

 @classmethod
 def parse(cls, raw: str) -> "JID":
  """
  Parses a raw JID string into a structured JID object.

  Args:
   raw: The raw WhatsApp ID string (e.g., "12345@c.us").

  Returns:
   A structured JID instance.

  Example:
   >>> jid = JID.parse("12345@c.us")
   >>> print(jid.user)
   "12345"
  """
  if not raw:
   return cls(user="unknown", server="unknown", serialized="unknown@unknown")

  if "@" not in raw:
   # Default to user server if missing
   return cls(user=raw, server="c.us", serialized=f"{raw}@c.us")

  username, server = raw.split("@", 1)
  return cls(user=username, server=server, serialized=raw)

 def __str__(self) -> str:
  return self.serialized

@dataclass
class User:
 """
 Represents a WhatsApp Actor - a person, group participant, or yourself.

 This class holds metadata about a contact or user, such as their
 display name and business status.
 """
 id: JID
 name: Optional[str] = None
 push_name: Optional[str] = None
 is_me: bool = False
 is_business: bool = False
 is_business: bool = False
 is_my_contact: bool = False
 _client: Any = None # Bound Astra Client

 @property
 def title(self) -> str:
  """Standardized title property for entity resolution."""
  return self.name or self.push_name or self.id.user

 async def send_message(self, text: str, **kwargs) -> Any:
  """Sends a private message to this user."""
  if not self._client: raise RuntimeError("User is not bound to a client.")
  return await self._client.chat.send_message(self.id.serialized, text, **kwargs)

 async def block(self) -> bool:
  """Blocks this user."""
  if not self._client: raise RuntimeError("User is not bound to a client.")
  return await self._client.bridge.call("blockContact", self.id.serialized)

 @classmethod
 def from_payload(cls, data: Dict[str, Any], client: Any = None) -> "User":
  """
  Creates a User instance from a raw dictionary payload.

  This is typically used when receiving data from the WhatsApp Web bridge.

  Args:
   data: The raw dictionary containing user data.

  Returns:
   A populated User instance.
  """
  return cls(
   id=JID.parse(data.get("id", "")),
   name=data.get("name"),
   push_name=data.get("pushname"),
   is_me=data.get("isMe", False),
   is_business=data.get("isBusiness", False),
   is_my_contact=data.get("isMyContact", False),
   _client=client
  )
