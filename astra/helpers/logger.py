# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import logging
import sys
import time
import os

# Startup timestamp for elapsed-time display
_START_TIME = time.time()

# Debug mode from environment
DEBUG = os.getenv("ASTRA_DEBUG", "").lower() in ("1", "true", "yes")

# ── ANSI escape codes ───────────────────────────────────────
RST  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"

# Level → (color, short tag)
_LEVEL_STYLE = {
    logging.DEBUG:    ("\033[90m",  "DBG"),
    logging.INFO:     ("\033[36m",  "INF"),
    logging.WARNING:  ("\033[33m",  "WRN"),
    logging.ERROR:    ("\033[31m",  "ERR"),
    logging.CRITICAL: ("\033[91m",  "CRT"),
}

# Category → color
_CAT_COLORS = {
    "Auth":    "\033[94m",
    "Sync":    "\033[92m",
    "Client":  "\033[96m",
    "Bridge":  "\033[95m",
    "Engine":  "\033[34m",
    "Browser": "\033[90m",
    "Storage": "\033[33m",
    "Group":   "\033[32m",
    "Chat":    "\033[36m",
    "Status":  "\033[90m",
    "Events":  "\033[35m",
    "Media":   "\033[33m",
    "Privacy": "\033[94m",
    "Account": "\033[92m",
    "Health":  "\033[91m",
}


class AstraFormatter(logging.Formatter):
    """
    Compact, professional log formatter.

    Normal:  [+1.2s] INF  Client   Connecting to WhatsApp...
    Error:   [+3.4s] ERR  Bridge   Connection lost (set ASTRA_DEBUG=1 for trace)
    Debug:   Full stack traces and verbose output when ASTRA_DEBUG=1
    """

    def format(self, record):
        elapsed = time.time() - _START_TIME

        # Elapsed timestamp
        if elapsed < 100:
            ts = f"[+{elapsed:5.1f}s]"
        elif elapsed < 3600:
            m, s = divmod(int(elapsed), 60)
            ts = f"[+{m}m{s:02d}s]"
        else:
            h, rem = divmod(int(elapsed), 3600)
            m = rem // 60
            ts = f"[+{h}h{m:02d}m]"

        # Level tag
        color, tag = _LEVEL_STYLE.get(record.levelno, (RST, "???"))

        # Category
        cat = record.name[:8]
        cat_c = _CAT_COLORS.get(record.name, RST)

        # Message
        msg = record.getMessage()

        # In production mode, truncate noisy errors
        if not DEBUG and record.levelno >= logging.ERROR and len(msg) > 200:
            msg = msg[:180] + "..."

        # Exception info
        exc = ""
        if record.exc_info and record.exc_info[1]:
            if DEBUG:
                import traceback
                exc = "\n" + "".join(traceback.format_exception(*record.exc_info))
            else:
                exc = f"\n  {DIM}> {record.exc_info[1]}{RST}"

        return (
            f"{DIM}{ts}{RST} "
            f"{color}{tag}{RST}  "
            f"{cat_c}{cat:<8}{RST} "
            f"{msg}{exc}"
        )


def setup_logging(level=logging.INFO):
    """Initializes the Astra logging system."""
    global _START_TIME, DEBUG
    _START_TIME = time.time()
    DEBUG = os.getenv("ASTRA_DEBUG", "").lower() in ("1", "true", "yes")

    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(AstraFormatter())

    root.setLevel(logging.DEBUG if DEBUG else level)
    root.addHandler(handler)

    # Silence third-party noise
    for name in ("playwright", "pyee", "asyncio", "urllib3", "websockets"):
        logging.getLogger(name).setLevel(logging.WARNING)

    if not DEBUG:
        logging.getLogger("Bridge").setLevel(logging.INFO)
        logging.getLogger("Engine").setLevel(logging.INFO)
