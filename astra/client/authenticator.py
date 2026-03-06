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

logger = logging.getLogger("Auth")

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
        self._last_code = None
        self._phone_injected = False
        self._last_pairing_attempt = 0.0

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
        logger.info(f"Logging in with {self._phone or 'QR scan'}...")
        
        start_time = asyncio.get_event_loop().time()
        
        # --- DB Recovery Logic ---
        # If the browser is in a fresh state, try to restore from SQLite backup
        try:
             initial_state = await self._detect_state()
             if initial_state in ["LOGIN_QR", "LOGIN_PHONE", "UNKNOWN"]:
                  logger.info("Checking for saved session...")
                  # We use the store linked to the parent client if available
                  # BrowserController doesn't have direct access, but Authenticator is owned by Client
                  # We assume the caller (Client) has initialized self.store
                  db_state = getattr(self._controller, "_db_recovery_state", None)
                  
                  # If we haven't checked the DB yet, do it now
                  if hasattr(self._controller, "get_db_state_callback"):
                       db_state = self._controller.get_db_state_callback()
                       
                  if db_state:
                       logger.info("Restoring session...")
                       await self.import_session(db_state)
                       # Wait for bridge to settle after navigation
                       await asyncio.sleep(3.0)
        except Exception as e:
             logger.debug(f"DB Recovery attempt failed or skipped: {e}")
        # -------------------------
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            state = await self._detect_state()
            
            if state == "CONNECTED":
                logger.info("Authentication successful. Session established.")
                return True
            
            if state == "LOGIN_QR":
                # Only trigger pairing if explicitly requested
                if self._use_pairing:
                    now = asyncio.get_event_loop().time()
                    # Retry every 60 seconds if still on QR screen
                    # This gives the user enough time to input the code on their phone
                    if not hasattr(self, "_last_pairing_attempt") or (now - self._last_pairing_attempt) > 60.0:
                        attempt = getattr(self, "_pairing_attempts", 0) + 1
                        self._pairing_attempts = attempt
                        self._last_pairing_attempt = now
                        
                        logger.info(f"Pairing attempt {attempt}...")
                        await self._trigger_pairing()
                        # Give it extra time to transition in slow envs
                        await asyncio.sleep(5.0)
                else:
                    qr_data = await self._get_qr_data()
                    if qr_data and qr_data != self._last_qr:
                        self._last_qr = qr_data
                        logger.info("Scan the QR code with WhatsApp.")
                        self._display_qr(qr_data)
            
            elif state == "LOGIN_PHONE":
                if self._phone:
                    if not self._phone_injected:
                        logger.info(f"Injecting phone number: {self._phone}")
                        await self._inject_phone(self._phone)
                        self._phone_injected = True
                else:
                    if int(asyncio.get_event_loop().time() - start_time) % 30 == 0:
                        logger.info("Waiting for phone number input in UI...")
            
            elif state == "LOGIN_CODE":
                code = await self._get_pairing_code()
                if code and code != self._last_code:
                    self._last_code = code
                    self._display_code(code)
            
            elif state == "LOADING":
                if int(asyncio.get_event_loop().time() - start_time) % 60 == 0:
                    logger.debug("Loading...")
            
            elif state in ["RECONNECTING", "NET_ERROR"]:
                 if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
                    logger.warning(f"Network instability detected: {state}. Astra will retry shortly...")

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
        logger.debug(f"Sending phone number: {phone}...")
        
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

    async def export_session(self) -> dict:
        """
        Exports the current session state (cookies + localStorage).
        """
        page = self._controller.page
        cookies = await self._controller.context.cookies()
        
        # Navigate to WA origin to get localStorage if not already there
        # but persistent context usually handles this.
        storage = await page.evaluate("""
            () => {
                let json = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    json[key] = localStorage.getItem(key);
                }
                return json;
            }
        """)
        
        return {
            "cookies": cookies,
            "localStorage": storage
        }

    async def import_session(self, state: dict):
        """
        Imports a previously exported session state.
        """
        if not state: return
        
        # 1. Set cookies on the context (affects future requests)
        if "cookies" in state:
            try:
                await self._controller.context.add_cookies(state["cookies"])
            except Exception as e:
                logger.debug(f"Failed to add cookies: {e}")
            
        # 2. LocalStorage injection
        if "localStorage" in state:
            storage_data = state["localStorage"]
            
            # If the page is already at the target origin, inject immediately
            if self._controller.page and "whatsapp.com" in self._controller.page.url:
                logger.debug("Page active, injecting localStorage immediately...")
                await self._controller.inject_local_storage(storage_data)
                # Note: We don't force a reload here, as it might interrupt an active flow.
                # The next state detection cycle will catch the update.
            else:
                # Otherwise queue it for the next navigation (via start() or goto())
                self._controller._pending_storage = [{
                    "origin": "https://web.whatsapp.com",
                    "localStorage": storage_data
                }]
