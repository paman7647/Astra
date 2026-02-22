# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides a strategy for retrying failed connections.
It uses exponential backoff to avoid overwhelming the server.
"""

import random
import logging
from typing import Optional
from ..constants import MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY_MAX

logger = logging.getLogger("Sync")

class RetryStrategy:
 """
 A resilient retry manager for connection recovery.

 Implements exponential backoff with random jitter to ensure
 reconnections happen in a nature-friendly way.
 """

 def __init__(
  self,
  base_delay: float = 2.0,
  max_delay: float = RECONNECT_DELAY_MAX,
  max_attempts: int = MAX_RECONNECT_ATTEMPTS
 ):
  self.base_delay = base_delay
  self.max_delay = max_delay
  self.max_attempts = max_attempts
  self._current_attempt = 0

 def reset(self):
  """Resets the attempt counter (usually called on successful connection)."""
  if self._current_attempt > 0:
   logger.info("Connection stable. Resetting retry policy.")
  self._current_attempt = 0

 def next_delay(self) -> Optional[float]:
  """
  Calculates the wait time for the next reconnection attempt.

  Returns:
   The delay in seconds, or None if the retry limit is reached.
  """
  if self._current_attempt >= self.max_attempts:
   return None

  # Exponential growth: 2, 4, 8, 16...
  backoff = min(self.base_delay * (2 ** self._current_attempt), self.max_delay)

  # Add Jitter (0.7 to 1.3 variant) to prevent thundering herd
  delay = backoff * random.uniform(0.7, 1.3)

  self._current_attempt += 1
  logger.debug(f"Retrying connection (Attempt {self._current_attempt}/{self.max_attempts}) in {delay:.2f}s")

  return delay

 @property
 def current_attempt(self) -> int:
  return self._current_attempt
