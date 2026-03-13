# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module handles the transformation of raw bridge data into
strongly-typed Astra models.
"""

import logging
from typing import Any, Dict, Optional
from ..types import Message, Chat, User
from ..types.chat import GroupInfo, GroupParticipant, JID

logger = logging.getLogger("Engine")

class DataTransformer:
 """
 Transformer for bridge payloads.

 Responsible for validating and hydrating Astra models from raw
 JavaScript runtime dictionaries.
 """

 @staticmethod
 def to_message(data: Dict[str, Any], client: Any = None) -> Message:
  """Converts a raw JSON payload into a Message model."""
  try:
   # Detailed logging for service message debugging
   if data.get("type") in {"gp2", "broadcast_notification", "e2e_notification"} or data.get("subtype"):
       logger.debug(f"TRANSFORMER: Service msg detected. Type={data.get('type')}, Subtype={data.get('subtype')}")
       logger.debug(f"TRANSFORMER: Recipients={data.get('recipients')}")

   message = Message.from_payload(data, client=client)
   logger.debug(f"Hydrated message: {message.id} (Type: {message.type}, Subtype: {message.subtype})")
   return message
  except Exception as e:
   logger.error(f"Failed to hydrate Message model: {e}", extra={"payload": data})
   raise RuntimeError(f"Data mapping error in Message: {e}")

 @staticmethod
 def to_chat(data: Dict[str, Any]) -> Chat:
  """Converts a raw JSON payload into a Chat model."""
  try:
   chat = Chat.from_payload(data)
   logger.debug(f"Hydrated chat: {chat.title}")
   return chat
  except Exception as e:
   logger.error(f"Failed to hydrate Chat model: {e}", extra={"payload": data})
   raise RuntimeError(f"Data mapping error in Chat: {e}")

 @staticmethod
 def to_user(data: Dict[str, Any]) -> User:
  """Converts a raw JSON payload into a User model."""
  try:
   user = User.from_payload(data)
   logger.debug(f"Hydrated user: {user.name or user.id}")
   return user
  except Exception as e:
   logger.error(f"Failed to hydrate User model: {e}", extra={"payload": data})
   raise RuntimeError(f"Data mapping error in User: {e}")

 @staticmethod
 def to_group_info(data: Dict[str, Any]) -> GroupInfo:
  """Converts a raw JSON payload into a GroupInfo model."""
  try:
   participants = []
   for p in data.get("participants", []):
    raw_pid = p.get("id", "")
    if isinstance(raw_pid, dict): raw_pid = raw_pid.get("_serialized", "")
    participants.append(GroupParticipant(
     id=JID.parse(raw_pid),
     is_admin=p.get("isAdmin", False),
     is_super_admin=p.get("isSuperAdmin", False)
    ))
   
   raw_owner = data.get("owner", "")
   if isinstance(raw_owner, dict): raw_owner = raw_owner.get("_serialized", "")
   owner = JID.parse(raw_owner) if raw_owner else None

   raw_id = data.get("id", "")
   if isinstance(raw_id, dict): raw_id = raw_id.get("_serialized", "")

   info = GroupInfo(
    id=JID.parse(raw_id),
    title=data.get("title", "Group"),
    subject=data.get("subject", "Group"),
    description=data.get("description", ""),
    owner=owner,
    creation=data.get("creation", 0),
    participants=participants
   )
   logger.debug(f"Hydrated GroupInfo: {info.title}")
   return info
  except Exception as e:
   logger.error(f"Failed to hydrate GroupInfo model: {e}", extra={"payload": data})
   raise RuntimeError(f"Data mapping error in GroupInfo: {e}")
