# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the TaskSupervisor, which manages background
asyncio tasks for the Astra client.
"""

import asyncio
import logging
from typing import Dict, Awaitable

logger = logging.getLogger("Astra.System")

class TaskSupervisor:
 """
 Expert-grade task manager.

 Tracks background loops and ensures they are cleanly terminated
 when the client stops.
 """

 def __init__(self):
  self._tasks: Dict[str, asyncio.Task] = {}

 def start_task(self, name: str, coro: Awaitable):
  """Starts a background task and tracks it."""
  if name in self._tasks and not self._tasks[name].done():
   self._tasks[name].cancel()

  task = asyncio.create_task(coro, name=name)
  self._tasks[name] = task

  # Add a callback to log failures
  task.add_done_callback(lambda t: self._handle_completion(name, t))

 async def shutdown(self):
  """Cancels and waits for all tracked tasks to complete."""
  if not self._tasks:
   return

  logger.debug(f"Shutting down {len(self._tasks)} background tasks...")
  for name, task in self._tasks.items():
   if not task.done():
    task.cancel()

  await asyncio.gather(*self._tasks.values(), return_exceptions=True)
  self._tasks.clear()

 def _handle_completion(self, name: str, task: asyncio.Task):
  """Logs exceptions if a background task crashes."""
  try:
   if not task.cancelled() and task.exception():
    logger.error(f"Task '{name}' failed: {task.exception()}", exc_info=task.exception())
  except (asyncio.CancelledError, asyncio.InvalidStateError):
   pass
