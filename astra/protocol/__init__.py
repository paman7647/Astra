# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Astra Protocol: Handles the low-level communication with the browser's JavaScript engine.
"""

from .gateway import ProtocolBridge
from .actions import EngineAPI

__all__ = ["ProtocolBridge", "EngineAPI"]
