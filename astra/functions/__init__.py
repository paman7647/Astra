# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Astra Functions: Raw JavaScript bridge scripts for WhatsApp Web internals.
These are injected into the browser to interact with WhatsApp's webpack modules.
"""

from .base import CORE_SCRIPT
from .chat import CHAT_CODE
from .contact import CONTACT_CODE
from .group import GROUP_CODE
from .media import MEDIA_CODE
from .account import ACCOUNT_CODE
from .diagnostic import DIAGNOSTIC_CODE
from .status import STATUS_CODE
from .privacy import PRIVACY_CODE
from .dom import DOM_SCANNER_CODE
from .firefox_dom import FIREFOX_DOM_CODE
from .idb_cache import IDB_CACHE_CODE
from .download import DOWNLOAD_CODE
from .profile_bridge import PROFILE_CODE

__all__ = [
    "CORE_SCRIPT", "CHAT_CODE", "CONTACT_CODE", "GROUP_CODE",
    "MEDIA_CODE", "ACCOUNT_CODE", "DIAGNOSTIC_CODE", "STATUS_CODE",
    "PRIVACY_CODE", "DOM_SCANNER_CODE", "FIREFOX_DOM_CODE",
    "IDB_CACHE_CODE", "DOWNLOAD_CODE", "PROFILE_CODE"
]
