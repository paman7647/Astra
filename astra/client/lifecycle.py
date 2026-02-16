# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module manages the operational lifecycle of the Astra client.
It provides a safe way to transition between states like STARTING, READY, and STOPPED.
"""

from enum import Enum, auto
import logging
from astra.models import ClientStatus

logger = logging.getLogger("Astra.Status")

class LifeCycleController:
 """
 Expert-grade state machine for managing client health and transitions.
 """

 def __init__(self):
  self._current_status = ClientStatus.OFFLINE

 def transition_to(self, new_status: ClientStatus):
  """
  Safely transitions the client to a new operational state.

  Args:
   new_status: The state to transition into.
  """
  old_status = self._current_status
  if old_status == new_status:
   return

  self._current_status = new_status
  logger.info(f"Client state changed: {old_status.name} -> {new_status.name}")

 def is_ready(self) -> bool:
  """Returns True if the client is fully initialized and operational."""
  return self._current_status == ClientStatus.READY

 def is_operational(self) -> bool:
  """Returns True if the client has not failed or been stopped."""
  return self._current_status not in {ClientStatus.OFFLINE, ClientStatus.FAILED, ClientStatus.SHUTTING_DOWN}

 @property
 def current(self) -> ClientStatus:
  return self._current_status
