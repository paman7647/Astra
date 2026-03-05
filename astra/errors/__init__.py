# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Astra Errors: Structured, coded exceptions for every failure path.

Usage::

 from astra.errors import MessageSendError, ErrorCode

 try:
  await client.chat.send_message(jid, text)
 except MessageSendError as e:
  print(e.code)  # "E3001"
  print(e.hint)  # "Ensure the recipient JID is correct..."
  print(e.retryable) # True
"""

from .base import AstraError, Severity
from .codes import ErrorCode
from .exceptions import (
 # E1xxx · Auth
 LoginFailedError,
 QRTimeoutError,
 PairingError,
 SessionExpiredError,
 AuthRateLimitError,
 PhoneDisconnectedError,
 # E2xxx · Connection
 BrowserStartError,
 BrowserCrashError,
 BrowserLimitError,
 PageUnresponsiveError,
 ConnectionLostError,
 WebSocketDisconnectError,
 NavigationError,
 StartupError,
 # E3xxx · Messaging
 MessageSendError,
 MessageTimeoutError,
 InvalidRecipientError,
 MediaUploadError,
 MediaDownloadError,
 MessageEditError,
 MessageDeleteError,
 ReactionError,
 PollError,
 PollVoteError,
 ChatNotFoundError,
 ChatOperationError,
 SyncError,
 # E4xxx · Groups
 GroupCreateError,
 GroupMemberError,
 GroupPermissionError,
 GroupJoinError,
 GroupInfoError,
 GroupSettingsError,
 MembershipRequestError,
 CallRejectError,
 MessageForwardError,
 MessagePinError,
 ChatClearError,
 # E5xxx · Account
 ProfileReadError,
 ProfileUpdateError,
 StatusPostError,
 PrivacyError,
 BlockError,
 # E6xxx · Bridge
 BridgeCallError,
 BridgeMethodNotFoundError,
 EngineStallError,
 ModuleMissingError,
 # E7xxx · Validation
 InvalidInputError,
 InvalidJIDError,
 InvalidPhoneError,
 # E8xxx · WhatsApp-Side
 RateLimitedError,
 EcosystemBlockError,
 AccountBannedError,
 WAServerError,
 VersionMismatchError,
 MultiDeviceLimitError,
 # Compat aliases
 InvalidStateError,
 FeatureNotSupportedError,
)

__all__ = [
 # Base
 "AstraError", "Severity", "ErrorCode",
 # E1xxx
 "LoginFailedError", "QRTimeoutError", "PairingError",
 "SessionExpiredError", "AuthRateLimitError", "PhoneDisconnectedError",
 # E2xxx
 "BrowserStartError", "BrowserCrashError", "BrowserLimitError",
 "PageUnresponsiveError", "ConnectionLostError", "WebSocketDisconnectError",
 "NavigationError", "StartupError",
 # E3xxx
 "MessageSendError", "MessageTimeoutError", "InvalidRecipientError",
 "MediaUploadError", "MediaDownloadError", "MessageEditError",
 "MessageDeleteError", "ReactionError", "PollError", "PollVoteError",
 "ChatNotFoundError", "ChatOperationError", "SyncError",
 # E4xxx
 "GroupCreateError", "GroupMemberError", "GroupPermissionError",
 "GroupJoinError", "GroupInfoError", "GroupSettingsError",
 "MembershipRequestError", "CallRejectError",
 "MessageForwardError", "MessagePinError", "ChatClearError",
 # E5xxx
 "ProfileReadError", "ProfileUpdateError", "StatusPostError",
 "PrivacyError", "BlockError",
 # E6xxx
 "BridgeCallError", "BridgeMethodNotFoundError",
 "EngineStallError", "ModuleMissingError",
 # E7xxx
 "InvalidInputError", "InvalidJIDError", "InvalidPhoneError",
 # E8xxx
 "RateLimitedError", "EcosystemBlockError", "AccountBannedError",
 "WAServerError", "VersionMismatchError", "MultiDeviceLimitError",
 # Compat
 "InvalidStateError", "FeatureNotSupportedError",
]
