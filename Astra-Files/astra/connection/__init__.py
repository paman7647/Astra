# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Backward compatibility: astra.connection → astra.network
"""

from ..network import BrowserController

__all__ = ["BrowserController"]
