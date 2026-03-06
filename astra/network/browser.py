# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module manages the underlying Chromium browser instance.
It handles instance locking, crash recovery, and console relay.
"""

import os
import logging
import asyncio
import subprocess
import fcntl
from typing import Optional, Dict, Any, Callable, Awaitable, List

import signal
import time

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError

from ..constants import DEFAULT_USER_AGENT, WHATSAPP_URL
from ..errors import (
 BrowserLimitError, ConnectionLostError,
 BrowserStartError, BrowserCrashError,
)

logger = logging.getLogger("Browser")

class BrowserController:
 """
 Controller for the Playwright browser engine.

 This class ensures that only one instance of Astra uses a specific
 session directory and provides a stable interface for page interactions.
 """

 def __init__(self, session_path: str, headless: bool = True):
  """
  Initialize the controller.

  Args:
   session_path: Path to the browser profile directory.
   headless: Whether to run the browser without a UI.
  """
  self.session_path = os.path.abspath(session_path)
  self.headless = headless

  self._playwright = None
  self._browser: Optional[Browser] = None
  self._context: Optional[BrowserContext] = None
  self._page: Optional[Page] = None

  self._pending_storage: List[Dict[str, Any]] = []
  self._crash_handler: Optional[Callable[[], Awaitable[None]]] = None

  self._lock_file = os.path.join(self.session_path, "session.lock")
  self._lock_fh = None

 def _terminate_profile_processes(self, user_data_dir: str):
  """
  Close any existing Chromium/Playwright process using the same profile dir.
  This prevents ProcessSingleton lock conflicts on start/restart.
  """
  try:
   proc = subprocess.run(
    ["ps", "-ax", "-o", "pid=,command="],
    capture_output=True,
    text=True,
    check=False,
   )
   if proc.returncode != 0:
    return

   user_data_dir = os.path.abspath(user_data_dir)
   pids: List[int] = []
   for line in proc.stdout.splitlines():
    line = line.strip()
    if not line:
     continue
    parts = line.split(None, 1)
    if len(parts) < 2:
     continue
    pid_str, cmd = parts
    if not pid_str.isdigit():
     continue
    pid = int(pid_str)
    if pid == os.getpid():
     continue
    if user_data_dir not in cmd:
     continue
    if "firefox" not in cmd.lower() and "playwright" not in cmd.lower():
     continue
    pids.append(pid)

   if not pids:
    return

   logger.warning(f"Detected {len(pids)} existing browser processes for this session. Cleaning up...")
   for pid in pids:
    try:
     os.kill(pid, signal.SIGTERM)
    except Exception:
     pass

   time.sleep(1.0) # Graceful shutdown window

   for pid in pids:
    try:
     os.kill(pid, 0) # Check if still alive
     os.kill(pid, signal.SIGKILL)
    except Exception:
     continue
  except Exception as e:
   logger.debug(f"Process cleanup skipped: {e}")

 async def start(self) -> Page:
  """
  Launches the browser and navigates to WhatsApp Web.

  Returns:
   The primary Playwright Page object.

  Raises:
   BrowserLimitError: If another instance is using the same session.
  """
  self._acquire_session_lock()

  # Cleanup stale processes and locks.
  self._terminate_profile_processes(self.session_path)
  for lock_name in ["SingletonLock", "lock", ".parentlock"]:
   lock_p = os.path.join(self.session_path, lock_name)
   if os.path.exists(lock_p):
    try:
     os.remove(lock_p)
     logger.debug(f"Cleaned: {lock_name}")
    except Exception: pass

  try:
   logger.info("Starting engine...")
   self._playwright = await async_playwright().start()

   # Chromium launch - industry standard for WA Web stability
   self._context = await self._playwright.chromium.launch_persistent_context(
    user_data_dir=self.session_path,
    headless=self.headless,
    user_agent=DEFAULT_USER_AGENT,
    viewport={'width': 1280, 'height': 720},
    bypass_csp=True,
    ignore_https_errors=True,
    args=[
     '--no-sandbox',
     '--disable-setuid-sandbox',
     '--disable-dev-shm-usage',
     '--disable-web-security',
     '--disable-features=IsolateOrigins,site-per-process',
     '--disable-accelerated-2d-canvas',
     '--disable-software-rasterizer',
     '--no-first-run',
     '--no-zygote',
     '--disable-gpu',
     '--mute-audio'
    ]
   )

   # Access the default page or create one
   self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

   # Injection: Restore localStorage if pending
   if self._pending_storage:
    logger.debug("Restoring storage...")
    for origin_data in self._pending_storage:
     url = origin_data.get("origin")
     storage = origin_data.get("localStorage", {})
     
     # We must navigate to the origin to set localStorage
     # Persistent context handles cookies, but localStorage is origin-bound
     try:
      await self._page.goto(url, wait_until="commit")
      await self._page.evaluate("""
       (data) => {
        for (const [key, val] of Object.entries(data)) {
         localStorage.setItem(key, val);
        }
       }
      """, storage)
     except Exception as e:
      logger.warning(f"Failed to restore localStorage for {url}: {e}")
      
    self._pending_storage = []

   # Stability: Set long timeouts for slow networks
   self._page.set_default_timeout(60000)

   # Anti-detection: Hide automation signatures
   await self._page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

   # Wire up event listeners
   self._page.on("console", self._relay_console)
   self._context.on("close", self._handle_termination)

   logger.info("Engine is ready.")
   return self._page

  except Exception as e:
   await self.stop()
   raise ConnectionLostError(f"Failed to start browser: {e}")

 async def stop(self):
  """
  Gracefully shuts down the browser and releases files.
  """
  logger.debug("Stopping engine...")
  try:
   if self._page: await self._page.close()
   if self._context: await self._context.close()
   if self._playwright: await self._playwright.stop()
  except Exception as e:
   logger.debug(f"Errors during cleanup: {e}")
  finally:
   self._release_session_lock()
   self._reset_state()

 def set_crash_handler(self, handler: Callable[[], Awaitable[None]]):
  """Registers a callback for when the browser crashes."""
  self._crash_handler = handler

 async def get_state(self) -> str:
  """
  Detects the current state of WhatsApp Web (QR, Loading, Connected).
  """
  if not self._page or self._page.is_closed():
   return "OFFLINE"

  try:
   # Match using DOM inspection and Global state.
   return await self._page.evaluate("""
    () => {
     const check = (sel) => !!document.querySelector(sel);

     if (window.Store && window.Store.Stream) {
      const s = window.Store.Stream;
      if (s.state === 'CONNECTED' || s.mode === 'MAIN') return "CONNECTED";
     }

     if (check('[data-testid="side"]') || check('#pane-side')) return "CONNECTED";
     if (check('[data-testid="qrcode"]')) return "LOGIN_QR";
     if (check('input[type="tel"]')) return "LOGIN_PHONE";
     if (check('[data-testid="startup-loading-screen"]')) return "LOADING";

     return "INITIALIZING";
    }
   """)
  except Exception:
   return "ERROR"

 @property
 def context(self) -> BrowserContext:
  """Provides direct access to the Playwright BrowserContext."""
  if not self._context:
   raise ConnectionLostError("The browser context is not active.")
  return self._context

 @property
 def page(self) -> Page:
  """Provides direct access to the Playwright Page object."""
  if not self._page or self._page.is_closed():
   raise ConnectionLostError("The browser page is no longer available.")
  return self._page

 # --- Internal Management ---

 def _acquire_session_lock(self):
  """Prevents multiple Astra instances from clashing on the same profile."""
  os.makedirs(self.session_path, exist_ok=True)

  try:
   self._lock_fh = open(self._lock_file, "w")
   # LOCK_EX: exclusive lock
   # LOCK_NB: non-blocking, fail if already locked
   fcntl.lockf(self._lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)

   # Write PID for diagnostic visibility
   self._lock_fh.write(str(os.getpid()))
   self._lock_fh.flush()

  except (IOError, OSError):
   if self._lock_fh:
    self._lock_fh.close()
    self._lock_fh = None
   raise BrowserLimitError(
    f"Astra session '{os.path.basename(self.session_path)}' is already in use by another process."
   )

 def _release_session_lock(self):
  """Releases the OS-level lock and closes the file handle."""
  if self._lock_fh:
   try:
    fcntl.lockf(self._lock_fh, fcntl.LOCK_UN)
    self._lock_fh.close()
   except: pass
   finally:
    self._lock_fh = None
    if os.path.exists(self._lock_file):
     try: os.remove(self._lock_file)
     except: pass

 def _reset_state(self):
  self._page = None
  self._context = None
  self._playwright = None

 async def _handle_termination(self, _=None):
  logger.critical("Detecting browser shutdown!")
  if self._crash_handler:
   await self._crash_handler()

 def _relay_console(self, msg):
  """Passes browser logs to Python's logging system with filtering."""
  text = msg.text
  if " [Astra] " in text:
   # These are our internal bridge logs
   logger.debug(f"Engine: {text.split('[Astra]', 1)[1].strip()}")
  elif msg.type == "error":
   # Real JS errors on the page
   if not any(x in text for x in ["SameSite", "Content-Security-Policy", "ErrorUtils"]):
    logger.error(f"Browser Error: {text}")
  else:
   # Everything else is just debug noise
   logger.debug(f"JS: {text}")
