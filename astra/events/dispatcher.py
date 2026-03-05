# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
The EventDispatcher is the central brain of Astra's event system.
It routes incoming data from the bridge to appropriate handlers and waiters.
"""

import logging
import asyncio
import uuid
import time
from typing import Any, Callable, Dict, List, Optional, Union, Awaitable
from dataclasses import dataclass, field

from .filters import Criterion
from .context import EventContext

from ..network.serializers import DataTransformer

logger = logging.getLogger("Events")

@dataclass
class EventSubscription:
 """Represents a registered event or command handler."""
 id: str
 event_name: str
 callback: Callable[..., Awaitable[None]]
 criteria: Optional[Criterion] = None
 priority: int = 0
 is_command: bool = False
 command_name: Optional[str] = None

class EventDispatcher:
 """
 Routes incoming events across the application.

 Handles priority-based execution, command parsing, and event interception
 via middlewares.
 """

 def __init__(self, client):
  self._client = client
  self._subscriptions: Dict[str, List[EventSubscription]] = {}
  self._waiters: Dict[str, List[Dict[str, Any]]] = {}
  self._middlewares: List[Callable[[str, Any], Awaitable[bool]]] = []
  self._on_event_received: Optional[Callable[[], None]] = None
  self._event_count: int = 0

 def add_middleware(self, middleware: Callable[[str, Any], Awaitable[bool]]):
  """Injects a middleware to pre-process or block events."""
  self._middlewares.append(middleware)

 async def wait_for(self, event_name: str, criteria: Optional[Criterion] = None, timeout: Optional[float] = None) -> Any:
  """
  Suspends execution until a specific event arrives.
  """
  future = asyncio.get_event_loop().create_future()
  waiter = {"future": future, "criteria": criteria}

  self._waiters.setdefault(event_name, []).append(waiter)

  try:
   return await asyncio.wait_for(future, timeout=timeout)
  finally:
   # Ensure the waiter is removed regardless of success or timeout
   if event_name in self._waiters:
    self._waiters[event_name] = [w for w in self._waiters[event_name] if w["future"] is not future]

 def subscribe(
  self,
  event_name: str,
  callback: Callable[..., Awaitable[None]],
  criteria: Optional[Criterion] = None,
  priority: int = 0,
  is_command: bool = False,
  command_name: Optional[str] = None
 ) -> str:
  """
  Registers a new event handler.
  """
  sub_id = str(uuid.uuid4())
  sub = EventSubscription(
   id=sub_id,
   event_name=event_name,
   callback=callback,
   criteria=criteria,
   priority=priority,
   is_command=is_command,
   command_name=command_name
  )

  self._subscriptions.setdefault(event_name, []).append(sub)
  # Higher priority runs first
  self._subscriptions[event_name].sort(key=lambda s: s.priority, reverse=True)

  logger.debug(f"Subscribed: {event_name} (id={sub_id[:8]}, priority={priority})")
  return sub_id

 def set_event_callback(self, callback: Callable[[], None]):
  """Registers a callback invoked on every event dispatch (used by SyncEngine)."""
  self._on_event_received = callback

 async def dispatch(self, name: str, payload: Any):
  """
  Dispatches an event through the engine.
  """
  correlation_id = str(uuid.uuid4())[:8]
  self._event_count += 1
  logger.debug(f"Dispatcher received event '{name}' (ID: {correlation_id})")

  # Notify SyncEngine that an event just arrived (resets stall timer)
  if self._on_event_received:
   try:
    self._on_event_received()
   except Exception:
    pass

  # 1. Transform raw payload to Astra models
  is_msg = name in {"message", "msg"}
  if is_msg: name = "message"
  is_reaction = name == "reaction"

  if (is_msg or is_reaction) and isinstance(payload, dict):
   payload = DataTransformer.to_message(payload, self._client)

  # 1b. Filter stale events (older than startup)
  if hasattr(payload, 'timestamp') and payload.timestamp < self._client.startup_at:
   logger.debug(f"[{correlation_id}] Ignoring stale event '{name}' (ts: {payload.timestamp}, startup: {round(self._client.startup_at)})")
   return

  # 2. Contextualize (for Message/Reaction events)
  prefix, cmd, args = (None, None, [])
  if is_msg:
   text = (getattr(payload, 'text', None) or getattr(payload, 'body', None) or "").strip()
   logger.debug(f"[{correlation_id}] Captured text: '{text}'")
   if text and text[0] in "/.!":
    prefix = text[0]
    parts = text[1:].split()
    if parts:
     cmd = parts[0].lower()
     # Sanity check: command names are rarely longer than 32 chars
     if len(cmd) > 32:
      logger.warning(f"[{correlation_id}] Ignoring suspicious long command name: {cmd[:50]}...")
      cmd = None
      parts = []
     else:
      args = parts[1:]

   logger.debug(f"[{correlation_id}] Parsed Command: {cmd}, Prefix: {prefix}")

   # Upgrade payload to EventContext
   payload = EventContext(self._client, payload, cmd, args, prefix)
  elif is_reaction:
   # Wrap reaction in context as well (for consistency)
   payload = EventContext(self._client, payload)

  # 3. Middleware Execution
  for middleware in self._middlewares:
   try:
    if not await middleware(name, payload):
     logger.debug(f"[{correlation_id}] Event '{name}' intercepted by middleware.")
     return
   except Exception as e:
    logger.error(f"[{correlation_id}] Middleware error: {e}")

  # 4. Notify Listeners (via Client EventEmitter)
  if hasattr(self._client, "events"):
   logger.debug(f"[{correlation_id}] Emitting '{name}' to event emitter")
   self._client.events.emit(name, payload)

  # 5. Handle Waiters
  await self._process_waiters(name, payload, cmd, args, prefix, correlation_id)

  # 6. Run Registered Subscriptions
  if name in self._subscriptions:
   for sub in self._subscriptions[name]:
    # Command Check
    if sub.is_command and (not is_msg or cmd != sub.command_name):
     continue

    # Criteria Check
    if sub.criteria:
     if not await sub.criteria.passes(payload):
      continue

    # Run the handler in a new task
    asyncio.create_task(self._execute_safe(sub, payload, cmd, args, prefix, correlation_id))

 # --- Private Execution Logic ---

 async def _process_waiters(self, name, payload, cmd, args, prefix, correlation_id):
  if name not in self._waiters: return

  for waiter in self._waiters[name][:]:
   if waiter["future"].done(): continue

   if waiter["criteria"]:
    ctx = EventContext(self._client, payload, cmd, args, prefix) if name == "message" else payload
    if not await waiter["criteria"].passes(ctx): continue

   waiter["future"].set_result(payload)

 async def _execute_safe(self, sub, payload, cmd, args, prefix, cid):
  start = time.time()
  try:
   if sub.is_command:
    ctx = EventContext(self._client, payload, cmd, args, prefix)
    await sub.callback(ctx)
   else:
    await sub.callback(payload)

   ms = (time.time() - start) * 1000
   logger.debug(f"[{cid}] '{sub.callback.__name__}' done in {ms:.2f}ms")
  except Exception as e:
   logger.error(f"[{cid}] Handler '{sub.callback.__name__}' failed: {e}", exc_info=True)
