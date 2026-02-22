# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Authentication manager for Astra.

Handles QR code generation, state detection, and phone number
pairing flows during the login sequence.
"""


import asyncio
import logging
import io
import qrcode
from typing import Optional

from ..connection import BrowserController
from ..errors import LoginFailedError, AuthRateLimitError
from .phonepairing import JS_SCRIPTS, format_pairing_code

logger = logging.getLogger("Astra.Auth")

class Authenticator:
    """
    Manages the WhatsApp Web login process.

    Handles state detection and UI interaction to establish a session
    via QR code or phone pairing.
    """

    def __init__(self, controller: BrowserController, phone: str = None, use_pairing: bool = False):
        """
        Initialize the Authenticator.

        Args:
            controller: The browser controller instance.
            phone: Optional phone number for pairing mode.
            use_pairing: Whether to force pairing mode even if phone is not provided.
        """
        # (Authenticator internal state initialization)
        self._controller = controller
        self._phone = phone
        self._use_pairing = use_pairing
        self._last_qr = None

    async def login(self, timeout: float = 120.0):
        """
        Executes the authentication loop until connected or timeout.

        Args:
            timeout: Maximum time in seconds to wait for authentication.

        Returns:
            bool: True if authentication was successful.

        Raises:
            LoginFailedError: If authentication times out or fails.
            AuthRateLimitError: If WhatsApp blocks pairing attempts.
        """
        logger.info(f"Starting authentication for {self._phone or 'QR scan'}...")
        
        start_time = asyncio.get_event_loop().time()
        pairing_attempts = 0
        max_pairing_attempts = 3
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            state = await self._detect_state()
            
            if state == "CONNECTED":
                logger.info("✅ Authentication successful. Session established.")
                return True
            
            if state == "LOGIN_QR":
                # If we have a phone number, we prefer pairing over QR
                if (self._phone or self._use_pairing) and pairing_attempts < max_pairing_attempts:
                    if pairing_attempts == 0:
                        logger.info("📱 Phone number detected. Switching to high-fidelity pairing mode...")
                    else:
                        logger.warning(f"🔄 Pairing trigger retry ({pairing_attempts}/{max_pairing_attempts})...")
                    
                    await self._trigger_pairing()
                    pairing_attempts += 1
                    # Give it some extra time to transition state after trigger
                    await asyncio.sleep(5.0)
                else:
                    qr_data = await self._get_qr_data()
                    if qr_data and qr_data != self._last_qr:
                        self._last_qr = qr_data
                        logger.info("🆕 QR code updated. Scan with WhatsApp Mobile App.")
                        self._display_qr(qr_data)
            
            elif state == "LOGIN_PHONE":
                if self._phone:
                    logger.info(f"💾 Injecting phone number: {self._phone}")
                    await self._inject_phone(self._phone)
                else:
                    if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
                        logger.info("⌨️ Waiting for phone number input in UI...")
            
            elif state == "LOGIN_CODE":
                code = await self._get_pairing_code()
                if code:
                    self._display_code(code)
            
            elif state == "LOADING":
                if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
                    logger.info("⏳ WhatsApp Web is loading...")
            
            elif state in ["RECONNECTING", "NET_ERROR"]:
                 if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
                    logger.warning(f"🌐 Network instability detected: {state}. Astra will retry shortly...")

            elif state == "ALERT_VISIBLE":
                logger.warning("Dismissing blocking alert...")
                await self._controller.page.keyboard.press("Escape")
            
            elif state == "RATE_LIMITED":
                raise AuthRateLimitError(
                    "WhatsApp has temporarily blocked pairing attempts due to too many tries.",
                    hint="Wait for 8-24 hours before trying again or use a different phone number."
                )

            elif state == "UNKNOWN" or state is None:
                 if int(asyncio.get_event_loop().time() - start_time) % 20 == 0:
                    logger.debug("Still waiting for login UI to stabilize...")
            
            await asyncio.sleep(2.0)

        raise LoginFailedError(
            f"Authentication timed out after {timeout}s.",
            hint="Ensure your phone is linked and the internet connection is stable."
        )

    # --- Low-Level UI Interactions using JS_SCRIPTS ---

    async def _detect_state(self) -> str:
        """Detects the current UI state using the bridge JS engine."""
        page = self._controller.page
        return await page.evaluate(JS_SCRIPTS["DETECT_STATE"])

    async def _trigger_pairing(self):
        """Clicks the 'Link with phone number' button using modular JS script."""
        await self._controller.page.evaluate(JS_SCRIPTS["TRIGGER_PAIRING"])

    async def _inject_phone(self, phone: str):
        """
        Injects the phone number using the robust JS strategy.
        Now handles country code selection (+91) and formatting internally.
        """
        page = self._controller.page
        logger.info(f"Injecting {phone} via robust JS engine...")
        
        # We invoke the async JS function directly
        # The script is a function definition, so we wrap it in () and call it
        try:
             # Pass phone number to the JS function
             await page.evaluate(f"({JS_SCRIPTS['INJECT_PHONE']})('{phone}')")
        except Exception as e:
             logger.error(f"Failed to inject phone via JS: {e}")
             raise

    async def _get_pairing_code(self) -> Optional[str]:
        """Extracts the 8-character pairing code using modular JS script."""
        return await self._controller.page.evaluate(JS_SCRIPTS["EXTRACT_CODE"])

    async def _get_qr_data(self) -> Optional[str]:
        """Extracts the QR data string, with Cross-Browser Compatibility."""
        return await self._controller.page.evaluate("""
            () => {
                const qrEl = document.querySelector('canvas[data-ref]') || 
                             document.querySelector('[data-testid="qrcode"][data-ref]') ||
                             document.querySelector('svg[data-ref]') ||
                             document.querySelector('[data-ref]');
                
                if (qrEl) return qrEl.getAttribute('data-ref');
                return null;
            }
        """)

    def _display_qr(self, data: str):
        """Displays the QR code in the terminal."""
        qr = qrcode.QRCode(box_size=1, border=2)
        qr.add_data(data)
        output = io.StringIO()
        qr.print_ascii(out=output, invert=True)
        print(f"\n--- SCAN THIS QR CODE ---\n{output.getvalue()}\n")

    def _display_code(self, code: str):
        """Displays the pairing code prominently."""
        formatted = format_pairing_code(code)
        print(f"\n{'='*30}\nPAIRING CODE: {formatted}\n{'='*30}\n")
