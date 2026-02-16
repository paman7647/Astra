# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module handles the authentication flow for Astra, including
QR code generation and phone number pairing.
"""

import asyncio
import logging
import io
from typing import Optional, Callable
from playwright.async_api import Page

try:
 import qrcode
except ImportError:
 qrcode = None

from ..connection import BrowserController
from ..errors import (
 LoginFailedError, QRTimeoutError, PairingError,
 AuthRateLimitError, PhoneDisconnectedError,
)

logger = logging.getLogger("Astra.Auth")

class Authenticator:
 """
 Expert-grade authentication manager.

 Orchestrates the login process by monitoring the browser state
 and interacting with the WhatsApp Web UI.
 """

 def __init__(self, controller: BrowserController, phone: str = None, use_pairing: bool = False):
  self._controller = controller
  self._phone = phone
  self._use_pairing = use_pairing
  self._last_qr = None

 async def login(self, timeout: float = 120.0):
  """
  Executes the authentication loop.

  Monitors the page for QR codes or pairing prompts and
  blocks until the user is authenticated.
  """
  masked = f"****{self._phone[-4:]}" if self._phone and len(self._phone) >= 4 else "QR mode"
  logger.info(f"Authenticating ({masked})...")

  start_time = asyncio.get_event_loop().time()
  pairing_attempted = False

  while (asyncio.get_event_loop().time() - start_time) < timeout:
   state = await self._detect_state()

   if state == "CONNECTED":
    logger.info("Authentication successful. Session established.")
    return True

   if state == "LOGIN_QR":
    # If we have a phone number, we prefer pairing over QR
    if (self._phone or self._use_pairing) and not pairing_attempted:
     logger.info("Pairing mode requested. Switching to pairing UI...")
     await self._trigger_pairing()
     pairing_attempted = True
    else:
     qr_data = await self._get_qr_data()
     if qr_data and qr_data != self._last_qr:
      self._last_qr = qr_data
      logger.info("QR code updated. Scan with WhatsApp Mobile App.")
      self._display_qr(qr_data)

   elif state == "LOGIN_PHONE":
    logger.info(f"Injecting phone number: {self._phone}")
    await self._inject_phone(self._phone)

   elif state == "LOGIN_CODE":
    code = await self._get_pairing_code()
    if code:
     self._display_code(code)

   elif state == "LOADING":
    if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
     logger.info("Loading...")

   elif state in ["RECONNECTING", "NET_ERROR"]:
    if int(asyncio.get_event_loop().time() - start_time) % 10 == 0:
     logger.warning(f"[E1006] Network instability detected: {state}. Astra will retry shortly...")

   elif state == "ALERT_VISIBLE":
    logger.warning("Dismissing blocking alert...")
    await self._controller.page.keyboard.press("Escape")

   elif state == "UNKNOWN":
    if int(asyncio.get_event_loop().time() - start_time) % 20 == 0:
     logger.debug("Still waiting for login UI to stabilize...")

   await asyncio.sleep(2.0)

  # Classify timeout based on what was happening
  if self._phone and pairing_attempted:
   raise PairingError(
    f"Phone pairing timed out after {timeout}s.",
   )
  else:
   raise QRTimeoutError(
    f"QR code scan timed out after {timeout}s.",
   )

 # --- Low-Level UI Interactions ---

 async def _detect_state(self) -> str:
  """Expertly detects the current UI state using CSS selectors and engine state."""
  page = self._controller.page
  return await page.evaluate("""
   () => {
    const check = (s) => document.querySelector(s);

    // 1. High-fidelity engine check (Ported from nnew/whatsapp-web.js)
    if (window.Store && (window.Store.Stream || window.Store.WAWebStreamModel)) {
     const stream = window.Store.WAWebStreamModel
      ? window.Store.WAWebStreamModel.Stream
      : window.Store.Stream;

     const state = stream.state;
     const mode = stream.mode;

     if (state === 'CONNECTED' || mode === 'MAIN' || state === 'SYNCING') return "CONNECTED";
     if (state === 'PAIRING' || (state && mode === 'QR')) return "LOGIN_QR";
    }

    // 1b. Socket-level state check (nnew implementation)
    if (window.Store && window.Store.AppState && window.Store.AppState.state) {
     const sState = window.Store.AppState.state;
     if (sState === 'CONNECTED') return "CONNECTED";
     if (sState === 'PAIRING' || sState === 'UNPAIRED' || sState === 'UNPAIRED_IDLE') return "LOGIN_QR";
     if (sState === 'PROXYBLOCK' || sState === 'TOS_BLOCK' || sState === 'SMB_TOS_BLOCK') return "BLOCKED";
     if (sState === 'TIMEOUT') return "RECONNECTING";
    }

    if (window.Store && window.Store.Conn && window.Store.Conn.isMain) return "CONNECTED";

    const findByText = (text) => {
     return Array.from(document.querySelectorAll('span, div, button, h1'))
        .find(el => el.innerText && el.innerText.includes(text));
    };

    // 2. DOM Fallbacks
    if (check('[data-testid="side"]') || check('#pane-side')) return "CONNECTED";
    if (check('[data-testid="startup-loading-screen"]')) return "LOADING";

    // 3. Network & Connectivity Overlays
    if (findByText('computer has an active internet connection')) return "NET_ERROR";
    if (findByText('Reconnecting')) return "RECONNECTING";

    // 4. QR & Pairing - Firefox/Cross-Browser Compatibility
    if (check('canvas') || check('[data-testid="qrcode"]') || check('[data-ref]')) return "LOGIN_QR";
    if (check('[data-link-code]') || findByText('Enter code on phone')) return "LOGIN_CODE";
    if (check('input[aria-label*="phone number"]') || check('input[type="tel"]') || findByText('Phone number')) return "LOGIN_PHONE";

    if (findByText('Scan the QR code') || findByText('Link with phone number')) return "LOGIN_QR";

    return "UNKNOWN";
   }
  """)

 async def _trigger_pairing(self):
  """Clicks the 'Link with phone number' button with broad Firefox support."""
  await self._controller.page.evaluate("""
   () => {
    const findByText = (text) => {
     return Array.from(document.querySelectorAll('span, div, button, h1'))
        .find(el => el.innerText && el.innerText.includes(text));
    };

    const trigger = document.querySelector('[data-testid="link-device-qrcode-alt-pairing"]') ||
        findByText('Link with phone number');
    if (trigger) trigger.click();
   }
  """)

 async def _inject_phone(self, phone: str):
  """Standardizes and injects the phone number into the input field."""
  page = self._controller.page
  input_sel = 'input[aria-label*="phone number"]'
  await page.wait_for_selector(input_sel)
  await page.fill(input_sel, phone)
  await asyncio.sleep(1)
  await page.keyboard.press("Enter")

 async def _get_pairing_code(self) -> Optional[str]:
  """Extracts the 8-character pairing code from the UI."""
  return await self._controller.page.evaluate("""
   () => {
    const el = document.querySelector('[data-link-code]');
    return el ? el.getAttribute('data-link-code').substring(0, 8) : null;
   }
  """)

 async def _get_qr_data(self) -> Optional[str]:
  """Extracts the QR data string, with Firefox compatibility."""
  return await self._controller.page.evaluate("""
   () => {
    // 1. Try Astra Bridge (High Fidelity)
    if (window.Astra && window.Astra.lastQR) return window.Astra.lastQR;

    // 2. Fallback to DOM - Targeted for Firefox
    const qrEl = document.querySelector('canvas[data-ref]') ||
        document.querySelector('[data-testid="qrcode"][data-ref]') ||
        document.querySelector('svg[data-ref]') ||
        document.querySelector('[data-ref]');

    if (qrEl) return qrEl.getAttribute('data-ref');

    // Last Resort: Search all elements with data-ref
    const allWithRef = Array.from(document.querySelectorAll('*')).find(el => el.getAttribute('data-ref'));
    return allWithRef ? allWithRef.getAttribute('data-ref') : null;
   }
  """)

 def _display_qr(self, data: str):
  """Displays the QR code in the terminal."""
  if qrcode:
   qr = qrcode.QRCode(box_size=1, border=2)
   qr.add_data(data)
   output = io.StringIO()
   qr.print_ascii(out=output, invert=True)
   print(f"\n--- SCAN THIS QR CODE ---\n{output.getvalue()}\n")
  else:
   print(f"\n[Astra] QR Code: {data}\n")

 async def export_session(self) -> dict:
  """
  Exports the current authentication state as a dictionary.
  Includes cookies and localStorage.
  """
  return await self._controller.context.storage_state()

 async def import_session(self, state: dict):
  """
  Restores a previously exported authentication state.

  Args:
   state: The dictionary returned by export_session().
  """
  await self._controller.context.add_cookies(state.get("cookies", []))
  # Local storage needs to be injected via page.evaluate on the correct domain
  self._controller._pending_storage = state.get("origins", [])

 def _display_code(self, code: str):
  """Displays the pairing code prominently."""
  formatted = f"{code[:4]}-{code[4:]}" if len(code) == 8 else code
  print(f"\n{'='*30}\nPAIRING CODE: {formatted}\n{'='*30}\n")
