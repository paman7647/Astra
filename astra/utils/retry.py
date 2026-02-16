# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import asyncio
import logging
import random
from typing import Callable, Any, Type, Union, Tuple

logger = logging.getLogger("Astra.Utils")


async def with_retry(
 coro_func: Callable[[], Any],
 retries: int = 3,
 delay: float = 2.0,
 backoff: float = 2.0,
 exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
) -> Any:
 """
 Executes a coroutine with exponential backoff and jitter.
 """
 attempt = 0
 current_delay = delay

 while attempt < retries:
  try:
   return await coro_func()
  except exceptions as e:
   attempt += 1
   if attempt >= retries:
    logger.error(f"Final retry attempt failed: {e}")
    raise e

   # Apply jitter to avoid thundering herd
   sleep_time = current_delay * (0.5 + random.random())
   logger.warning(f"Attempt {attempt} failed: {e}. Retrying in {sleep_time:.2f}s...")
   await asyncio.sleep(sleep_time)
   current_delay *= backoff
