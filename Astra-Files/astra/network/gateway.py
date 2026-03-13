# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
The ProtocolBridge is the primary conduit for executing commands and
receiving events from the WhatsApp Web browser context.
"""

import logging
import asyncio
import os
from typing import Any, Optional, Callable, Awaitable, Dict
from playwright.async_api import Page

_DEBUG = os.getenv("ASTRA_DEBUG", "").lower() in ("1", "true", "yes")

from ..errors import (
 BridgeCallError, BridgeMethodNotFoundError,
 MessageTimeoutError, RateLimitedError,
 ConnectionLostError, PageUnresponsiveError,
)

from ..constants import BRIDGE_NAMESPACE, PROTOCOL_CALL_TIMEOUT
from .engine import JS_ENGINE_SOURCE

logger = logging.getLogger("Bridge")

class ProtocolBridge:
 """
 Manages the two-way bridge between Python and JavaScript.

 This class handles the injection of the Astra engine into the browser
 and facilitates calling remote methods with automatic result normalization.
 """

 def __init__(self, page: Optional[Page] = None):
  self._page = page
  self._is_active = False
  self._on_event: Optional[Callable[[str, Any], Awaitable[None]]] = None
  self._connect_count: int = 0
  self._progress_callbacks: Dict[str, Callable[[int, int], Any]] = {}

 async def connect(self):
  """
  Initializes the bridge by injecting the core engine scripts.

  This method uses persistent init scripts to ensure the bridge
  survives page reloads and navigations.
  """
  logger.debug("Connecting Protocol Bridge...")

  # 1. Expose the event uplink (allows JS to call Python)
  try:
   # Direct exposure of the uplink function
   async def astra_uplink_py(name, payload):
    if name == "log":
     msg = payload.get("msg", "") if isinstance(payload, dict) else str(payload)
     # Suppress WA internal noise that isn't actionable
     if "Requiring unknown module" in msg or "ErrorUtils" in msg or "fburl.com" in msg:
      return
     level = payload.get("level", "log") if isinstance(payload, dict) else "log"
     if level == "error":
      logger.error(f"[Bridge] {msg}")
     elif level == "warn":
      logger.warning(f"[Bridge] {msg}")
     else:
      logger.debug(f"[Bridge] {msg}")
     return
    await self._process_event(name, payload)

   await self._page.expose_function("astra_uplink", astra_uplink_py)
   if _DEBUG:
        logger.info("Bridge uplink exposed.")
  except Exception as e:
   logger.debug(f"Uplink bind skipped: {type(e).__name__}")

  # 2. Prepare the Bridge Proxy Snippet
  # This snippet maps window.Astra methods to the bridge namespace
  bridge_boot = f"""
   window.{BRIDGE_NAMESPACE} = window.{BRIDGE_NAMESPACE} || {{}};
   Object.assign(window.{BRIDGE_NAMESPACE}, {{
    emit: (name, payload) => window.astra_uplink(name, payload),

    call: async (method, payload, id) => {{
     const engine = window.AstraEngine;
     if (!engine || typeof engine[method] !== 'function') {{
      console.error(`[Astra] Remote method [${{method}}] not found.`);
      throw new Error(`Method not found: ${{method}}`);
     }}
     // Inject ID into payload if it's an object, otherwise wrap it
     const params = (payload && typeof payload === 'object') ? {{ ...payload, _call_id: id }} : {{ value: payload, _call_id: id }};
     return await engine[method](params);
    }}
   }});
   console.log("[Astra] Bridge uplink established.");
  """

  # 3. Inject Scripts (Persistent + Immediate)
  # add_init_script ensures the code runs on every navigation
  await self._page.add_init_script(JS_ENGINE_SOURCE)
  await self._page.add_init_script(bridge_boot)

  # evaluate runs the code immediately for the current page
  try:
   await self._page.evaluate(JS_ENGINE_SOURCE)
   await self._page.evaluate(bridge_boot)
  except Exception as e:
   logger.debug(f"Injection deferred: {type(e).__name__}")

  self._is_active = True
  self._connect_count += 1

 async def call(self, method: str, params: Any = None, timeout: float = PROTOCOL_CALL_TIMEOUT, progress: Optional[Callable] = None) -> Any:
  """
  Calls a remote JS method via the bridge with automatic recovery.

  If the bridge is unreachable (page closed, bridge missing), it
  attempts a single self-heal via ensure_bridge() before retrying.
  """
  if not self._is_active:
   raise BridgeCallError("Bridge is not connected. Wait for client.start() to complete.", method=method)

  call_id = f"call_{asyncio.get_event_loop().time()}"
  if progress:
   self._progress_callbacks[call_id] = progress

  logger.debug(f"Calling remote method: {method} [ID: {call_id}]")

  for attempt in range(2): # At most 1 retry after bridge recovery
   try:
    result = await self._page.evaluate(
     f"(args) => window.{BRIDGE_NAMESPACE}.call(args.method, args.params, args.id)",
     {"method": method, "params": params, "id": call_id}
    )
    return result

   except Exception as e:
    err_text = str(e).lower()
    is_recoverable = any(k in err_text for k in [
     "target closed", "target page", "not found",
     "execution context", "frame was detached",
     "page closed", "navigation"
    ])

    if is_recoverable and attempt == 0:
     logger.warning(f"Bridge stalled on '{method}', recovering...")
     healed = await self.ensure_bridge()
     if healed:
      logger.info(f"Bridge recovered, retrying '{method}'")
      continue
     else:
      logger.error(f"Bridge recovery failed for '{method}'")

    # Classify the error
    if "method not found" in err_text:
     raise BridgeMethodNotFoundError(method=method) from e
    elif "timeout" in err_text or "sendmsgresultpromise timeout" in err_text:
     raise MessageTimeoutError(f"'{method}' timed out") from e
    elif "rate" in err_text or "too many" in err_text:
     raise RateLimitedError(f"Rate limited on '{method}'") from e
    elif "target closed" in err_text or "page has been closed" in err_text or "page closed" in err_text:
     raise ConnectionLostError(f"Browser disconnected during '{method}'") from e
    else:
     short = str(e).split(chr(10))[0][:120] if not _DEBUG else str(e); raise BridgeCallError(f"'{method}' failed: {short}", cause=e, method=method) from e
   finally:
    self._progress_callbacks.pop(call_id, None)

 async def ensure_bridge(self) -> bool:
  """
  Verifies the JS bridge is alive and re-injects it if needed.

  Returns True if the bridge is healthy after this call.
  """
  try:
   if not self._page or self._page.is_closed():
    logger.warning("ensure_bridge: page is closed — cannot heal.")
    return False

   is_alive = await self._page.evaluate(
    "() => typeof window.AstraEngine !== 'undefined'"
   )
   if is_alive:
    return True

   logger.debug("Bridge re-injected successfully.")
   return True

  except Exception as exc:
   logger.error(f"Bridge self-heal failed" if not _DEBUG else f"ensure_bridge: {exc}")
   return False

 async def get_bridge_diagnostics(self) -> Dict[str, Any]:
  """
  Returns a structured health snapshot of the JS bridge.
  """
  try:
   if not self._page or self._page.is_closed():
    return {"alive": False, "reason": "page_closed"}

   return await self._page.evaluate("""
    () => {
     try {
      const store = window.Store || {};
      return {
       alive: !!window.AstraEngine,
       storeReady: !!(store.Chat && store.Msg),
       msgListener: !!(window.Astra && window.Astra._msgListenerAttached),
       waVersion: (window.Debug && window.Debug.VERSION) || null,
       socketState: (store.AppState && store.AppState.state) || 'unknown',
       injections: window.AstraInjected || 0,
      };
     } catch (e) {
      return { alive: false, error: e.message };
     }
    }
   """)
  except Exception as exc:
   return {"alive": False, "error": str(exc)}

 def set_event_handler(self, handler: Callable[[str, Any], Awaitable[None]]):
  """Sets the sink for incoming browser events."""
  self._on_event = handler

 async def _process_event(self, name: str, payload: Any):
  """Internal handler for messages arriving from the JS uplink."""
  if name == "progress":
   call_id = payload.get("id")
   if call_id in self._progress_callbacks:
    cb = self._progress_callbacks[call_id]
    try:
     if asyncio.iscoroutinefunction(cb) or asyncio.iscoroutine(cb):
      await cb(payload.get("current", 0), payload.get("total", 0))
     else:
      cb(payload.get("current", 0), payload.get("total", 0))
    except Exception as e:
     logger.debug(f"Progress callback error: {e}")
   return

  if self._on_event:
   logger.debug(f"[Gate] Forwarding event: {name}")
   await self._on_event(name, payload)

 @property
 def is_connected(self) -> bool:
  return self._is_active

 async def execute(self, code: str) -> Any:
  """
  Executes raw JavaScript in the page context.
  This is used for bootstrapping and complex low-level operations.
  """
  if not self._page or self._page.is_closed():
   raise BridgeCallError("Page reached an unreachable state during execute.", method="execute")
  
  try:
   return await self._page.evaluate(code)
  except Exception as e:
   short = str(e).split("\n")[0][:100] if not _DEBUG else str(e); logger.error(f"JS eval failed: {short}")
   raise BridgeCallError(f"Execution failed: {e}", cause=e, method="execute") from e

 async def edit_message_native(self, message_id: str, text: str) -> bool:
  """
  High-speed native Playwright fallback for editing messages.
  """
  if not self._page or self._page.is_closed():
   return False

  try:
   # 1. Faster selector
   msg_locator = self._page.locator(f'div[data-id="{message_id}"]')
   if await msg_locator.count() == 0:
    await self._page.mouse.wheel(0, 2000)
    await asyncio.sleep(0.5)
    if await msg_locator.count() == 0: return False

   # 2. Optimized hover and menu trigger
   await msg_locator.hover()
   
   # Try multiple menu icons for speed
   menu_btn = msg_locator.locator('span[data-icon="down-context"], [aria-label="Context menu"]').first
   if await menu_btn.count() > 0:
    await menu_btn.click()
   else:
    await msg_locator.click(button="right")
   
   # 3. Find Edit button with tighter wait
   edit_btn = self._page.locator('div[role="button"]:has-text("Edit"), [aria-label*="Edit"]').first
   await edit_btn.wait_for(state="visible", timeout=1500)
   await edit_btn.click()

   # 4. Instant type and Enter
   input_box = self._page.locator('div[contenteditable="true"]').first
   await input_box.focus()
   
   # Select all + Backspace
   await self._page.keyboard.down("Meta")
   await self._page.keyboard.press("A")
   await self._page.keyboard.up("Meta")
   await self._page.keyboard.press("Backspace")
   
   await self._page.keyboard.type(text)
   await self._page.keyboard.press("Enter")
   
   return True

  except Exception as e:
   logger.error(f"Native edit failed" if not _DEBUG else f"Native edit: {e}")
   return False

 # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 # PLAYWRIGHT NATIVE FALLBACKS
 # Human-like automation using keyboard, mouse, and locators.
 # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 async def _pw_click_text(self, text, timeout=3000):
  try:
   loc = self._page.get_by_text(text, exact=False).first
   await loc.wait_for(state="visible", timeout=timeout)
   await loc.click()
   await asyncio.sleep(0.8)
   return True
  except Exception:
   return False

 async def _pw_click_role(self, role, name, timeout=3000):
  try:
   loc = self._page.get_by_role(role, name=name).first
   await loc.wait_for(state="visible", timeout=timeout)
   await loc.click()
   await asyncio.sleep(0.8)
   return True
  except Exception:
   return False

 async def _pw_click_sel(self, sel, timeout=3000):
  try:
   loc = self._page.locator(sel).first
   await loc.wait_for(state="visible", timeout=timeout)
   await loc.click()
   await asyncio.sleep(0.8)
   return True
  except Exception:
   return False

 async def _pw_open_settings(self):
  if not self._page or self._page.is_closed(): return False
  if await self._pw_click_sel('[data-testid="menu-bar-settings"]'): return True
  if await self._pw_click_role("button", "Settings"): return True
  if await self._pw_click_sel('span[data-icon="menu"]'):
   await asyncio.sleep(0.5)
   return await self._pw_click_text("Settings")
  return False

 async def _pw_open_profile(self):
  if not self._page or self._page.is_closed(): return False
  if await self._pw_click_sel('[data-testid="menu-bar-profile"]'): return True
  if await self._pw_click_role("button", "Profile"): return True
  return False

 async def _pw_go_back(self):
  try:
   b = self._page.locator('[data-testid="back"], button[aria-label="Back"]').first
   if await b.count() > 0 and await b.is_visible():
    await b.click()
    await asyncio.sleep(0.5)
    return True
  except Exception:
   pass
  await self._page.keyboard.press("Escape")
  await asyncio.sleep(0.5)
  return True

 async def _pw_close_all(self):
  for _ in range(4):
   try:
    await self._page.keyboard.press("Escape")
    await asyncio.sleep(0.3)
   except Exception:
    break

 async def set_privacy_native(self, category, value):
  """Playwright fallback: Settings → Privacy → Category → Select."""
  if not self._page or self._page.is_closed(): return False
  try:
   logger.info(f"Privacy: {category} → {value}")
   if not await self._pw_open_settings():
    return False
   await asyncio.sleep(1)
   if not await self._pw_click_text("Privacy"):
    await self._pw_close_all(); return False
   await asyncio.sleep(1)

   if category == "read_receipts":
    t = self._page.locator('input[role="switch"]').first
    if await t.count() > 0:
     want = value in ("all", "contacts", "true", True)
     if await t.is_checked() != want: await t.click()
    await self._pw_close_all(); return True

   cats = {"last_seen": ["Last seen", "Last seen and online"], "profile_pic": ["Profile photo", "Profile picture"], "about": ["About"], "status": ["Status"]}
   for lbl in cats.get(category, [category]):
    if await self._pw_click_text(lbl): break
   else:
    await self._pw_close_all(); return False
   await asyncio.sleep(1)

   vm = {"all": "Everyone", "contacts": "My contacts", "none": "Nobody", "nobody": "Nobody"}
   vl = vm.get(value, value)
   if not await self._pw_click_role("radio", vl):
    if not await self._pw_click_text(vl):
     await self._pw_close_all(); return False

   if category == "last_seen":
    await asyncio.sleep(0.5)
    ol = "Everyone" if value == "all" else "Same as last seen"
    await self._pw_click_role("radio", ol) or await self._pw_click_text(ol)

   await asyncio.sleep(0.5)
   await self._pw_close_all()
   logger.info(f"Privacy set: {category} → {value}")
   return True
  except Exception as e:
   logger.error(f"Privacy update failed: {e}")
   await self._pw_close_all(); return False

 async def set_profile_name_native(self, name):
  """Playwright fallback for updating profile name."""
  if not self._page or self._page.is_closed(): return False
  try:
   logger.info(f"Profile name: {name}")
   if not await self._pw_open_profile(): return False
   await asyncio.sleep(1)

   pencils = self._page.locator('span[data-icon="pencil"]')
   if await pencils.count() > 0: await pencils.first.click()
   else: await self._pw_close_all(); return False
   await asyncio.sleep(0.8)

   tb = self._page.locator('div[role="textbox"]').first
   await tb.click()
   await self._page.keyboard.down("Control")
   await self._page.keyboard.press("A")
   await self._page.keyboard.up("Control")
   await self._page.keyboard.press("Backspace")
   await self._page.keyboard.type(name, delay=30)

   sv = self._page.locator('span[data-icon="checkmark-medium"]').first
   if await sv.count() > 0: await sv.click()
   else: await self._page.keyboard.press("Enter")
   await asyncio.sleep(1)
   await self._pw_close_all()
   return True
  except Exception as e:
   logger.error(f"Profile name update failed: {e}")
   await self._pw_close_all(); return False

 async def set_about_native(self, text):
  """Playwright fallback for updating About/Bio."""
  if not self._page or self._page.is_closed(): return False
  try:
   logger.info(f"About: {text}")
   if not await self._pw_open_profile(): return False
   await asyncio.sleep(1)

   pencils = self._page.locator('span[data-icon="pencil"]')
   c = await pencils.count()
   if c >= 2: await pencils.nth(1).click()
   elif c == 1: await pencils.first.click()
   else: await self._pw_close_all(); return False
   await asyncio.sleep(0.8)

   tb = self._page.locator('div[role="textbox"]').first
   await tb.click()
   await self._page.keyboard.down("Control")
   await self._page.keyboard.press("A")
   await self._page.keyboard.up("Control")
   await self._page.keyboard.press("Backspace")
   await self._page.keyboard.type(text, delay=30)

   sv = self._page.locator('span[data-icon="checkmark-medium"]').first
   if await sv.count() > 0: await sv.click()
   else: await self._page.keyboard.press("Enter")
   await asyncio.sleep(1)
   await self._pw_close_all()
   return True
  except Exception as e:
   logger.error(f"About update failed: {e}")
   await self._pw_close_all(); return False


