# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module contains standard enumerations used throughout Astra.
Enums help maintain consistency in state management and message types.
"""

from enum import Enum, auto

class SessionState(Enum):
 """
 Represents the health and connectivity state of a WhatsApp session.
 """
 UNINITIALIZED = "UNINITIALIZED"
 AUTHENTICATING = "AUTHENTICATING"
 CONNECTED = "CONNECTED"
 DISCONNECTED = "DISCONNECTED"
 RECONNECTING = "RECONNECTING"
 EXPIRED = "EXPIRED"
 LOGGED_OUT = "LOGGED_OUT"

class ClientStatus(Enum):
 """
 Represents the high-level operational status of the Astra Client.
 """
 IDLE = auto()
 STARTING = auto()
 AUTHENTICATING = auto()
 READY = auto()
 SHUTTING_DOWN = auto()
 STOPPED = auto()
 CRASHED = auto()
 FAILED = auto()
 OFFLINE = auto()

class MessageType(Enum):
 """
 Core WhatsApp message types supported by the bridge.
 """
 TEXT = "chat"
 IMAGE = "image"
 VIDEO = "video"
 AUDIO = "audio"
 VOICE_NOTE = "ptt"
 DOCUMENT = "document"
 STICKER = "sticker"
 LOCATION = "location"
 CONTACT = "vcard"
 REVOKED = "revoked"
 POLL = "poll_creation"
 REACTION = "reaction"
 TEMPLATE = "notification_template"
 UNKNOWN = "unknown"

 @classmethod
 def _missing_(cls, value):
  return cls.UNKNOWN

class MessageAck(Enum):
 """
 Message acknowledgement levels (tick markers).
 Values match WhatsApp Web internal constants.
 """
 ERROR = -1
 PENDING = 0
 SENT = 1
 DELIVERED = 2
 READ = 3
 PLAYED = 4
 UNKNOWN = 5

 @classmethod
 def _missing_(cls, value):
  return cls.UNKNOWN
