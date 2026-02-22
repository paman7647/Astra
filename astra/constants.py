# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module contains global configuration constants for Astra.
These values define the framework's behavior, timeouts, and selectors.
"""

import os

# --- Framework Metadata ---
VERSION = "0.0.2b10"
DEFAULT_USER_AGENT = (
 "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
 "Chrome/122.0.0.0 Safari/537.36"
)

# --- Connectivity & URLs ---
WHATSAPP_URL = "https://web.whatsapp.com"
SESSION_STORAGE_PATH = os.path.join(os.getcwd(), ".astra_sessions")
LOCAL_CACHE_DB = "astra_cache.db"

# --- Engine Configuration ---
BRIDGE_NAMESPACE = "Astra"
JS_ENGINE_TIMEOUT = 30.0 # Seconds to wait for JS execution
PROTOCOL_CALL_TIMEOUT = 15.0 # Seconds to wait for bridge responses

# --- Reconnection Logic ---
MAX_RECONNECT_ATTEMPTS = 10
RECONNECT_DELAY_MAX = 60.0 # Maximum backoff delay in seconds
RETRY_BACKOFF_MULTIPLIER = 2.0
RECONNECT_JITTER_MAX = 5.0 # Max random jitter added to backoff

# --- Sync Engine Configuration ---
SYNC_HEARTBEAT_INTERVAL = 30.0 # Seconds between bridge health checks
SYNC_STALL_THRESHOLD = 3600.0 # Seconds of silence before declaring stall
SYNC_POLL_INTERVAL = 15.0  # Seconds between fallback data polls

# --- WhatsApp Web DOM Selectors ---
# These are internal selectors used to detect page state or UI elements.
SELECTORS = {
 "qr_canvas": "canvas[aria-label='Scan me!']",
 "side_pane": "#pane-side",
 "chat_header": "header[data-testid='conversation-header']",
 "loading_screen": "[data-testid='startup-loading-screen']"
}
