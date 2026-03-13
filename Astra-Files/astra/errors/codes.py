# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Central registry of all Astra error codes.

Error codes follow Exxx numbering by category:
 E1xxx Authentication
 E2xxx Connection & Browser
 E3xxx Messaging & Chat
 E4xxx Groups
 E5xxx Account & Profile
 E6xxx Bridge & Engine
 E7xxx Validation
 E8xxx WhatsApp-Side (rate limits, bans, server)
"""

from enum import Enum
from typing import NamedTuple


class _CodeDef(NamedTuple):
 code: str
 category: str
 message: str
 hint: str
 retryable: bool


class ErrorCode(Enum):
 """
 Every known Astra error code.

 Usage::

  from astra.errors.codes import ErrorCode
  raise LoginFailedError(ErrorCode.AUTH_FAILED)
 """

 # ── E1xxx · Authentication ─────────────────────────────
 AUTH_FAILED = _CodeDef(
  "E1001", "Auth",
  "Authentication failed.",
  "Check your internet and try scanning the QR code again.",
  True
 )
 AUTH_QR_TIMEOUT = _CodeDef(
  "E1002", "Auth",
  "QR code scan timed out.",
  "Restart the client to generate a new QR code.",
  True
 )
 AUTH_PAIRING_FAILED = _CodeDef(
  "E1003", "Auth",
  "Phone pairing failed.",
  "Ensure the phone number is correct and WhatsApp is installed.",
  True
 )
 AUTH_SESSION_EXPIRED = _CodeDef(
  "E1004", "Auth",
  "Session has expired.",
  "Re-authenticate by scanning the QR code.",
  True
 )
 AUTH_RATE_LIMITED = _CodeDef(
  "E1005", "Auth",
  "Too many login attempts.",
  "Wait 5-10 minutes before trying again. Avoid rapid re-logins.",
  False
 )
 AUTH_PHONE_DISCONNECTED = _CodeDef(
  "E1006", "Auth",
  "Primary phone lost connection.",
  "Ensure your phone has an active internet connection.",
  True
 )

 # ── E2xxx · Connection & Browser ───────────────────────
 CONN_BROWSER_START = _CodeDef(
  "E2001", "Connection",
  "Failed to launch browser.",
  "Check that Playwright browsers are installed: python -m playwright install",
  False
 )
 CONN_BROWSER_CRASH = _CodeDef(
  "E2002", "Connection",
  "Browser process crashed.",
  "This is usually a resource issue. Try reducing headless=False for debugging.",
  True
 )
 CONN_BROWSER_LIMIT = _CodeDef(
  "E2003", "Connection",
  "Another browser instance is using this session profile.",
  "Close other Astra instances or WhatsApp tabs using this session.",
  False
 )
 CONN_PAGE_UNRESPONSIVE = _CodeDef(
  "E2004", "Connection",
  "Browser page is unresponsive.",
  "The page may have frozen. Astra will attempt recovery.",
  True
 )
 CONN_LOST = _CodeDef(
  "E2005", "Connection",
  "Lost connection to the browser.",
  "The browser might have crashed. Astra will attempt to reconnect.",
  True
 )
 CONN_WS_DISCONNECT = _CodeDef(
  "E2006", "Connection",
  "WebSocket connection to WhatsApp dropped.",
  "Check your internet connection. This may also indicate a server-side issue.",
  True
 )
 CONN_NAVIGATION_FAILED = _CodeDef(
  "E2007", "Connection",
  "Failed to navigate to WhatsApp Web.",
  "Check your internet connection and firewall settings.",
  True
 )
 CONN_STARTUP_FAILED = _CodeDef(
  "E2008", "Connection",
  "Client startup failed.",
  "Check the error log for details. Usually a browser or auth issue.",
  True
 )

 # ── E3xxx · Messaging & Chat ───────────────────────────
 MSG_SEND_FAILED = _CodeDef(
  "E3001", "Messaging",
  "Message failed to send.",
  "Ensure the recipient JID is correct and you have an active connection.",
  True
 )
 MSG_SEND_TIMEOUT = _CodeDef(
  "E3002", "Messaging",
  "Message send timed out.",
  "WhatsApp server did not acknowledge. The message may still deliver.",
  True
 )
 MSG_INVALID_RECIPIENT = _CodeDef(
  "E3003", "Messaging",
  "Invalid recipient.",
  "JID must end with @c.us (contacts) or @g.us (groups).",
  False
 )
 MSG_MEDIA_UPLOAD = _CodeDef(
  "E3004", "Messaging",
  "Media upload failed.",
  "Check file path, format, and size (max 64MB for documents).",
  True
 )
 MSG_MEDIA_DOWNLOAD = _CodeDef(
  "E3005", "Messaging",
  "Media download failed.",
  "The media may have expired or the sender deleted it.",
  True
 )
 MSG_EDIT_FAILED = _CodeDef(
  "E3006", "Messaging",
  "Failed to edit message.",
  "Only your own messages sent within 15 minutes can be edited.",
  False
 )
 MSG_DELETE_FAILED = _CodeDef(
  "E3007", "Messaging",
  "Failed to delete message.",
  "You can only delete your own messages. 'Delete for everyone' has a time limit.",
  False
 )
 MSG_REACT_FAILED = _CodeDef(
  "E3008", "Messaging",
  "Failed to react to message.",
  "The message might have been deleted or the chat is read-only.",
  False
 )
 MSG_POLL_FAILED = _CodeDef(
  "E3010", "Messaging",
  "Failed to create poll.",
  "Polls need a question and at least 2 options (max 12).",
  False
 )
 MSG_POLL_VOTE_FAILED = _CodeDef(
  "E3011", "Messaging",
  "Failed to vote on poll.",
  "The poll may have been deleted or you already voted.",
  False
 )
 MSG_FORWARD_FAILED = _CodeDef(
  "E3012", "Messaging",
  "Failed to forward message.",
  "The original message may have been deleted.",
  False
 )
 MSG_CHAT_NOT_FOUND = _CodeDef(
  "E3020", "Messaging",
  "Chat not found.",
  "The chat ID may be incorrect or the chat was deleted.",
  False
 )
 MSG_CHAT_ARCHIVE = _CodeDef(
  "E3021", "Messaging",
  "Chat archive/unarchive failed.",
  "Ensure the chat exists and you have the correct permissions.",
  False
 )
 MSG_CHAT_MUTE = _CodeDef(
  "E3022", "Messaging",
  "Chat mute/unmute failed.",
  "Ensure the chat exists.",
  False
 )
 MSG_CHAT_PIN = _CodeDef(
  "E3023", "Messaging",
  "Chat pin/unpin failed.",
  "Maximum 3 chats can be pinned. Unpin one first.",
  False
 )
 MSG_SEEN_FAILED = _CodeDef(
  "E3024", "Messaging",
  "Failed to mark chat as seen.",
  "The chat may not exist.",
  False
 )
 MSG_SYNC_FAILED = _CodeDef(
  "E3025", "Messaging",
  "Chat history sync failed.",
  "WhatsApp may be throttling requests. Try again later.",
  True
 )

 # ── E4xxx · Groups ─────────────────────────────────────
 GRP_CREATE_FAILED = _CodeDef(
  "E4001", "Group",
  "Failed to create group.",
  "You need at least one other participant. Check JID formats.",
  False
 )
 GRP_ADD_FAILED = _CodeDef(
  "E4002", "Group",
  "Failed to add member(s) to group.",
  "You must be an admin. The user may have privacy settings preventing this.",
  False
 )
 GRP_REMOVE_FAILED = _CodeDef(
  "E4003", "Group",
  "Failed to remove member(s) from group.",
  "You must be an admin to remove participants.",
  False
 )
 GRP_PROMOTE_FAILED = _CodeDef(
  "E4004", "Group",
  "Failed to promote member to admin.",
  "Only group admins can promote other members.",
  False
 )
 GRP_DEMOTE_FAILED = _CodeDef(
  "E4005", "Group",
  "Failed to demote admin.",
  "You cannot demote the group creator.",
  False
 )
 GRP_JOIN_FAILED = _CodeDef(
  "E4006", "Group",
  "Failed to join group via invite link.",
  "The invite link may have expired or been revoked.",
  False
 )
 GRP_INFO_FAILED = _CodeDef(
  "E4007", "Group",
  "Failed to get group info.",
  "You may not be a member of this group anymore.",
  False
 )
 GRP_LEAVE_FAILED = _CodeDef(
  "E4008", "Group",
  "Failed to leave group.",
  "An internal error occurred. Try again.",
  True
 )
 GRP_SETTINGS_FAILED = _CodeDef(
  "E4010", "Group",
  "Failed to update group settings.",
  "Only admins can change group settings.",
  False
 )
 GRP_PERMISSION_DENIED = _CodeDef(
  "E4020", "Group",
  "Permission denied for group action.",
  "This action requires admin privileges.",
  False
 )
 GRP_MEMBERSHIP_FAILED = _CodeDef(
  "E4021", "Group",
  "Failed to process membership request.",
  "You must be a group admin to approve or reject join requests.",
  False
 )

 CALL_REJECT_FAILED = _CodeDef(
  "E4030", "Call",
  "Failed to reject incoming call.",
  "The call may have already ended or the required modules are unavailable.",
  False
 )

 # ── E5xxx · Account & Profile ──────────────────────────
 ACCT_PROFILE_READ = _CodeDef(
  "E5001", "Account",
  "Failed to read profile.",
  "WhatsApp may still be loading. Try again in a few seconds.",
  True
 )
 ACCT_PROFILE_UPDATE = _CodeDef(
  "E5002", "Account",
  "Failed to update profile.",
  "Check that the value is within WhatsApp's limits.",
  False
 )
 ACCT_STATUS_POST = _CodeDef(
  "E5010", "Account",
  "Failed to post status/story.",
  "The Status tab may not be accessible. Try opening it manually first.",
  True
 )
 ACCT_STATUS_MEDIA = _CodeDef(
  "E5011", "Account",
  "Failed to post media status.",
  "Check file format and size. Images: JPEG/PNG. Videos: MP4 (max 30s).",
  True
 )
 ACCT_PRIVACY_FAILED = _CodeDef(
  "E5020", "Account",
  "Failed to read/update privacy settings.",
  "Privacy settings require navigating the Settings UI. Ensure no dialogs are open.",
  True
 )
 ACCT_BLOCK_FAILED = _CodeDef(
  "E5030", "Account",
  "Failed to block/unblock contact.",
  "The contact JID may be invalid.",
  False
 )
 ACCT_PP_FAILED = _CodeDef(
  "E5040", "Account",
  "Failed to get/set profile picture.",
  "The contact may have disabled profile picture visibility.",
  False
 )
 ACCT_LOGOUT_FAILED = _CodeDef(
  "E5050", "Account",
  "Logout failed.",
  "The session may already be disconnected.",
  False
 )

 # ── E6xxx · Bridge & Engine ────────────────────────────
 BRIDGE_METHOD_NOT_FOUND = _CodeDef(
  "E6001", "Bridge",
  "Bridge method not found.",
  "The requested function does not exist in the JS engine. Check method name.",
  False
 )
 BRIDGE_CALL_FAILED = _CodeDef(
  "E6002", "Bridge",
  "Bridge call failed.",
  "A JavaScript error occurred in the browser. Check the inner error.",
  True
 )
 BRIDGE_EVAL_FAILED = _CodeDef(
  "E6003", "Bridge",
  "JavaScript evaluation failed.",
  "The browser context may have been destroyed. Astra will attempt recovery.",
  True
 )
 BRIDGE_NOT_CONNECTED = _CodeDef(
  "E6004", "Bridge",
  "Bridge is not connected.",
  "Wait for the client to finish starting before making calls.",
  True
 )
 BRIDGE_ENGINE_STALL = _CodeDef(
  "E6005", "Bridge",
  "Engine stall detected.",
  "No events received for an extended period. Astra is attempting recovery.",
  True
 )
 BRIDGE_MODULE_MISSING = _CodeDef(
  "E6006", "Bridge",
  "Required WA module not found.",
  "WhatsApp may have updated its internal structure. Check for Astra updates.",
  False
 )
 BRIDGE_INJECTION_FAILED = _CodeDef(
  "E6007", "Bridge",
  "Script injection failed.",
  "The page may not be on the correct origin yet.",
  True
 )
 BRIDGE_STORE_UNAVAILABLE = _CodeDef(
  "E6008", "Bridge",
  "WhatsApp Store object is unavailable.",
  "Modules haven't loaded yet. Wait for full initialization.",
  True
 )

 # ── E7xxx · Validation ─────────────────────────────────
 VAL_INVALID_JID = _CodeDef(
  "E7001", "Validation",
  "Invalid JID format.",
  "JID must match: number@c.us or number@g.us",
  False
 )
 VAL_EMPTY_TEXT = _CodeDef(
  "E7002", "Validation",
  "Text content cannot be empty.",
  "Provide a non-empty text string.",
  False
 )
 VAL_MISSING_KEYS = _CodeDef(
  "E7003", "Validation",
  "Required parameters are missing.",
  "Check the function signature for required arguments.",
  False
 )
 VAL_INVALID_PHONE = _CodeDef(
  "E7004", "Validation",
  "Invalid phone number format.",
  "Use international format without + or spaces: e.g., 14155552671",
  False
 )
 VAL_INVALID_MEDIA = _CodeDef(
  "E7005", "Validation",
  "Invalid media input.",
  "Provide a valid file path, URL, or base64 string.",
  False
 )
 VAL_PAYLOAD_TOO_LARGE = _CodeDef(
  "E7006", "Validation",
  "Payload exceeds maximum size.",
  "Reduce the size of the data being sent.",
  False
 )

 # ── E8xxx · WhatsApp-Side ──────────────────────────────
 WA_RATE_LIMITED = _CodeDef(
  "E8001", "WhatsApp",
  "Rate limited by WhatsApp.",
  "You are sending too many requests. Wait 5-10 minutes before retrying.",
  True
 )
 WA_ECOSYSTEM_BLOCK = _CodeDef(
  "E8002", "WhatsApp",
  "Message blocked for ecosystem protection.",
  "WhatsApp has flagged this as potential spam. Reduce automation frequency.",
  False
 )
 WA_ACCOUNT_BANNED = _CodeDef(
  "E8003", "WhatsApp",
  "Account temporarily or permanently banned.",
  "Contact WhatsApp support. Avoid using unofficial automation on this number.",
  False
 )
 WA_SERVER_DOWN = _CodeDef(
  "E8004", "WhatsApp",
  "WhatsApp servers are experiencing issues.",
  "Wait and try again. Check https://downdetector.com/status/whatsapp/",
  True
 )
 WA_VERSION_MISMATCH = _CodeDef(
  "E8005", "WhatsApp",
  "WhatsApp Web version mismatch.",
  "Clear browser cache and reload. WhatsApp may have pushed an update.",
  True
 )
 WA_MULTIDEVICE_LIMIT = _CodeDef(
  "E8006", "WhatsApp",
  "Maximum linked devices reached.",
  "Remove old linked devices from WhatsApp → Settings → Linked Devices.",
  False
 )
 WA_ENCRYPTION_ERROR = _CodeDef(
  "E8007", "WhatsApp",
  "End-to-end encryption error.",
  "This usually resolves on its own. Try restarting the client.",
  True
 )
 WA_CONTACT_NOT_ON_WA = _CodeDef(
  "E8008", "WhatsApp",
  "Contact is not registered on WhatsApp.",
  "Verify the phone number and ensure they have WhatsApp installed.",
  False
 )

 # --- Accessors ---
 @property
 def id(self) -> str:
  return self.value.code

 @property
 def category(self) -> str:
  return self.value.category

 @property
 def default_message(self) -> str:
  return self.value.message

 @property
 def default_hint(self) -> str:
  return self.value.hint

 @property
 def retryable(self) -> bool:
  return self.value.retryable
