# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import asyncio
import logging
from typing import Dict, Any, Coroutine, Optional, Set, Callable


logger = logging.getLogger("Astra.Tasks")


class TaskSupervisor:
 """
 Hands-on manager for all asynchronous background tasks.
 Guarantees no orphaned tasks and provides health insights.
 """

 def __init__(self):
  self._tasks: Dict[str, asyncio.Task] = {}
  self._on_failure_callbacks: List[Callable[[str, Exception], None]] = []

 def spawn(self, name: str, coro: Coroutine[Any, Any, Any]) -> asyncio.Task:
  """
  Spawns a named background task and ensures it is tracked.

  Args:
   name: Human-readable unique identifier for the task.
   coro: The coroutine to execute.
  """
  if name in self._tasks and not self._tasks[name].done():
   logger.warning(f"Task '{name}' is already running. Cancelling previous instance.")
   self._tasks[name].cancel()

  task = asyncio.create_task(coro, name=name)
  self._tasks[name] = task

  # Monitor for completion or failure
  task.add_done_callback(lambda t: self._on_task_done(name, t))
  return task

 def _on_task_done(self, name: str, task: asyncio.Task):
  """Internal cleanup when a task concludes."""
  try:
   if name in self._tasks:
    del self._tasks[name]

   if task.cancelled():
    logger.debug(f"Task '{name}' was cancelled successfully.")
    return

   exc = task.exception()
   if exc:
    logger.error(f"Supervised task '{name}' failed with exception: {exc}", exc_info=exc)
    for cb in self._on_failure_callbacks:
     try:
      cb(name, exc)
     except Exception as fatal:
      logger.critical(f"Task failure callback failed: {fatal}")
   else:
    logger.debug(f"Task '{name}' completed successfully.")

  except asyncio.CancelledError:
   pass
  except Exception as e:
   logger.critical(f"Critical error in supervisor cleanup for '{name}': {e}")

 async def cancel_all(self, timeout: float = 5.0):
  """
  Gracefully cancels all tracked tasks and awaits their termination.
  """
  if not self._tasks:
   return

  active_tasks = [t for t in self._tasks.values() if not t.done()]
  if not active_tasks:
   return

  logger.info(f"Terminating {len(active_tasks)} supervised tasks...")
  for task in active_tasks:
   task.cancel()

  try:
   await asyncio.wait(active_tasks, timeout=timeout)
  except asyncio.TimeoutError:
   logger.warning("Timed out while waiting for tasks to terminates. Proceeding with shutdown.")

  self._tasks.clear()

 def add_failure_callback(self, callback: Callable[[str, Exception], None]):
  """Registers a global callback for managed task failures."""
  self._on_failure_callbacks.append(callback)

 def health(self) -> Dict[str, Any]:
  """Provides a snapshot of task health."""
  return {
   "active_count": len(self._tasks),
   "running": [name for name, t in self._tasks.items() if not t.done()],
   "status": "HEALTHY" if not self._tasks else "BUSY"
  }
