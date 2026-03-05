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
from ..errors import MessageEditError, BridgeCallError
from ..types import Message, Chat, User

logger = logging.getLogger("Engine")

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

 async def promote(self, group_id: str, participants: List[str]) -> bool:
  """Promotes participants to admin in a group."""
  return await self._bridge.call("promote", {"groupId": group_id, "participants": participants})

 async def demote(self, group_id: str, participants: List[str]) -> bool:
  """Demotes participants from admin in a group."""
  return await self._bridge.call("demote", {"groupId": group_id, "participants": participants})

 async def get_group_info(self, group_id: str) -> Dict[str, Any]:
  """Retrieves detailed info about a group."""
  return await self._bridge.call("getGroupInfo", group_id)

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
  JS bridge first → Playwright keyboard fallback.
  """
  try:
   return await self._bridge.call("setProfileName", {"name": name})
  except BridgeCallError as e:
   logger.warning(f"JS setProfileName failed ({e}), trying Playwright fallback...")
   return await self._bridge.set_profile_name_native(name)

 async def set_about_text(self, text: str) -> bool:
  """
  Updates the user's 'About' text content.
  JS bridge first → Playwright keyboard fallback.
  """
  try:
   return await self._bridge.call("setAbout", {"about": text})
  except BridgeCallError as e:
   logger.warning(f"JS setAbout failed ({e}), trying Playwright fallback...")
   return await self._bridge.set_about_native(text)

 async def update_profile_pic(self, media: str) -> bool:
  """
  Updates the authenticated user's profile picture.
  """
  return await self._bridge.call("updateProfilePic", {"data": media})

 async def update_group_pic(self, group_id: str, media: str) -> bool:
  """
  Updates a group's profile picture.
  """
  return await self._bridge.call("updateGroupPic", {"groupId": group_id, "data": media})

 async def set_privacy(self, category: str, value: str) -> bool:
  """
  Sets a privacy setting.
  Categories: 'last_seen', 'profile_pic', 'about', 'status', 'read_receipts'
  JS bridge first → Playwright keyboard/mouse fallback.
  """
  try:
   return await self._bridge.call("setPrivacy", {"category": category, "value": value})
  except BridgeCallError as e:
   logger.warning(f"JS setPrivacy failed ({e}), trying Playwright fallback...")
   return await self._bridge.set_privacy_native(category, value)

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

 # --- Group Settings (NEWWP) ---

 async def set_group_subject(self, group_id: str, subject: str) -> bool:
  """Changes the group's display name/subject."""
  return await self._bridge.call("setGroupSubject", {"groupId": group_id, "subject": subject})

 async def set_group_description(self, group_id: str, description: str) -> bool:
  """Updates the group's description text."""
  return await self._bridge.call("setGroupDescription", {"groupId": group_id, "description": description})

 async def set_group_property(self, group_id: str, property: str, value: int) -> bool:
  """
  Sets a group property.
  
  Properties:
      - 'member_add_mode': 0 = admins only, 1 = all members
      - 'announcement': 1 = admins only can send, 0 = all
      - 'restrict': 1 = admins only can edit info, 0 = all
  """
  return await self._bridge.call("setGroupProperty", {
   "groupId": group_id, "property": property, "value": value
  })

 async def set_admins_only_add(self, group_id: str, admins_only: bool = True) -> bool:
  """Only admins can add new members."""
  return await self._bridge.call("setAddMembersAdminsOnly", {
   "groupId": group_id, "adminsOnly": admins_only
  })

 async def set_admins_only_send(self, group_id: str, admins_only: bool = True) -> bool:
  """Only admins can send messages (announcement mode)."""
  return await self._bridge.call("setMessagesAdminsOnly", {
   "groupId": group_id, "adminsOnly": admins_only
  })

 async def set_admins_only_info(self, group_id: str, admins_only: bool = True) -> bool:
  """Only admins can edit group info."""
  return await self._bridge.call("setInfoAdminsOnly", {
   "groupId": group_id, "adminsOnly": admins_only
  })

 # --- Membership Requests (NEWWP) ---

 async def get_membership_requests(self, group_id: str) -> List[Dict[str, Any]]:
  """Gets pending join requests for a group."""
  return await self._bridge.call("getGroupMembershipRequests", group_id)

 async def approve_membership(self, group_id: str, requester_ids: List[str] = None) -> List[Dict[str, Any]]:
  """Approves pending join requests. If no IDs given, approves all."""
  return await self._bridge.call("membershipRequestAction", {
   "groupId": group_id, "action": "approve", "requesterIds": requester_ids or []
  })

 async def reject_membership(self, group_id: str, requester_ids: List[str] = None) -> List[Dict[str, Any]]:
  """Rejects pending join requests. If no IDs given, rejects all."""
  return await self._bridge.call("membershipRequestAction", {
   "groupId": group_id, "action": "reject", "requesterIds": requester_ids or []
  })

 async def revoke_invite(self, group_id: str) -> str:
  """Revokes the current invite link and generates a new one."""
  return await self._bridge.call("revokeInviteLink", group_id)

 async def join_via_invite(self, code: str) -> bool:
  """Joins a group via an invite code."""
  return await self._bridge.call("joinViaLink", code)

 async def leave_group(self, group_id: str) -> bool:
  """Leaves a group."""
  return await self._bridge.call("leaveGroup", group_id)

 # --- Chat Operations (NEWWP) ---

 async def clear_chat(self, chat_id: str) -> bool:
  """Clears all messages from a chat (locally)."""
  return await self._bridge.call("clearChat", chat_id)

 async def delete_chat(self, chat_id: str) -> bool:
  """Deletes a chat entirely."""
  return await self._bridge.call("deleteChat", chat_id)

 async def forward_message(self, chat_id: str, message_id: str) -> bool:
  """Forwards a message to another chat."""
  return await self._bridge.call("forwardMessage", {"chatId": chat_id, "msgId": message_id})

 async def pin_message(self, message_id: str, pin: bool = True, duration: int = 604800) -> bool:
  """
  Pins or unpins a message in a chat.
  Duration is in seconds (default: 7 days).
  """
  return await self._bridge.call("pinMessage", {
   "msgId": message_id, "pin": pin, "duration": duration
  })

 # --- Call Management (NEWWP) ---

 async def reject_call(self, peer_jid: str, call_id: str) -> bool:
  """Rejects an incoming call."""
  return await self._bridge.call("rejectCall", {"peerJid": peer_jid, "callId": call_id})

 # --- Chat Management ---

 async def archive_chat(self, chat_id: str, archive: bool = True) -> bool:
  """Archives or unarchives a chat."""
  return await self._bridge.call("archiveChat", {"chatId": chat_id, "archive": archive})

 async def pin_chat(self, chat_id: str, pin: bool = True) -> bool:
  """Pins or unpins a chat."""
  return await self._bridge.call("pinChat", {"chatId": chat_id, "pin": pin})

 async def mute_chat(self, chat_id: str, duration: int = -1) -> bool:
  """Mutes a chat. Duration -1 = forever."""
  return await self._bridge.call("muteChat", {"chatId": chat_id, "duration": duration})

 async def mark_seen(self, chat_id: str) -> bool:
  """Marks all messages in a chat as read."""
  return await self._bridge.call("markSeen", chat_id)

 async def block_contact(self, contact_id: str, block: bool = True) -> bool:
  """Blocks or unblocks a contact."""
  return await self._bridge.call("block", {"chatId": contact_id, "block": block})

 # --- Contact & Number Lookup (NEWWP) ---

 async def get_number_id(self, number: str) -> Optional[Dict[str, Any]]:
  """
  Checks if a phone number is registered on WhatsApp.
  Returns the registered WID object, or None if not on WhatsApp.
  """
  if not number.endswith("@c.us"):
   number += "@c.us"
  return await self._bridge.call("getNumberId", number)

 async def is_registered(self, number: str) -> bool:
  """Checks if a phone number is registered on WhatsApp."""
  result = await self.get_number_id(number)
  return result is not None

 async def get_profile_pic_url(self, contact_id: str) -> Optional[str]:
  """Gets a contact's profile picture URL (if privacy permits)."""
  return await self._bridge.call("getProfilePicUrl", contact_id)

 async def get_common_groups(self, contact_id: str) -> List[str]:
  """Gets group IDs that you share with a contact."""
  return await self._bridge.call("getCommonGroups", contact_id)

 async def get_pinned_messages(self, chat_id: str) -> List[Message]:
  """Gets all pinned messages in a chat."""
  raw = await self._bridge.call("getPinnedMessages", chat_id)
  return [DataTransformer.to_message(m, self._client) for m in (raw or [])]

 async def mark_unread(self, chat_id: str) -> bool:
  """Marks a chat as unread."""
  return await self._bridge.call("markUnread", chat_id)

 async def send_presence(self, available: bool = True) -> bool:
  """Sets your online presence (online/offline)."""
  method = "sendPresenceAvailable" if available else "sendPresenceUnavailable"
  return await self._bridge.call(method)

 async def search_messages(self, query: str, chat_id: Optional[str] = None, limit: int = 25) -> List[Message]:
  """Searches for messages matching a query."""
  raw = await self._bridge.call("searchMessages", {
   "query": query, "chatId": chat_id, "limit": limit
  })
  return [DataTransformer.to_message(m, self._client) for m in (raw or [])]

 async def set_display_name(self, name: str) -> bool:
  """Sets your WhatsApp push name (display name visible to non-contacts)."""
  return await self._bridge.call("setDisplayName", name)

 async def get_state(self) -> Optional[str]:
  """Gets the current connection state (CONNECTED, OPENING, etc)."""
  return await self._bridge.call("getState")


