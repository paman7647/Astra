# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module implements the Conversation API for Astra.
It allows for stateful, interactive dialog flows within a chat.
"""

import asyncio
import logging
from typing import Optional, Any, TYPE_CHECKING
from ..models import Message

if TYPE_CHECKING:
 from .client import Client

logger = logging.getLogger("Chat")

class Conversation:
 """
 Conversation manager.

 Provides an imperative interface for interactive message flows.

 Example:
  async with client.conversation(chat_id) as conv:
   await conv.send_message("What's your name?")
   name_msg = await conv.get_response()
   await conv.send_message(f"Hello, {name_msg.text}!")
 """

 def __init__(self, client: 'Client', chat_id: str, timeout: float = 120.0):
  self._client = client
  self.chat_id = chat_id
  self.timeout = timeout
  self._queue = asyncio.Queue()
  self._subscription_id = None

 async def __aenter__(self):
  # Register a temporary listener for this chat
  from ..events import Filters

  # Define a filter that only catches messages from this specific chat
  # Special case: allow outgoing messages if we are in a self-chat for testing
  criteria = Filters.chat(self.chat_id)

  # Don't strictly enforce incoming if we're in the same chat as 'me'
  # (This helps with subagent/manual testing in self-chat)
  try:
   me = await self._client.get_me()
   if me and me.id.serialized != self.chat_id:
    criteria &= Filters.incoming
  except:
   # Fallback to incoming only if get_me fails
   criteria &= Filters.incoming

  async def _handler(msg: Message):
   await self._queue.put(msg)

  self._subscription_id = self._client.dispatcher.subscribe("message", _handler, criteria=criteria)
  return self

 async def __aexit__(self, exc_type, exc_val, exc_tb):
  if self._subscription_id:
   self._client.dispatcher.unsubscribe(self._subscription_id)

 async def send_message(self, text: str, **kwargs) -> Message:
  """Sends a message to the current conversation chat."""
  return await self._client.send_message(self.chat_id, text, **kwargs)

 async def get_response(self, timeout: Optional[float] = None) -> Message:
  """
  Waits for a response message in the conversation.
  Skips the message if it was sent by the bot (e.g. the prompt).
  """
  to = timeout or self.timeout
  try:
   while True:
    msg = await asyncio.wait_for(self._queue.get(), timeout=to)
    # Skip the prompt we just sent if it was captured
    if msg.id == getattr(self, '_last_sent_id', None):
     continue
    return msg
  except asyncio.TimeoutError:
   logger.warning(f"Conversation with {self.chat_id} timed out.")
   raise

 async def ask(self, text: str, timeout: Optional[float] = None, **kwargs) -> Message:
  """Helper to send a message and immediately wait for a response."""
  sent = await self.send_message(text, **kwargs)
  self._last_sent_id = sent.id
  return await self.get_response(timeout=timeout)
