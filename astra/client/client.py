# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
Astra - The WhatsApp Userbot Framework.

This module provides the main Client class, which is your primary
interface for interacting with WhatsApp.
"""

import os
import json
import logging
import asyncio
import sys
import importlib
import pkgutil
import time
import socket
from pathlib import Path
from typing import Optional, Callable, Any, Dict, List, Union

from ..constants import WHATSAPP_URL, SESSION_STORAGE_PATH, VERSION
from ..models import ClientStatus, Message, Chat, User, JID
from ..errors import (
 LoginFailedError, AstraError, StartupError,
 ProfileReadError, ConnectionLostError,
)

from .lifecycle import LifeCycleController
from .authenticator import Authenticator
from .conversation import Conversation
from .sync_engine import SyncEngine
from .session_store import SessionStore

from ..connection import BrowserController
from ..protocol import ProtocolBridge, EngineAPI
from ..events import EventEmitter, EventDispatcher, Filters, EventContext

from .methods.chat import ChatMethods
from .methods.group import GroupMethods
from .methods.media import MediaMethods
from .methods.account import AccountMethods

logger = logging.getLogger("Astra")

class Client:
 """
 The main Astra Client.

 Handles the browser engine, protocol bridge, and event system 
 to provide a high-level API for WhatsApp automation.
 """

 # --- Global Class Decorators (for Plugins) ---
 _class_handlers = []

 def __init__(
  self,
  session_id: str = "default",
  phone: Optional[str] = None,
  headless: bool = True,
  log_level: int = logging.INFO,
  show_banner: bool = True, use_cache: bool = True
 ):
  """
  Initialize the Astra Client.

  Args:
   session_id: A unique identifier for the session (affects profile caching).
   phone: The WhatsApp phone number (e.g., "919876543210").
   headless: If True, runs the browser without a visual window.
   log_level: Sensitivity of the internal logger.
   show_banner: Whether to print the Astra banner on startup.
  """
  # 1. Configuration
  self.session_id = session_id
  self.session_path = os.path.join(SESSION_STORAGE_PATH, session_id)
  self.phone = phone or os.getenv("PHONE_NUMBER")
  self.headless = headless
  self._show_banner = show_banner
  self.use_cache = use_cache
  # 2. Core Controllers
  self.status = LifeCycleController()
  self.browser = BrowserController(self.session_path, headless=headless)
  self.bridge = ProtocolBridge() # Page attached in start()
  self.api = EngineAPI(self.bridge, client=self)

  # 3. Event System
  self.events = EventEmitter()
  self.dispatcher = EventDispatcher(self)

  # 4. Authentication
  pairing_env = os.getenv("ASTRA_PHONE_PAIRING") or os.getenv("PHONEPAIRING")
  if not self.phone:
   raise ValueError("Configuration Error: 'phone' number is now mandatory for all login methods (including QR) for verification purposes. Please set PHONE_NUMBER env var or pass phone='...' to Client().")

  self.use_pairing = (pairing_env.lower() == "true") if pairing_env else False
  # Pairing mode is optional, but phone number is now required
  self.authenticator = Authenticator(self.browser, self.phone, use_pairing=self.use_pairing)

  # 4b. Method Managers
  self.chat = ChatMethods(self)
  self.group = GroupMethods(self)
  self.media = MediaMethods(self)
  self.account = AccountMethods(self)
  self.privacy = self.account

  # 5. Register Class-Level Handlers (Plugins)
  for event, func, criteria in self._class_handlers:
   self.on(event, criteria=criteria)(func)
  self.startup_at: float = time.time()
  self._class_handlers.clear()

  # Internal Cache
  self._entity_cache: Dict[str, Union[Chat, User]] = {}

  # Internal Readiness Flag
  self._ready_event = asyncio.Event()
  self._disconnecting = False

  # 6. Sync Engine — replaces the old primitive _monitor_loop
  self.sync_engine = SyncEngine(self)

  # 7. Session Store (SQLite cache)
  self.store = SessionStore(self.session_path)
  self.store.open()

 # --- Context Manager ---

 async def __aenter__(self) -> 'Client':
  """Allows using the client as an async context manager."""
  await self.start()
  return self

 async def __aexit__(self, exc_type, exc_val, exc_tb):
  """Ensures the client stops cleanly when the context exits."""
  await self.stop()

 # --- Properties ---

 @property
 def is_connected(self) -> bool:
  return self.status.is_ready()

 @property
 def newfn(self) -> 'ChatMethods':
  """Compatibility alias for the functional core (now directed to ChatMethods)."""
  return self.chat

 async def send_message(self, *args, **kwargs) -> Message:
  """Shortcut for client.chat.send_message."""
  return await self.chat.send_message(*args, **kwargs)

 async def send_media(self, *args, **kwargs) -> Message:
  """Shortcut for client.chat.send_media."""
  return await self.chat.send_media(*args, **kwargs)

 async def send_sticker(self, *args, **kwargs) -> Message:
  """Shortcut for client.media.send_sticker."""
  return await self.media.send_sticker(*args, **kwargs)

 async def send_video(self, chat_id: str, file_path: str, **kwargs) -> Message:
  """Sends a video file with document fallback."""
  try:
   return await self.media.send_video(chat_id, file_path, **kwargs)
  except Exception:
   return await self.media.send_file(chat_id, file_path, document=True, **kwargs)

 async def send_audio(self, chat_id: str, file_path: str, **kwargs) -> Message:
  """Sends an audio file with document fallback."""
  try:
   return await self.media.send_audio(chat_id, file_path, **kwargs)
  except Exception:
   return await self.media.send_file(chat_id, file_path, document=True, **kwargs)
  
 
 async def delete_message(self, chat_id: str, message_id: str, everyone: bool = True) -> bool:
  """Shortcut for client.chat.delete_message."""
  return await self.chat.delete_message(message_id, everyone=everyone)

 async def send_file(self, *args, **kwargs) -> bool:
  """Backward compatibility alias for client.media.send_file."""
  return await self.media.send_file(*args, **kwargs)

 async def download_media(self, *args, **kwargs) -> str:
  """Shortcut for client.media.download_media."""
  return await self.media.download_media(*args, **kwargs)

 async def get_contact(self, contact_id: str) -> User:
  """Shortcut for client.api.get_contact."""
  return await self.api.get_contact(contact_id)

 # --- Core Operations ---

 async def start(self):
  """
  Launches Astra and establishes a connection to WhatsApp.

  This method is asynchronous and will wait until the client is
  fully authenticated and ready to receive events.
  """
  if self.status.is_operational() and self.status.is_ready():
   logger.warning("Client is already running.")
   return

  try:
   # Print startup banner
   if self._show_banner:
    self._print_banner()

   logger.info(f"Initializing [{self.session_id}]...")
   self.status.transition_to(ClientStatus.STARTING)

   # 1. Launch Browser
   page = await self.browser.start()

   # 1b. Clear stale browser caches (prevents WA version mismatch stalls)
   await self._clear_browser_cache(page)

   # 2. Establish Bridge (Pre-auth)
   logger.info("Establishing engine bridge...")
   self.bridge._page = page
   await self.bridge.connect()

   # Wire up event propagation early
   self.bridge.set_event_handler(self.dispatcher.dispatch)

   # 3. Navigate to WhatsApp
   logger.info("Connecting to WhatsApp...")
   await page.goto(WHATSAPP_URL, wait_until="domcontentloaded")

   # 4. Handle Authentication
   self.status.transition_to(ClientStatus.AUTHENTICATING)
   await self.authenticator.login()

   # 5. Mark as Ready
   self.status.transition_to(ClientStatus.READY)
   self._ready_event.set()

   # 6. Start Sync Engine (replaces old _monitor_loop)
   self.sync_engine = SyncEngine(self)
   self.sync_engine.start()

   # 6b. Wire dispatcher → SyncEngine event notification
   self.dispatcher.set_event_callback(self.sync_engine.notify_event_received)

   # 7. Save session metadata + start IDB observer
   await self._save_session_meta()
   await self._start_idb_observer()

   # 8. Initial cache population
   if self.use_cache: await self._populate_cache()

   # Print post-auth session info
   if self._show_banner:
    await self._print_session_info()

   self.startup_at = time.time()
   # Notify listeners
   self.events.emit("ready")

   logger.info("Client is ready.")

  except Exception as e:
   logger.error(f"Startup failed: {e}", exc_info=True)
   self.status.transition_to(ClientStatus.FAILED)
   await self.stop()
   raise StartupError(f"Failed to start Astra: {e}", cause=e)

 async def stop(self):
  """
  Gracefully shuts down the client and releases all resources.
  """
  if self._disconnecting:
   return
  self._disconnecting = True
  logger.info("Shutting down...")
  self.status.transition_to(ClientStatus.SHUTTING_DOWN)

  # Stop sync engine
  self.sync_engine.stop()

  # Close session store
  self.store.close()

  await self.browser.stop()
  self._ready_event.clear()

  self.status.transition_to(ClientStatus.OFFLINE)
  logger.info("Offline.")

 async def restart(self):
  """
  # Restart engine.
  Cleans up browser, processes, and locks before starting fresh.
  """
  logger.warning("Astra Engine restart initiated...")
  await self.stop()
  self._disconnecting = False # Reset for restart
  await asyncio.sleep(2)
  await self.start()

 async def run_forever(self):
  """
  # Blocking loop.
  Keeps the client alive and handles auto-restarts indefinitely.
  """
  logger.info("Running. Press Ctrl+C to stop.")
  while not self._disconnecting:
   try:
    await asyncio.sleep(5)
   except (KeyboardInterrupt, asyncio.CancelledError):
    logger.info("Astra run interrupted by user.")
    await self.stop()
    break
   except Exception as e:
    logger.error(f"Unexpected error in run_forever: {e}")
    await asyncio.sleep(2)

 async def sync(self) -> bool:
  """
  Manually triggers a bridge-level data synchronization.
  Also resets the sync engine stall timer.
  """
  self.sync_engine.notify_event_received()
  return await self.api.sync_data()

 async def logout(self) -> bool:
  """
  Logs out the current session and clears storage.
  """
  result = await self.api.logout()
  self._clear_session_meta()
  return result

 async def scan_dom(self, section: str = "chats") -> list:
  """
  Performs a deep DOM scan of a specific section (e.g., 'chats', 'settings').
  """
  return await self.api.scan_dom(section)

 async def generate_report(self, section: str = "chats") -> str:
  """
  Generates a detailed text report of stable selectors in a section.
  """
  return await self.api.generate_dom_report(section)

 # --- Messaging API (Facade) ---

 async def send_message(self, to: str, text: str, reply_to: Optional[str] = None, **kwargs) -> Message:
  """
  Sends a text message to a chat.

  Args:
   to: The recipient's JID (e.g. '12345@c.us').
   text: The message content.
   reply_to: Optional message ID to quote.
   **kwargs: Additional options like 'mentions'.
  """
  options = {"quotedMsgId": reply_to} if reply_to else {}
  options.update(kwargs)
  return await self.api.send_text(to, text, options=options)

 async def react(self, chat_id: str, message_id: str, emoji: str) -> bool:
  """Adds a reaction emoji to a message."""
  return await self.api.react(message_id, emoji)

 # --- Event Utilities ---

 def on(self, event: str, criteria: Optional[Any] = None):
  """
  Decorator to register an event handler.

  Example::

   @client.on("message", Filters.text_contains("hi"))
   async def on_hi(msg):
    await msg.reply("Hello!")
  """
  return self.events.on(event, criteria=criteria)

 async def wait_for(self, event: str, criteria: Optional[Any] = None, timeout: Optional[float] = None) -> Any:
  """
  Waits for a specific event to occur.
  """
  return await self.dispatcher.wait_for(event, criteria=criteria, timeout=timeout)

 # --- Specialized Decorators ---

 def on_message(self=None, criteria: Optional[Any] = None):
  """
  Decorator for handling new messages.
  Supports both instance (@client.on_message) and class (@Client.on_message).
  """
  if not isinstance(self, Client):
   # Class-level use (@Client.on_message)
   if callable(self) and criteria is None:
    func = self
    Client._class_handlers.append(("message", func, None))
    return func
   _crit = self
   def decorator(func: Callable):
    Client._class_handlers.append(("message", func, _crit))
    return func
   return decorator

  # Instance-level use (@client.on_message)
  if callable(criteria):
   return self.on("message")(criteria)
  return self.on("message", criteria=criteria)

 def on_reaction(self=None, criteria: Optional[Any] = None):
  """
  Decorator for handling reactions.
  Supports both instance (@client.on_reaction) and class (@Client.on_reaction).
  """
  if not isinstance(self, Client):
   if callable(self) and criteria is None:
    func = self
    Client._class_handlers.append(("reaction", func, None))
    return func
   _crit = self
   def decorator(func: Callable):
    Client._class_handlers.append(("reaction", func, _crit))
    return func
   return decorator

  if callable(criteria):
   return self.on("reaction")(criteria)
  return self.on("reaction", criteria=criteria)

 def on_ready(self, func: Callable):
  """Decorator for the 'ready' event."""
  return self.events.on("ready", func)

 # --- Entity Resolution (Telethon Style) ---

 async def get_entity(self, jid: Union[str, JID]) -> Union[Chat, User]:
  """
  Resolves a JID into a hydrated Chat or User object.
  Supported by a local cache to minimize bridge overhead.
  """
  jid_str = str(jid)
  if jid_str in self._entity_cache:
   return self._entity_cache[jid_str]

  data = await self.bridge.call("getChatById", jid_str)
  if data and (data.get("isGroup") or data.get("isReadOnly")):
   # If name is missing or "Unknown", try to use ID user part as title
   if not data.get("name") or data.get("name") == "Unknown":
    data["name"] = jid_str.split("@")[0]
   entity = Chat.from_payload(data, client=self)
  else:
   contact = await self.bridge.call("getContactById", jid_str)
   if not contact:
    # Fallback to a basic User payload if contact lookup fails
    contact = {"id": jid_str, "name": jid_str.split("@")[0]}
   
   # Robust name fallback for contacts too
   if not contact.get("name") or contact.get("name") == "Unknown":
    contact["name"] = jid_str.split("@")[0]
    
   entity = User.from_payload(contact, client=self)

  self._entity_cache[jid_str] = entity
  return entity

 async def get_me(self) -> User:
  data = await self.bridge.call("getMe")
  if not data:
   return User(id=JID.parse("0@c.us"), name="Unknown User", is_me=True, _client=self)
  return User.from_payload(data, client=self)

 def conversation(self, chat_id: str, timeout: float = 60.0) -> Conversation:
  """
  Creates a stateful conversation context for interactive flows.
  """
  return Conversation(self, chat_id, timeout=timeout)

 async def fetch_messages(self, chat_id: str, **kwargs) -> List[Message]:
  """
  Shortcut for client.chat.fetch_messages.
  Fetches messages from a chat with advanced filters.
  """
  return await self.chat.fetch_messages(chat_id, **kwargs)

 # --- Session Management ---

 async def export_session(self) -> dict:
  """
  Exports the current session state (cookies + localStorage).
  Can be used to migrate the session to another instance or server.
  """
  return await self.authenticator.export_session()

 async def import_session(self, state: dict):
  """
  Imports a previously exported session state.
  This should be called BEFORE calling client.start().
  """
  await self.authenticator.import_session(state)

 # --- Plugin System (Pyrogram Style) ---

 def load_plugins(self, root: Union[str, Path]):
  """
  Recursively loads event handlers from a directory.

  Handlers in the target directory should use the @Client.on_...
  decorators (if implemented) or be registered via other mechanisms.

  Args:
   root: The root directory containing plugin files.
  """
  root_path = Path(root).resolve()
  if not root_path.exists():
   raise FileNotFoundError(f"Plugin directory not found: {root_path}")

  logger.info(f"Loading plugins from {root_path}...")

  # Add root to sys.path to allow relative imports within plugins
  sys.path.insert(0, str(root_path.parent))

  package_name = root_path.name
  for loader, module_name, is_pkg in pkgutil.walk_packages([str(root_path)], prefix=f"{package_name}."):
   try:
    importlib.import_module(module_name)
    logger.debug(f"Loaded plugin module: {module_name}")

    # Register discovered handlers to THIS instance
    for event, func, criteria in Client._class_handlers:
     # Wrap handler to inject 'client' (self) as first argument
     # This supports the standard (client, message) signature
     async def wrapper(event_payload, _f=func):
      return await _f(self, event_payload)
     
     self.on(event, criteria=criteria)(wrapper)
    Client._class_handlers.clear()

   except Exception as e:
    logger.error(f"Failed to load plugin {module_name}: {e}", exc_info=True)

 async def run_until_disconnected(self):
  """
  Starts the client and blocks until the connection is lost or the
  process is terminated.
  """
  if not self.status.is_ready():
   await self.start()

  logger.info("Client is running. Press Ctrl+C to stop.")
  try:
   while self.status.is_operational():
    await asyncio.sleep(1)
  except (KeyboardInterrupt, asyncio.CancelledError):
   logger.info("Shutdown signal received.")
  finally:
   await self.stop()

 def run_forever_sync(self):
  """
  Main blocking entry point. Runs the client until the event loop 
  is stopped or an unrecoverable error occurs.
  
  Environment Variables:
   TRACE_ERROR (bool): If true, prints full Python stack traces on failure.
   Defaults to False (shows clean error + hint).
  """
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  try:
   loop.run_until_complete(self.run_until_disconnected())
  except KeyboardInterrupt:
   pass
  except Exception as e:
   import os
   if os.environ.get("TRACE_ERROR", "false").lower() == "true":
    raise e
   else:
    # Clean error output for end-users
    print(f"Error: {e}")
    exit(1)
  finally:
   loop.close()

 # --- Session Management ---

 async def _clear_browser_cache(self, page):
  """
  Clears stale browser caches on startup to prevent WA Web version
  mismatches and sync stalls. Preserves authentication cookies and
  localStorage (session data) — only evicts Service Workers, Cache
  Storage, and temporary data.
  """
  try:
   context = self.browser.context
   # Clear Service Workers & Cache Storage (these cause version mismatch)
   await page.evaluate("""
    async () => {
     try {
      // 1. Unregister all service workers
      if ('serviceWorker' in navigator) {
       const registrations = await navigator.serviceWorker.getRegistrations();
       for (const reg of registrations) {
        await reg.unregister();
       }
      }
      // 2. Clear Cache Storage entries
      if ('caches' in window) {
       const names = await caches.keys();
       for (const name of names) {
        await caches.delete(name);
       }
      }
     } catch (e) {
      // Swallow — page may not be on correct origin yet
     }
    }
   """)
   logger.info("Browser cache (SW + CacheStorage) cleared.")
  except Exception as exc:
   logger.debug(f"Cache clear skipped (pre-navigation): {exc}")

 async def _save_session_meta(self):
  """Persists lightweight session metadata to SQLite store."""
  try:
   self.store.save_session_meta(
    session_id=self.session_id,
    phone=self.phone or "",
    wa_version=self.sync_engine._wa_version or "",
    pid=os.getpid()
   )
  except Exception as exc:
   logger.debug(f"Failed to save session metadata: {exc}")

 def _clear_session_meta(self):
  """Clears session metadata on logout."""
  try:
   self.store.clear_session_meta()
  except Exception:
   pass

 def get_session_info(self) -> dict:
  """Returns current session metadata."""
  try:
   return self.store.get_session_info()
  except Exception:
   return {}

 async def _start_idb_observer(self):
  """Starts the IndexedDB transaction observer for cache invalidation."""
  try:
   page = self.browser.page
   await page.evaluate("window.Astra.idb.startObserver()")
   logger.debug("IDB transaction observer started.")
  except Exception as exc:
   logger.debug(f"IDB observer start skipped: {exc}")

 async def _populate_cache(self):
  """Initial population of the SQLite cache from live data."""
  try:
   page = self.browser.page
   chats = await page.evaluate("window.Astra.idb.getChats(200)")
   if chats:
    self.store.upsert_chats(chats)
    logger.info(f"Cache populated: {len(chats)} chats")

   contacts = await page.evaluate("window.Astra.idb.getContacts(500)")
   if contacts:
    self.store.upsert_contacts(contacts)
    logger.info(f"Cache populated: {len(contacts)} contacts")
  except Exception as exc:
   logger.debug(f"Initial cache population skipped: {exc}")

 @property
 def cache(self) -> 'SessionStore':
  """Direct access to the local SQLite cache."""
  return self.store

 # --- Connection Display (Telethon-style) ---

 @staticmethod
 def _get_local_ip() -> str:
  try:
   socket_obj = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   socket_obj.settimeout(1)
   socket_obj.connect(("8.8.8.8", 80))
   ip = socket_obj.getsockname()[0]
   socket_obj.close()
   return ip
  except Exception:
   return "127.0.0.1"

 def _print_banner(self):
  """Prints a Telethon-style connection banner at startup."""
  ip = self._get_local_ip()
  print(f"""
\033[96m╔══════════════════════════════════════════════════╗
║   \033[1mAstra · WhatsApp Client\033[0m\033[96m    ║
║     v{VERSION:<10s}      ║
╠══════════════════════════════════════════════════╣\033[0m
 Session \033[1m{self.session_id}\033[0m
 IP   \033[1m{ip}\033[0m
 Headless \033[1m{self.headless}\033[0m
 PID  \033[1m{os.getpid()}\033[0m
 Auth  \033[1m{'Phone pairing' if self.phone else 'QR code'}\033[0m
\033[96m╚══════════════════════════════════════════════════╝\033[0m
""")

 async def _print_session_info(self):
  """Prints post-auth session info after WA version is detected."""
  try:
   # Wait briefly for WA version detection
   for _ in range(10):
    if self.sync_engine._wa_version:
     break
    await asyncio.sleep(2)

   me = await self.get_me()
   name = me.name or "Unknown"
   jid = me.id.serialized if me.id else "?"
   wa_ver = self.sync_engine._wa_version or "unknown"
   cache_stats = self.store.get_stats()

   print(f"""
\033[92m┌──────────────────────────────────────────────────┐
│ \033[1mConnected\033[0m\033[92m          │
├──────────────────────────────────────────────────┤\033[0m
 User  \033[1m{name}\033[0m
 JID  \033[1m{jid}\033[0m
 WA Ver  \033[1m{wa_ver}\033[0m
 Cache  \033[1m{cache_stats.get('chats', 0)} chats | {cache_stats.get('contacts', 0)} contacts\033[0m
\033[92m└──────────────────────────────────────────────────┘\033[0m
""")
  except Exception as e:
   logger.debug(f"Session info display skipped: {e}")
