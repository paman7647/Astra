# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Backward compatibility: astra.models → astra.types
"""

from ..types import *
from ..types import JID, User, Chat, Message, SessionState, ClientStatus, MessageType, MessageAck

__all__ = [
 "JID",
 "User",
 "Chat",
 "Message",
 "SessionState",
 "ClientStatus",
 "MessageType",
 "MessageAck",
]
