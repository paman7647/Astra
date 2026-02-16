# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import re
from typing import Any, List
from ..errors.validation_errors import InvalidInputError

class SchemaValidator:
 """Utility for enforcing structural integrity on protocol inputs."""

 JID_REGEX = re.compile(r"^[a-zA-Z0-9.\-_]+@([a-zA-Z0-9\-_]+\.)*[a-zA-Z0-9\-_]+$")

 @classmethod
 def validate_jid(cls, jid: str):
  if not isinstance(jid, str) or not cls.JID_REGEX.match(jid):
   raise InvalidInputError(f"Malformed JID: {jid}")

 @classmethod
 def validate_text(cls, text: str):
  if not isinstance(text, str) or not text.strip():
   raise InvalidInputError("Text content cannot be null or empty.")

 @classmethod
 def ensure_keys(cls, data: dict, required: List[str]):
  missing = [k for k in required if k not in data]
  if missing:
   raise InvalidInputError(f"Buffer missing required keys: {missing}")
