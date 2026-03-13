# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import asyncio
import random
import logging
from typing import Callable, Any, Type, Union, Tuple

logger = logging.getLogger("Astra.Utils")

async def with_retry(
 operation: Callable[[], Any],
 attempts: int = 3,
 initial_delay: float = 1.0,
 backoff_factor: float = 2.0,
 exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
) -> Any:
 """
 Executes an async callable with truncated exponential backoff and jitter.

 Args:
  operation: Async function/coroutine to run.
  attempts: Maximum tries.
  initial_delay: Starting wait time in seconds.
  backoff_factor: Multiplier for sequential delays.
  exceptions: Which exception types to catch and retry.
 """
 last_exception = None
 delay = initial_delay

 for i in range(attempts):
  try:
   return await operation()
  except exceptions as e:
   last_exception = e
   if i == attempts - 1:
    break

   # Apply jitter (0.5x to 1.5x of the delay)
   wait_time = delay * (0.5 + random.random())
   logger.warning(f"Retry {i+1}/{attempts} failed: {e}. Waiting {wait_time:.2f}s...")
   await asyncio.sleep(wait_time)
   delay *= backoff_factor

 raise last_exception
