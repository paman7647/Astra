# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger("Astra.Tasks")


class Scheduler:
 """
 Simple interval-based scheduler for recurrent tasks.
 """

 def __init__(self, supervisor):
  self._supervisor = supervisor

 def every(self, seconds: float, func: Callable, *args, **kwargs):
  """Schedules a function to run every X seconds."""
  name = f"scheduled_{func.__name__}_{id(func)}"

  async def loop():
   while True:
    try:
     await asyncio.sleep(seconds)
     if asyncio.iscoroutinefunction(func):
      await func(*args, **kwargs)
     else:
      func(*args, **kwargs)
    except asyncio.CancelledError:
     break
    except Exception as e:
     logger.error(f"Scheduled task {name} failed: {e}")

  self._supervisor.spawn(name, loop())
