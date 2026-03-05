# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Backward compatibility: astra.protocol → astra.network
"""

from ..network import ProtocolBridge, EngineAPI, DataTransformer

__all__ = ["ProtocolBridge", "EngineAPI", "DataTransformer"]
