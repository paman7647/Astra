# Astra Error Codes Reference

Every error in Astra carries a structured code, a human-readable message, and a recovery hint. Catch specific exceptions to handle failures gracefully.

## Quick Example

```python
from astra.errors import MessageSendError, RateLimitedError

try:
 await client.chat.send_message(jid, text)
except RateLimitedError as e:
 print(f"{e.code}: {e.hint}") # E8001: You are sending too many requests...
 if e.retryable:
  await asyncio.sleep(60)
except MessageSendError as e:
 print(e) # [E3001] Failed to send message to ...
```

---

## E1xxx — Authentication

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E1001 | `LoginFailedError` | Authentication failed | ✅ |
| E1002 | `QRTimeoutError` | QR code scan timed out | ✅ |
| E1003 | `PairingError` | Phone pairing failed | ✅ |
| E1004 | `SessionExpiredError` | Session has expired | ✅ |
| E1005 | `AuthRateLimitError` | Too many login attempts | ❌ |
| E1006 | `PhoneDisconnectedError` | Primary phone lost connection | ✅ |

## E2xxx — Connection & Browser

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E2001 | `BrowserStartError` | Failed to launch browser | ❌ |
| E2002 | `BrowserCrashError` | Browser process crashed | ✅ |
| E2003 | `BrowserLimitError` | Another instance using this session | ❌ |
| E2004 | `PageUnresponsiveError` | Browser page frozen | ✅ |
| E2005 | `ConnectionLostError` | Lost connection to browser | ✅ |
| E2006 | `WebSocketDisconnectError` | WS connection to WA dropped | ✅ |
| E2007 | `NavigationError` | Failed to navigate to WA Web | ✅ |
| E2008 | `StartupError` | Client startup failed | ✅ |

## E3xxx — Messaging & Chat

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E3001 | `MessageSendError` | Message failed to send | ✅ |
| E3002 | `MessageTimeoutError` | Message send timed out | ✅ |
| E3003 | `InvalidRecipientError` | Invalid recipient JID | ❌ |
| E3004 | `MediaUploadError` | Media upload failed | ✅ |
| E3005 | `MediaDownloadError` | Media download failed | ✅ |
| E3006 | `MessageEditError` | Failed to edit message | ❌ |
| E3007 | `MessageDeleteError` | Failed to delete message | ❌ |
| E3008 | `ReactionError` | Failed to react | ❌ |
| E3010 | `PollError` | Failed to create poll | ❌ |
| E3011 | `PollVoteError` | Failed to vote on poll | ❌ |
| E3012 | — | Failed to forward message | ❌ |
| E3020 | `ChatNotFoundError` | Chat not found | ❌ |
| E3021 | `ChatOperationError` | Archive/unarchive failed | ❌ |
| E3022 | `ChatOperationError` | Mute/unmute failed | ❌ |
| E3023 | `ChatOperationError` | Pin/unpin failed | ❌ |
| E3024 | — | Mark as seen failed | ❌ |
| E3025 | `SyncError` | Chat history sync failed | ✅ |

## E4xxx — Groups

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E4001 | `GroupCreateError` | Failed to create group | ❌ |
| E4002 | `GroupMemberError` | Failed to add member(s) | ❌ |
| E4003 | `GroupMemberError` | Failed to remove member(s) | ❌ |
| E4004 | — | Failed to promote to admin | ❌ |
| E4005 | — | Failed to demote admin | ❌ |
| E4006 | `GroupJoinError` | Failed to join via invite | ❌ |
| E4007 | `GroupInfoError` | Failed to get group info | ❌ |
| E4008 | — | Failed to leave group | ✅ |
| E4010 | `GroupSettingsError` | Failed to update settings | ❌ |
| E4020 | `GroupPermissionError` | Permission denied | ❌ |

## E5xxx — Account & Profile

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E5001 | `ProfileReadError` | Failed to read profile | ✅ |
| E5002 | `ProfileUpdateError` | Failed to update profile | ❌ |
| E5010 | `StatusPostError` | Failed to post status | ✅ |
| E5011 | — | Failed to post media status | ✅ |
| E5020 | `PrivacyError` | Failed to update privacy | ✅ |
| E5030 | `BlockError` | Failed to block/unblock | ❌ |
| E5040 | — | Failed to get/set profile pic | ❌ |
| E5050 | — | Logout failed | ❌ |

## E6xxx — Bridge & Engine

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E6001 | `BridgeMethodNotFoundError` | JS method not found | ❌ |
| E6002 | `BridgeCallError` | Bridge call failed | ✅ |
| E6003 | — | JS evaluation failed | ✅ |
| E6004 | — | Bridge not connected | ✅ |
| E6005 | `EngineStallError` | Engine stall detected | ✅ |
| E6006 | `ModuleMissingError` | Required WA module missing | ❌ |
| E6007 | — | Script injection failed | ✅ |
| E6008 | — | WA Store unavailable | ✅ |

## E7xxx — Validation

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E7001 | `InvalidJIDError` | Invalid JID format | ❌ |
| E7002 | — | Empty text content | ❌ |
| E7003 | `InvalidInputError` | Missing required params | ❌ |
| E7004 | `InvalidPhoneError` | Invalid phone number | ❌ |
| E7005 | — | Invalid media input | ❌ |
| E7006 | — | Payload too large | ❌ |

## E8xxx — WhatsApp-Side

| Code | Exception | Description | Retryable |
|------|-----------|-------------|-----------|
| E8001 | `RateLimitedError` | Rate limited by WA | ✅ |
| E8002 | `EcosystemBlockError` | Blocked for ecosystem protection | ❌ |
| E8003 | `AccountBannedError` | Account banned | ❌ |
| E8004 | `WAServerError` | WA servers down | ✅ |
| E8005 | `VersionMismatchError` | WA Web version mismatch | ✅ |
| E8006 | `MultiDeviceLimitError` | Max linked devices reached | ❌ |
| E8007 | — | Encryption error | ✅ |
| E8008 | — | Contact not on WhatsApp | ❌ |

---

## Error Inheritance

```
Exception
└── AstraError (base — has .code, .hint, .retryable, .severity, .to_dict())
 ├── LoginFailedError (E1001)
 ├── QRTimeoutError (E1002)
 ├── PairingError (E1003)
 ├── ...
 ├── MessageSendError (E3001)
 ├── PollError (E3010)
 ├── GroupCreateError (E4001)
 ├── BridgeCallError (E6002)
 ├── InvalidInputError (E7xxx)
 │ ├── InvalidJIDError (E7001)
 │ └── InvalidPhoneError (E7004)
 ├── RateLimitedError (E8001)
 └── AccountBannedError (E8003)
```
