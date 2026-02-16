# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Typed exception classes for every failure category in Astra.

Each exception auto-wires to its ErrorCode, providing structured
messages, hints, codes, and retry guidance out of the box.
"""

from .base import AstraError, Severity
from .codes import ErrorCode
from typing import Optional, Dict, Any


def _from_code(
 error_code: ErrorCode,
 message: Optional[str] = None,
 hint: Optional[str] = None,
 severity: Severity = Severity.ERROR,
 payload: Optional[Dict[str, Any]] = None,
 cause: Optional[Exception] = None
) -> dict:
 """Helper to build kwargs from an ErrorCode."""
 return dict(
  message=message or error_code.default_message,
  code=error_code.id,
  hint=hint or error_code.default_hint,
  severity=severity,
  retryable=error_code.retryable,
  payload=payload or {},
  cause=cause
 )


# ═══════════════════════════════════════════════════════════
# E1xxx · Authentication
# ═══════════════════════════════════════════════════════════

class LoginFailedError(AstraError):
 """[E1001] Authentication with WhatsApp failed."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.AUTH_FAILED, message, cause=cause, **kw))

class QRTimeoutError(AstraError):
 """[E1002] QR code scan timed out."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.AUTH_QR_TIMEOUT, message, **kw))

class PairingError(AstraError):
 """[E1003] Phone pairing failed."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.AUTH_PAIRING_FAILED, message, cause=cause, **kw))

class SessionExpiredError(AstraError):
 """[E1004] Session has expired."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.AUTH_SESSION_EXPIRED, message, **kw))

class AuthRateLimitError(AstraError):
 """[E1005] Too many login attempts."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.AUTH_RATE_LIMITED, message, severity=Severity.WARNING, **kw))

class PhoneDisconnectedError(AstraError):
 """[E1006] Primary phone lost connection."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.AUTH_PHONE_DISCONNECTED, message, **kw))


# ═══════════════════════════════════════════════════════════
# E2xxx · Connection & Browser
# ═══════════════════════════════════════════════════════════

class BrowserStartError(AstraError):
 """[E2001] Failed to launch browser."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_BROWSER_START, message, cause=cause, severity=Severity.FATAL, **kw))

class BrowserCrashError(AstraError):
 """[E2002] Browser process crashed."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_BROWSER_CRASH, message, severity=Severity.FATAL, **kw))

class BrowserLimitError(AstraError):
 """[E2003] Another browser instance is using this session."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_BROWSER_LIMIT, message, **kw))

class PageUnresponsiveError(AstraError):
 """[E2004] Browser page is unresponsive."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_PAGE_UNRESPONSIVE, message, **kw))

class ConnectionLostError(AstraError):
 """[E2005] Lost connection to the browser."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_LOST, message, severity=Severity.FATAL, **kw))

class WebSocketDisconnectError(AstraError):
 """[E2006] WebSocket connection to WhatsApp dropped."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_WS_DISCONNECT, message, **kw))

class NavigationError(AstraError):
 """[E2007] Failed to navigate to WhatsApp Web."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_NAVIGATION_FAILED, message, **kw))

class StartupError(AstraError):
 """[E2008] Client startup failed."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.CONN_STARTUP_FAILED, message, cause=cause, severity=Severity.FATAL, **kw))


# ═══════════════════════════════════════════════════════════
# E3xxx · Messaging & Chat
# ═══════════════════════════════════════════════════════════

class MessageSendError(AstraError):
 """[E3001] Message failed to send."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_SEND_FAILED, message, cause=cause, **kw))

class MessageTimeoutError(AstraError):
 """[E3002] Message send timed out."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_SEND_TIMEOUT, message, **kw))

class InvalidRecipientError(AstraError):
 """[E3003] Invalid recipient JID."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_INVALID_RECIPIENT, message, severity=Severity.WARNING, **kw))

class MediaUploadError(AstraError):
 """[E3004] Media upload failed."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_MEDIA_UPLOAD, message, cause=cause, **kw))

class MediaDownloadError(AstraError):
 """[E3005] Media download failed."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_MEDIA_DOWNLOAD, message, **kw))

class MessageEditError(AstraError):
 """[E3006] Failed to edit message."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_EDIT_FAILED, message, **kw))

class MessageDeleteError(AstraError):
 """[E3007] Failed to delete message."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_DELETE_FAILED, message, **kw))

class ReactionError(AstraError):
 """[E3008] Failed to react to message."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_REACT_FAILED, message, **kw))

class PollError(AstraError):
 """[E3010] Failed to create poll."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_POLL_FAILED, message, cause=cause, **kw))

class PollVoteError(AstraError):
 """[E3011] Failed to vote on poll."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_POLL_VOTE_FAILED, message, **kw))

class ChatNotFoundError(AstraError):
 """[E3020] Chat not found."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_CHAT_NOT_FOUND, message, **kw))

class ChatOperationError(AstraError):
 """[E3021-E3025] General chat operation failure."""
 def __init__(self, message: str = None, code: ErrorCode = ErrorCode.MSG_CHAT_ARCHIVE, **kw):
  super().__init__(**_from_code(code, message, **kw))

class SyncError(AstraError):
 """[E3025] Chat sync failed."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.MSG_SYNC_FAILED, message, **kw))


# ═══════════════════════════════════════════════════════════
# E4xxx · Groups
# ═══════════════════════════════════════════════════════════

class GroupCreateError(AstraError):
 """[E4001] Failed to create group."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.GRP_CREATE_FAILED, message, cause=cause, **kw))

class GroupMemberError(AstraError):
 """[E4002-E4003] Failed to add/remove member."""
 def __init__(self, message: str = None, code: ErrorCode = ErrorCode.GRP_ADD_FAILED, **kw):
  super().__init__(**_from_code(code, message, **kw))

class GroupPermissionError(AstraError):
 """[E4020] Permission denied for group action."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.GRP_PERMISSION_DENIED, message, severity=Severity.WARNING, **kw))

class GroupJoinError(AstraError):
 """[E4006] Failed to join group via invite link."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.GRP_JOIN_FAILED, message, **kw))

class GroupInfoError(AstraError):
 """[E4007] Failed to get group info."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.GRP_INFO_FAILED, message, **kw))

class GroupSettingsError(AstraError):
 """[E4010] Failed to update group settings."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.GRP_SETTINGS_FAILED, message, **kw))


# ═══════════════════════════════════════════════════════════
# E5xxx · Account & Profile
# ═══════════════════════════════════════════════════════════

class ProfileReadError(AstraError):
 """[E5001] Failed to read profile."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.ACCT_PROFILE_READ, message, **kw))

class ProfileUpdateError(AstraError):
 """[E5002] Failed to update profile."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.ACCT_PROFILE_UPDATE, message, **kw))

class StatusPostError(AstraError):
 """[E5010] Failed to post status/story."""
 def __init__(self, message: str = None, cause: Exception = None, **kw):
  super().__init__(**_from_code(ErrorCode.ACCT_STATUS_POST, message, cause=cause, **kw))

class PrivacyError(AstraError):
 """[E5020] Failed to read/update privacy settings."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.ACCT_PRIVACY_FAILED, message, **kw))

class BlockError(AstraError):
 """[E5030] Failed to block/unblock contact."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.ACCT_BLOCK_FAILED, message, **kw))


# ═══════════════════════════════════════════════════════════
# E6xxx · Bridge & Engine
# ═══════════════════════════════════════════════════════════

class BridgeCallError(AstraError):
 """[E6002] Bridge call failed."""
 def __init__(self, message: str = None, cause: Exception = None, method: str = None, **kw):
  payload = {"method": method} if method else {}
  super().__init__(**_from_code(ErrorCode.BRIDGE_CALL_FAILED, message, cause=cause, payload=payload, **kw))

class BridgeMethodNotFoundError(AstraError):
 """[E6001] Bridge method not found."""
 def __init__(self, method: str = None, **kw):
  msg = f"Bridge method '{method}' not found." if method else None
  super().__init__(**_from_code(ErrorCode.BRIDGE_METHOD_NOT_FOUND, msg, **kw))

class EngineStallError(AstraError):
 """[E6005] Engine stall detected."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.BRIDGE_ENGINE_STALL, message, severity=Severity.WARNING, **kw))

class ModuleMissingError(AstraError):
 """[E6006] Required WA module not found."""
 def __init__(self, module_name: str = None, **kw):
  msg = f"Required module '{module_name}' not found." if module_name else None
  super().__init__(**_from_code(ErrorCode.BRIDGE_MODULE_MISSING, msg, **kw))


# ═══════════════════════════════════════════════════════════
# E7xxx · Validation
# ═══════════════════════════════════════════════════════════

class InvalidInputError(AstraError):
 """[E7001-E7006] Validation failure."""
 def __init__(self, message: str = None, code: ErrorCode = ErrorCode.VAL_MISSING_KEYS, **kw):
  super().__init__(**_from_code(code, message, severity=Severity.WARNING, **kw))

class InvalidJIDError(InvalidInputError):
 """[E7001] Invalid JID format."""
 def __init__(self, jid: str = None, **kw):
  msg = f"Malformed JID: {jid}" if jid else None
  super().__init__(msg, code=ErrorCode.VAL_INVALID_JID, **kw)

class InvalidPhoneError(InvalidInputError):
 """[E7004] Invalid phone number format."""
 def __init__(self, phone: str = None, **kw):
  msg = f"Invalid phone number: {phone}" if phone else None
  super().__init__(msg, code=ErrorCode.VAL_INVALID_PHONE, **kw)


# ═══════════════════════════════════════════════════════════
# E8xxx · WhatsApp-Side
# ═══════════════════════════════════════════════════════════

class RateLimitedError(AstraError):
 """[E8001] Rate limited by WhatsApp."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.WA_RATE_LIMITED, message, severity=Severity.WARNING, **kw))

class EcosystemBlockError(AstraError):
 """[E8002] Message blocked for ecosystem protection."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.WA_ECOSYSTEM_BLOCK, message, severity=Severity.FATAL, **kw))

class AccountBannedError(AstraError):
 """[E8003] Account banned."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.WA_ACCOUNT_BANNED, message, severity=Severity.FATAL, **kw))

class WAServerError(AstraError):
 """[E8004] WhatsApp servers are down."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.WA_SERVER_DOWN, message, **kw))

class VersionMismatchError(AstraError):
 """[E8005] WhatsApp Web version mismatch."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.WA_VERSION_MISMATCH, message, **kw))

class MultiDeviceLimitError(AstraError):
 """[E8006] Maximum linked devices reached."""
 def __init__(self, message: str = None, **kw):
  super().__init__(**_from_code(ErrorCode.WA_MULTIDEVICE_LIMIT, message, **kw))


# --- Compatibility aliases ---
InvalidStateError = InvalidInputError
FeatureNotSupportedError = ModuleMissingError
