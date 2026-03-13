# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module monitors the WhatsApp Web page for state transitions.
It handles QR code discovery and authentication tracking.
"""

import asyncio
import logging
from typing import Optional, Callable
from playwright.async_api import Page

from ..constants import SELECTORS
from ..errors import LoginFailedError

logger = logging.getLogger("Browser")

class PageMonitor:
 """
 Monitors the browser page to detect authentication status and QR codes.
 """

 def __init__(self, page: Page):
  self._page = page
  self._on_qr_received: Optional[Callable[[str], None]] = None

 def on_qr(self, callback: Callable[[str], None]):
  """Registers a callback for when a new QR code is displayed."""
  self._on_qr_received = callback

 async def wait_until_ready(self, timeout: float = 60.0):
  """
  Polls the page until the user is authenticated or the timeout expires.

  Args:
   timeout: Maximum time to wait in seconds.

  Raises:
   LoginFailedError: If the user fails to authenticate in time.
  """
  logger.info("Monitoring page for authentication...")

  deadline = asyncio.get_event_loop().time() + timeout

  while asyncio.get_event_loop().time() < deadline:
   # 1. Success case: Chat list is visible
   if await self._page.query_selector(SELECTORS["side_pane"]):
    logger.info("Authentication successful. Welcome to Astra!")
    return

   # 2. QR Discovery
   qr_element = await self._page.query_selector(SELECTORS["qr_canvas"])
   if qr_element and self._on_qr_received:
    # The 'data-ref' attribute contains the raw QR string
    qr_data = await qr_element.get_attribute("data-ref")
    if qr_data:
     self._on_qr_received(qr_data)

   # Smart polling interval
   await asyncio.sleep(2.0)

  raise LoginFailedError(
   f"Authentication timed out after {timeout}s.",
   hint="Ensure your phone is linked and has a stable internet connection."
  )
