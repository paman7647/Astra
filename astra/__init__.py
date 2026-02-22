# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Astra: A WhatsApp userbot framework.
"""

from .client.client import Client
from .events.filters import Filters
from .models import User, Chat, Message, ClientStatus
from .errors import AstraError

__version__ = "0.0.2b25"
__all__ = ["Client", "Filters", "User", "Chat", "Message", "AstraError", "ClientStatus"]
