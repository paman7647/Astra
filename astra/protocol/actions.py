# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
The EngineAPI is the primary interface for sending commands to the
WhatsApp Web engine.
"""

import logging
from typing import Optional, List, Any, Dict
from .gateway import ProtocolBridge
from .serializers import DataTransformer
from ..errors import MessageEditError
from ..models import Message, Chat, User

logger = logging.getLogger("Astra.Engine")

class EngineAPI:
 """
 Interface for WhatsApp engine operations.

 This class handles calls to the ProtocolBridge and translates
 the responses into Python objects.
 """

 def __init__(self, bridge: ProtocolBridge, client: Any = None):
  self._bridge = bridge
  self._client = client

 # --- Messaging ---

 async def send_text(self, chat_id: str, text: str, options: dict = None) -> Message:
  """Sends a text message to a chat."""
  opts = (options or {}).copy()
  if "waitForSend" not in opts:
   opts["waitForSend"] = False

  data = await self._bridge.call("sendMessage", {
   "to": chat_id,
   "text": text,
   "options": opts
  })
  return Message.from_payload(data, client=self._client)

 async def send_poll(self, to: str, question: str, options: List[str], poll_options: Optional[Dict[str, Any]] = None) -> Message:
  """
  Creates and sends a poll.
  """
  raw = await self._bridge.call("sendPoll", {
   "to": str(to),
   "name": question,
   "options": options,
   "pollOptions": poll_options or {}
  })
  return DataTransformer.to_message(raw, self._client)

 async def react(self, message_id: str, emoji: str) -> bool:
  """Adds a reaction to a message."""
  return await self._bridge.call("react", {"msgId": message_id, "emoji": emoji})

 async def delete_message(self, message_id: str, for_everyone: bool = True) -> bool:
  """Removes a message from the thread."""
  return await self._bridge.call("deleteMessage", {"msgId": message_id, "forEveryone": for_everyone})

 async def bulk_delete(self, message_ids: List[str], for_everyone: bool = True) -> bool:
  """Removes multiple messages from the thread."""
  return await self._bridge.call("bulkDeleteMessages", {"msgIds": message_ids, "forEveryone": for_everyone})

 async def edit_message(self, message_id: str, text: str) -> bool:
  """Edits a previously sent message."""
  res = await self._bridge.call("editMessage", {
   "msgId": message_id,
   "text": text
  })
  if isinstance(res, dict) and "error" in res:
   raise MessageEditError(res["error"])
  return True

 async def fetch_messages(self, chat_id: str, options: Optional[Dict[str, Any]] = None) -> List[Message]:
  """Loads earlier messages for a chat."""
  raw_msgs = await self._bridge.call("fetchMessages", {
   "chatId": chat_id,
   "searchOptions": options or {}
  })
  return [DataTransformer.to_message(m, self._client) for m in raw_msgs]

 async def sync_history(self, chat_id: str) -> bool:
  """Triggers a peer data operation request to sync history."""
  return await self._bridge.call("syncHistory", {"chatId": chat_id})

 async def send_media(self, to: str, media: str, mimetype: str, filename: Optional[str] = None, caption: Optional[str] = None, options: dict = None) -> Message:
  """Sends a media file."""
  raw = await self._bridge.call("sendMedia", {
   "to": to,
   "media": media,
   "mimetype": mimetype,
   "filename": filename,
   "caption": caption,
   "options": options or {}
  })
  return DataTransformer.to_message(raw, self._client)

 # --- Group Management ---

 async def create_group(self, title: str, participants: List[str]) -> str:
  """
  Creates a new group with the specified title and members.
  Returns the new Group ID.
  """
  return await self._bridge.call("createGroup", {"title": title, "participants": participants})

 async def add_members(self, group_id: str, participants: List[str]) -> bool:
  """Adds new participants to a group."""
  return await self._bridge.call("addMembers", {"groupId": group_id, "participants": participants})

 async def remove_members(self, group_id: str, participants: List[str]) -> bool:
  """Kicks participants from a group."""
  return await self._bridge.call("removeMembers", {"groupId": group_id, "participants": participants})

 async def get_invite_link(self, group_id: str) -> str:
  """Generates a group invite link."""
  return await self._bridge.call("getInviteLink", group_id)

 # --- Identity & Sync ---

 async def get_me(self) -> User:
  """Gets the authenticated user's profile."""
  raw = await self._bridge.call("getMe")
  return DataTransformer.to_user(raw)

 async def sync_data(self) -> bool:
  """Performs a deep sync of metadata from the server."""
  return await self._bridge.call("sync")

 # --- Status ---

 async def send_status(self, text: str, options: Optional[Dict[str, Any]] = None) -> bool:
  """Posts a text status update."""
  return await self._bridge.call("setMyStatus", {"status": text, "options": options or {}})

 async def send_media_status(self, data: str, mimetype: str, caption: str = "", options: Optional[Dict[str, Any]] = None) -> bool:
  """
  Sends a media status update.
  """
  return await self._bridge.call("postStatus", {
   "data": data,
   "mimetype": mimetype,
   "caption": caption,
   "options": options or {}
  })

 async def get_status_viewers(self, message_id: str) -> List[Dict[str, Any]]:
  """
  Retrieves the list of viewers for a status message.
  """
  return await self._bridge.call("getStatusViewers", {"msgId": message_id})

 async def set_profile_name(self, name: str) -> bool:
  """
  Updates the user's pushname.
  """
  return await self._bridge.call("setProfileName", {"name": name})

 async def set_about_text(self, text: str) -> bool:
  """
  Updates the user's 'About' text content.
  """
  # Note: mapping is setAbout in js_engine.py
  return await self._bridge.call("setAbout", {"about": text})

 async def set_privacy(self, category: str, value: str) -> bool:
  """
  Sets a privacy setting.
  Categories: 'last_seen', 'profile_pic', 'about', 'status', 'read_receipts'
  """
  return await self._bridge.call("setPrivacy", {"category": category, "value": value})

 async def get_privacy_settings(self) -> Dict[str, Any]:
  """
  Retrieves current privacy settings.
  """
  return await self._bridge.call("getPrivacySettings", {})

 # --- Utility ---

 async def get_contact(self, contact_id: str) -> User:
  """Fetches metadata for a specific contact."""
  raw = await self._bridge.call("getContactById", contact_id)
  return DataTransformer.to_user(raw)

 async def get_chat(self, chat_id: str) -> Chat:
  """Fetches a specific chat thread."""
  raw = await self._bridge.call("getChatById", chat_id)
  return DataTransformer.to_chat(raw)

 async def get_chats(self) -> List[Chat]:
  """Fetches all chats."""
  raw_chats = await self._bridge.call("getChats")
  return [DataTransformer.to_chat(c) for c in raw_chats]

 async def scan_dom(self, section: str) -> List[Dict[str, Any]]:
  """Performs a deep DOM scan of a specific section."""
  return await self._bridge.call("scanDOM", section)

 async def generate_dom_report(self, section: str) -> str:
  """Generates a detailed text report of stable selectors in a section."""
  return await self._bridge.call("generateDOMReport", section)

 async def logout(self) -> bool:
  """Terminated the current session and logs out."""
  return await self._bridge.call("logout")

 async def send_chat_state(self, chat_id: str, state: str) -> bool:
  """
  Sets the chat state (typing, recording, clear).
  """
  return await self._bridge.call("sendChatState", {"chatId": chat_id, "state": state})
