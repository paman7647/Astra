# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module defines the foundational error hierarchy for Astra.
Every exception in the framework inherits from AstraError.
"""

from typing import Optional, Dict, Any
from enum import Enum


class Severity(Enum):
 """Error severity levels."""
 INFO = "info"
 WARNING = "warning"
 ERROR = "error"
 FATAL = "fatal"


class AstraError(Exception):
 """
 The base class for all errors in the Astra framework.

 AstraError provides a structured way to report failures, including
 human-readable messages, unique error codes, recovery hints,
 severity levels, and retry guidance.

 Example::

  try:
   await client.chat.send_message(jid, text)
  except MessageSendError as e:
   print(e.code)  # "E3001"
   print(e.hint)  # "Ensure the recipient JID is correct..."
   print(e.retryable) # True
   print(e.severity) # Severity.ERROR
 """
 def __init__(
  self,
  message: str,
  code: str = "E0000",
  hint: Optional[str] = None,
  severity: Severity = Severity.ERROR,
  retryable: bool = False,
  payload: Optional[Dict[str, Any]] = None,
  cause: Optional[Exception] = None
 ):
  """
  Initialize the error.

  Args:
   message: A clear description of what went wrong.
   code: A unique error code (Exxx format).
   hint: An actionable suggestion to resolve the issue.
   severity: How critical this error is.
   retryable: Whether retrying the operation may succeed.
   payload: Additional metadata for debugging.
   cause: The original exception that triggered this error.
  """
  self.message = message
  self.code = code
  self.hint = hint
  self.severity = severity
  self.retryable = retryable
  self.payload = payload or {}
  self.cause = cause

  # Build a human-friendly error string
  full_msg = f"[{self.code}] {self.message}"
  if self.hint:
   full_msg += f"\n → Hint: {self.hint}"

  super().__init__(full_msg)

 def __str__(self) -> str:
  return self.args[0]

 def __repr__(self) -> str:
  return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"

 def to_dict(self) -> dict:
  """Serialize error for logging, API responses, or telemetry."""
  return {
   "error": self.__class__.__name__,
   "code": self.code,
   "message": self.message,
   "hint": self.hint,
   "severity": self.severity.value,
   "retryable": self.retryable,
   "payload": self.payload,
  }
