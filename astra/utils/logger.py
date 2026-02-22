# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import logging
import sys
import time

# --- Color Constants (ANSI) ---
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"

# Level Colors
LEVEL_MAP = {
    logging.DEBUG: "\033[90m",    # Gray
    logging.INFO: "\033[36m",     # Cyan
    logging.WARNING: "\033[33m",  # Yellow
    logging.ERROR: "\033[31m",    # Red
    logging.CRITICAL: "\033[41m", # Background Red
}

# Category Colors
CAT_MAP = {
    "Auth": "\033[94m",     # Light Blue
    "Sync": "\033[92m",     # Light Green
    "Client": "\033[96m",   # Cyan
    "Bridge": "\033[95m",   # Magenta
    "Engine": "\033[34m",   # Dark Blue
    "Browser": "\033[90m",  # Gray
    "Storage": "\033[33m",  # Gold
    "Group": "\033[32m",    # Green
    "Chat": "\033[36m",     # Cyan
    "Status": "\033[90m",   # Dim
}

class AstraFormatter(logging.Formatter):
    """
    A premium, clean formatter for the Astra Framework.
    Focused on alignment, legibility, and refined color usage.
    """
    
    def format(self, record):
        # 1. Timestamp [HH:MM:SS] (Dimmed)
        ts = self.formatTime(record, "%H:%M:%S")
        ts_str = f"{C_DIM}[{ts}]{C_RESET}"

        # 2. Category [NAME] (Colorized & Padded)
        cat_name = record.name[:7].upper()
        cat_color = CAT_MAP.get(record.name, C_RESET)
        cat_str = f"{cat_color}{cat_name:<8}{C_RESET}"

        # 3. Level indicator (Only if high priority)
        level_str = ""
        if record.levelno > logging.INFO:
            lvl_color = LEVEL_MAP.get(record.levelno, "")
            level_str = f"{lvl_color} {record.levelname[:3]} {C_RESET} "
        else:
            level_str = "     "

        # 4. Message
        msg = record.getMessage()
        
        # Clean separator
        sep = f"{C_DIM}»{C_RESET}" if record.levelno <= logging.INFO else f"{C_DIM}:{C_RESET}"

        return f"{ts_str} {cat_str} {sep} {level_str}{msg}"

def setup_logging(level=logging.INFO):
    """
    Apply the premium Astra logging style to the root logger.
    """
    root = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    if root.handlers:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(AstraFormatter())
    
    root.setLevel(level)
    root.addHandler(handler)

    # Clean dependent noise
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("pyee").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
