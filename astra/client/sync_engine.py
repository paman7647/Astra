# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
SyncEngine — Connection health monitor and background sync manager.

This module implements connection health checks, stall detection,
recovery logic, heartbeat polling, and version tracking.

The SyncEngine runs as a background asyncio task. It does not
handle the authentication or pairing sequences.
"""

import asyncio
import logging
import random
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
 from .client import Client

from ..constants import (
 SYNC_HEARTBEAT_INTERVAL,
 SYNC_STALL_THRESHOLD,
 SYNC_POLL_INTERVAL,
 MAX_RECONNECT_ATTEMPTS,
 RECONNECT_DELAY_MAX,
 RETRY_BACKOFF_MULTIPLIER,
 RECONNECT_JITTER_MAX,
)

logger = logging.getLogger("Astra.Sync")


class SyncEngine:
 """
 Background monitor for the Astra client.

 Responsibilities:
  1. Heartbeat — Verifies the JS bridge state.
  2. Stall detection — Monitors event flow gaps.
  3. Fallback polling — Updates counts if events stall.
  4. Version tracking — Monitors WhatsApp Web version updates.
  5. Event binding — Ensures listeners are attached.
  6. Reconnection — Handles automatic restarts on failure.
 """

 def __init__(self, client: "Client"):
  self._client = client
  self._task: Optional[asyncio.Task] = None
  self._running = False

  # Timestamps
  self._last_event_ts: float = time.monotonic()
  self._last_heartbeat_ts: float = 0.0
  self._last_poll_ts: float = 0.0
  self._last_cache_sync_ts: float = 0.0
  self._start_ts: float = 0.0

  # WA Web version tracking
  self._wa_version: Optional[str] = None

  # Reconnect state
  self._reconnect_attempts: int = 0

  # Counters for diagnostics
  self._total_heartbeats: int = 0
  self._total_stalls_detected: int = 0
  self._total_rebinds: int = 0

 # ------------------------------------------------------------------
 # Lifecycle
 # ------------------------------------------------------------------

 def start(self):
  """Starts the background sync engine."""
  if self._running:
   return
  self._running = True
  self._start_ts = time.monotonic()
  self._last_event_ts = time.monotonic()
  self._reconnect_attempts = 0
  self._task = asyncio.create_task(self._run_loop())
  logger.info("SyncEngine started.")

 def stop(self):
  """Stops the sync engine gracefully."""
  self._running = False
  if self._task and not self._task.done():
   self._task.cancel()
  logger.info("SyncEngine stopped.")

 def notify_event_received(self):
  """Called by the EventDispatcher on every incoming event.

  Resets the stall timer so heartbeat knows events are flowing.
  """
  self._last_event_ts = time.monotonic()
  # Successful event receipt means connection is healthy
  self._reconnect_attempts = 0

 @property
 def uptime_seconds(self) -> float:
  """Returns seconds since engine start."""
  if self._start_ts == 0:
   return 0.0
  return time.monotonic() - self._start_ts

 @property
 def seconds_since_last_event(self) -> float:
  """Returns seconds since the last JS event was received."""
  return time.monotonic() - self._last_event_ts

 # ------------------------------------------------------------------
 # Main loop
 # ------------------------------------------------------------------

 async def _run_loop(self):
  """Background loop for health and sync checks."""
  logger.debug("SyncEngine loop entered.")

  # Initial delay — let WA Web fully stabilize after auth
  await asyncio.sleep(15)

  while self._running:
   try:
    now = time.monotonic()

    # 1. Heartbeat check
    if (now - self._last_heartbeat_ts) >= SYNC_HEARTBEAT_INTERVAL:
     await self._heartbeat()
     self._last_heartbeat_ts = now

    # 2. Stall detection
    if self.seconds_since_last_event > SYNC_STALL_THRESHOLD:
     await self._handle_stall()

    # 3. Fallback poll (only if heartbeat passes)
    if (now - self._last_poll_ts) >= SYNC_POLL_INTERVAL:
     await self._fallback_poll()
     self._last_poll_ts = now

    # 4. Periodic cache reconciliation (every 5 min)
    if (now - self._last_cache_sync_ts) >= 300:
     await self._sync_cache()
     self._last_cache_sync_ts = now

   except asyncio.CancelledError:
    break
   except Exception as exc:
    logger.debug(f"SyncEngine iteration error: {exc}")

   await asyncio.sleep(5)

  logger.debug("SyncEngine loop exited.")

 # ------------------------------------------------------------------
 # Heartbeat
 # ------------------------------------------------------------------

 async def _heartbeat(self):
  """Verifies the JS bridge and Store are alive inside the browser."""
  self._total_heartbeats += 1
  try:
   health = await self._get_bridge_health()
   if health is None:
    logger.warning("Heartbeat: bridge unreachable.")
    await self._attempt_bridge_recovery()
    return

   # Version tracking
   new_version = health.get("waVersion")
   if new_version and new_version != self._wa_version:
    if self._wa_version is not None:
     logger.warning(
      f"WA Web version changed: {self._wa_version} → {new_version}. "
      "Injected scripts may need re-validation."
     )
     self._client.events.emit("version_changed", {
      "old": self._wa_version,
      "new": new_version,
     })
    else:
     logger.info(f"WA Web version detected: {new_version}")
    self._wa_version = new_version

   # Event listener verification
   if not health.get("msgListenerAttached"):
    logger.warning("Heartbeat: message listeners detached — rebinding.")
    await self._rebind_events()

   # Store readiness
   if not health.get("storeReady"):
    logger.warning("Heartbeat: Store not ready — attempting re-init.")
    await self._reinit_store()

  except Exception as exc:
   logger.debug(f"Heartbeat failed: {exc}")

 async def _get_bridge_health(self) -> Optional[dict]:
  """Queries the browser for a structured health payload."""
  try:
   page = self._client.browser.page
   if not page or page.is_closed():
    return None

   return await page.evaluate("""
    () => {
     try {
      const store = window.Store || {};
      const astra = window.Astra || {};

      // Socket / Stream state
      let socketState = 'UNKNOWN';
      if (store.AppState && store.AppState.state) {
       socketState = store.AppState.state;
      } else if (store.WAWebStreamModel && store.WAWebStreamModel.Stream) {
       socketState = store.WAWebStreamModel.Stream.state || 'UNKNOWN';
      }

      return {
       storeReady: !!(store.Chat && store.Msg && store.SendMessage),
       msgListenerAttached: !!astra._msgListenerAttached,
       chatCount: store.Chat ? (store.Chat.getModelsArray ? store.Chat.getModelsArray().length : (store.Chat.models ? store.Chat.models.length : 0)) : 0,
       msgCount: store.Msg ? (store.Msg.getModelsArray ? store.Msg.getModelsArray().length : (store.Msg.models ? store.Msg.models.length : 0)) : 0,
       waVersion: (typeof window.Debug !== 'undefined' && window.Debug.VERSION) ? window.Debug.VERSION : null,
       socketState: socketState,
       bridgeAlive: !!window.AstraEngine,
       injectionCount: window.AstraInjected || 0,
      };
     } catch (e) {
      return null;
     }
    }
   """)
  except Exception:
   return None

 # ------------------------------------------------------------------
 # Stall detection & recovery
 # ------------------------------------------------------------------

 async def _handle_stall(self):
  """Handles a detected sync stall (no events for SYNC_STALL_THRESHOLD)."""
  self._total_stalls_detected += 1
  stall_s = self.seconds_since_last_event
  logger.warning(
   f"Sync stall detected -- no events for {stall_s:.0f}s "
   f"(threshold: {SYNC_STALL_THRESHOLD}s). Attempt #{self._reconnect_attempts + 1}"
  )

  self._client.events.emit("sync_stall", {
   "seconds": stall_s,
   "attempt": self._reconnect_attempts + 1,
  })

  # Step 1: Try rebinding events (lightweight fix)
  rebound = await self._rebind_events()
  if rebound:
   # Give events a chance to flow
   await asyncio.sleep(10)
   if self.seconds_since_last_event < SYNC_STALL_THRESHOLD:
    logger.info("Sync recovered after event rebind.")
    self._client.events.emit("sync_recovered", {"method": "rebind"})
    self._reconnect_attempts = 0
    return

  # Step 2: Try a full Store re-init + deepSync
  try:
   await self._reinit_store()
   await asyncio.sleep(5)
   if self.seconds_since_last_event < SYNC_STALL_THRESHOLD:
    logger.info("Sync recovered after Store re-init.")
    self._client.events.emit("sync_recovered", {"method": "reinit"})
    self._reconnect_attempts = 0
    return
  except Exception as exc:
   logger.debug(f"Store re-init during stall recovery failed: {exc}")

  # Step 3: Full reconnect with exponential backoff
  await self._reconnect_with_backoff()

 async def _reconnect_with_backoff(self):
  """Triggers a full client restart with exponential backoff + jitter."""
  if self._reconnect_attempts >= MAX_RECONNECT_ATTEMPTS:
   logger.critical(
    f"Max reconnect attempts ({MAX_RECONNECT_ATTEMPTS}) reached. "
    "Manual intervention may be required."
   )
   self._client.events.emit("sync_failed", {
    "attempts": self._reconnect_attempts,
   })
   # Reset counter to allow future attempts after a long cooldown
   self._reconnect_attempts = 0
   await asyncio.sleep(RECONNECT_DELAY_MAX * 2)
   return

  self._reconnect_attempts += 1
  base_delay = min(
   RETRY_BACKOFF_MULTIPLIER ** self._reconnect_attempts,
   RECONNECT_DELAY_MAX,
  )
  jitter = random.uniform(0, RECONNECT_JITTER_MAX)
  delay = base_delay + jitter

  logger.warning(
   f"Reconnecting in {delay:.1f}s "
   f"(attempt {self._reconnect_attempts}/{MAX_RECONNECT_ATTEMPTS}, "
   f"base={base_delay:.1f}s, jitter={jitter:.1f}s)"
  )

  await asyncio.sleep(delay)

  try:
   # Stop the sync engine before restart to avoid recursive loops
   self._running = False
   await self._client.restart()
   # restart() calls start() which re-creates a fresh SyncEngine
  except Exception as exc:
   logger.error(f"Reconnect attempt {self._reconnect_attempts} failed: {exc}")
   self._running = True # Re-enable if restart fails

 # ------------------------------------------------------------------
 # Bridge recovery helpers
 # ------------------------------------------------------------------

 async def _attempt_bridge_recovery(self):
  """Attempts to recover the protocol bridge when it becomes unreachable."""
  logger.info("Attempting bridge recovery...")
  try:
   page = self._client.browser.page
   if not page or page.is_closed():
    logger.warning("Page is closed — triggering full reconnect.")
    await self._reconnect_with_backoff()
    return

   # Re-inject the bridge
   bridge = self._client.bridge
   await bridge.connect()
   logger.info("Bridge re-injected successfully.")
   self._client.events.emit("bridge_reinjected", {})
  except Exception as exc:
   logger.error(f"Bridge recovery failed: {exc}")
   await self._reconnect_with_backoff()

 async def _rebind_events(self) -> bool:
  """Re-attaches JS event listeners if they were lost."""
  self._total_rebinds += 1
  try:
   page = self._client.browser.page
   if not page or page.is_closed():
    return False

   result = await page.evaluate("""
    () => {
     try {
      const Store = window.Store;
      const Astra = window.Astra;
      if (!Store || !Store.Msg || !Astra) return false;

      // Force re-attach message listener
      if (!Astra._msgListenerAttached) {
       const handleNewMsg = (msg) => {
        try {
         const serialized = Astra.serializeMsg(msg);
         if (!serialized) return;
         if (msg.type === 'ciphertext') {
          msg.once('change:type', (_msg) => handleNewMsg(_msg));
          return;
         }
         if (Astra.emit) {
          Astra.emit('msg', serialized);
         }
        } catch (e) {
         console.error('[Astra] Rebind capture error:', e);
        }
       };

       Store.Msg.on('add', handleNewMsg);
       Store.Msg.on('change:body', (msg) => {
        const s = Astra.serializeMsg(msg);
        if (Astra.emit) Astra.emit('msg_edit', s);
       });
       Store.Msg.on('change:ack', (msg) => {
        const s = Astra.serializeMsg(msg);
        if (Astra.emit) Astra.emit('msg_ack', s);
       });

       Astra._msgListenerAttached = true;
       console.log('[Astra] Events re-bound by SyncEngine.');
       return true;
      }
      return true; // Already attached
     } catch (e) {
      console.error('[Astra] Rebind failed:', e);
      return false;
     }
    }
   """)
   if result:
    logger.info("Event listeners verified/re-bound.")
   return bool(result)
  except Exception as exc:
   logger.debug(f"Event rebind failed: {exc}")
   return False

 async def _reinit_store(self):
  """Re-initializes the WhatsApp Store modules inside the browser."""
  try:
   page = self._client.browser.page
   if not page or page.is_closed():
    return

   await page.evaluate("""
    () => {
     if (window.Astra && window.Astra.initializeEngine) {
      window.Astra.initializeEngine();
      console.log('[Astra] Store re-initialized by SyncEngine.');
     }
    }
   """)
  except Exception as exc:
   logger.debug(f"Store re-init failed: {exc}")

 # ------------------------------------------------------------------
 # Fallback polling
 # ------------------------------------------------------------------

 async def _fallback_poll(self):
  """Polls WhatsApp Web internals for data changes when events are stalled.

  This acts as a safety net when the realtime event emitters fail
  silently (a known issue in WhatsApp Web integrations).
  """
  if self.seconds_since_last_event < SYNC_STALL_THRESHOLD / 2:
   # Events are flowing fine — skip the poll
   return

  try:
   page = self._client.browser.page
   if not page or page.is_closed():
    return

   poll_result = await page.evaluate("""
    () => {
     try {
      const Store = window.Store;
      if (!Store || !Store.Chat) return null;

      const chatCount = Store.Chat.getModelsArray
       ? Store.Chat.getModelsArray().length
       : (Store.Chat.models ? Store.Chat.models.length : 0);
      const msgCount = Store.Msg
       ? (Store.Msg.getModelsArray
        ? Store.Msg.getModelsArray().length
        : (Store.Msg.models ? Store.Msg.models.length : 0))
       : 0;

      // Check for unread chats as a sync indicator
      let unreadCount = 0;
      const chats = Store.Chat.getModelsArray
       ? Store.Chat.getModelsArray()
       : (Store.Chat.models || []);
      for (const c of chats) {
       if (c.unreadCount > 0) unreadCount++;
      }

      return { chatCount, msgCount, unreadCount };
     } catch (e) {
      return null;
     }
    }
   """)

   if poll_result:
    logger.debug(
     f"Fallback poll: chats={poll_result.get('chatCount', 0)}, "
     f"msgs={poll_result.get('msgCount', 0)}, "
     f"unread={poll_result.get('unreadCount', 0)}"
    )
  except Exception as exc:
   logger.debug(f"Fallback poll failed: {exc}")

 # ------------------------------------------------------------------
 # Diagnostics
 # ------------------------------------------------------------------

 def get_diagnostics(self) -> dict:
  """Returns a structured diagnostic snapshot of the sync engine state."""
  diag = {
   "running": self._running,
   "uptime_s": round(self.uptime_seconds, 1),
   "last_event_age_s": round(self.seconds_since_last_event, 1),
   "wa_version": self._wa_version,
   "reconnect_attempts": self._reconnect_attempts,
   "total_heartbeats": self._total_heartbeats,
   "total_stalls": self._total_stalls_detected,
   "total_rebinds": self._total_rebinds,
  }
  # Include cache stats if available
  try:
   if hasattr(self._client, 'store') and self._client.store._conn:
    diag["cache"] = self._client.store.get_stats()
  except Exception:
   pass
  return diag

 # ------------------------------------------------------------------
 # Cache reconciliation
 # ------------------------------------------------------------------

 async def _sync_cache(self):
  """Periodic full sync: browser IndexedDB → Python SQLite."""
  try:
   page = self._client.browser.page
   if not page or page.is_closed():
    return
   if not hasattr(self._client, 'store') or not self._client.store._conn:
    return

   chats = await page.evaluate("window.Astra.idb.getChats(200)")
   if chats:
    self._client.store.upsert_chats(chats)

   contacts = await page.evaluate("window.Astra.idb.getContacts(500)")
   if contacts:
    self._client.store.upsert_contacts(contacts)

   logger.debug(
    f"Cache sync complete: {len(chats or [])} chats, {len(contacts or [])} contacts"
   )
  except Exception as exc:
   logger.debug(f"Cache sync failed: {exc}")
