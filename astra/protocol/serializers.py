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
from ..models import Message, Chat, User

logger = logging.getLogger("Astra.Transformer")

class DataTransformer:
 """
 Expert-grade transformer for bridge payloads.

 Responsible for validating and hydrating Astra models from raw
 JavaScript runtime dictionaries.
 """

 @staticmethod
 def to_message(data: Dict[str, Any], client: Any = None) -> Message:
  """Converts a raw JSON payload into a Message model."""
  try:
   message = Message.from_payload(data, client=client)
   logger.debug(f"Hydrated message: {message.id}")
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
