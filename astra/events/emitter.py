# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
The EventEmitter is a lightweight registry for application-level events.
It supports both synchronous and asynchronous listeners with optional filtering.
"""

import asyncio
import logging
from typing import Callable, Any, Dict, List, Optional, Union

logger = logging.getLogger("Astra.Events")

class EventEmitter:
 """
 Expert-grade event registry.

 Allows functions to subscribe to specific event names and provides
 mechanisms for firing events with automatic task scheduling for sync
 and async callbacks.
 """

 def __init__(self):
  # Maps event names to a list of (callback, filter) tuples
  self._listeners: Dict[str, List[tuple]] = {}
  # Maps unique integer IDs to their corresponding registration metadata
  self._registry: Dict[int, tuple] = {}

 def on(self, event: str, callback: Optional[Callable] = None, criteria: Any = None):
  """
  Subscribes a listener to an event.

  Can be used as a decorator or a direct function call.

  Args:
   event: The name of the event to listen for.
   callback: The function to execute.
   criteria: An optional filter object or function.

  Example::

   @client.on("message")
   async def handle_message(msg):
    print(msg.body)
  """
  if callback:
   if event not in self._listeners:
    self._listeners[event] = []

   self._listeners[event].append((callback, criteria))

   # Use the function's memory ID as a registry handle
   handle = id(callback)
   self._registry[handle] = (event, callback)

   logger.debug(f"Registered listener '{callback.__name__}' for event '{event}'")
   return handle
  else:
   # Return a decorator if no callback is provided
   def decorator(func):
    return self.on(event, func, criteria)
   return decorator

 def off(self, handle: int):
  """
  Unregisters a listener using its handle.
  """
  if handle in self._registry:
   event, callback = self._registry.pop(handle)
   if event in self._listeners:
    self._listeners[event] = [
     (cb, f) for cb, f in self._listeners[event] if cb != callback
    ]
    logger.debug(f"Unregistered listener from event '{event}'")

 async def emit_async(self, event: str, payload: Any = None):
  """
  Triggers an event and waits for all handlers to complete.
  """
  listeners = self._listeners.get(event, [])
  if not listeners:
   return

  tasks = []
  for callback, criteria in listeners:
   try:
    # 1. Apply Criteria (Filter)
    if criteria:
     if hasattr(criteria, 'passes'):
      if not await criteria.passes(payload):
       # logger.debug(f"Filter failed for '{callback.__name__}'")
       continue
     elif callable(criteria):
      if not criteria(payload):
       # logger.debug(f"Functional filter failed for '{callback.__name__}'")
       continue

    logger.debug(f"Triggering '{callback.__name__}'")
    if asyncio.iscoroutinefunction(callback):
     tasks.append(asyncio.create_task(callback(payload)))
    else:
     callback(payload)
   except Exception as e:
    logger.error(f"Error in listener '{callback.__name__}' for '{event}': {e}", exc_info=True)

  if tasks:
   await asyncio.gather(*tasks, return_exceptions=True)

 def emit(self, event: str, payload: Any = None):
  """
  Triggers an event asynchronously without waiting for completion.
  """
  asyncio.create_task(self.emit_async(event, payload))
