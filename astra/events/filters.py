# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

"""
This module provides the criteria (filters) used to match events
in the Astra framework.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, List, Union, Callable, Optional

class Criterion(ABC):
 """
 Base class for all event matching criteria.

 Criteria can be combined using logical operators:
 - `&` (AND)
 - `|` (OR)
 - `~` (NOT)
 """

 @abstractmethod
 async def matches(self, event: Any) -> bool:
  """Determines if the given event matches this criterion."""
  pass

 def __and__(self, other: 'Criterion') -> 'AndCriterion':
  return AndCriterion(self, other)

 def __or__(self, other: 'Criterion') -> 'OrCriterion':
  return OrCriterion(self, other)

 def __invert__(self) -> 'NotCriterion':
  return NotCriterion(self)

 # Alias for EventEmitter compatibility
 async def passes(self, event: Any) -> bool:
  return await self.matches(event)

# --- Logical Combinators ---

class AndCriterion(Criterion):
 def __init__(self, c1: Criterion, c2: Criterion):
  self.c1, self.c2 = c1, c2

 async def matches(self, event: Any) -> bool:
  return await self.c1.matches(event) and await self.c2.matches(event)

class OrCriterion(Criterion):
 def __init__(self, c1: Criterion, c2: Criterion):
  self.c1, self.c2 = c1, c2

 async def matches(self, event: Any) -> bool:
  return await self.c1.matches(event) or await self.c2.matches(event)

class NotCriterion(Criterion):
 def __init__(self, c: Criterion):
  self.c = c

 async def matches(self, event: Any) -> bool:
  return not await self.c.matches(event)

# --- Predicate Implementations ---

class ChatTypeCriterion(Criterion):
 def __init__(self, is_group: bool):
  self.is_group = is_group

 async def matches(self, event: Any) -> bool:
  # Check EventContext or raw objects
  val = getattr(event, 'is_group', None)
  return val is self.is_group

class TextMatchCriterion(Criterion):
 def __init__(self, pattern: str, exact: bool = False, ignore_case: bool = True):
  self.pattern = pattern.lower() if ignore_case else pattern
  self.exact = exact
  self.ignore_case = ignore_case

 async def matches(self, event: Any) -> bool:
  text = str(getattr(event, 'text', "")).strip()
  if self.ignore_case: text = text.lower()

  if self.exact:
   return text == self.pattern
  return self.pattern in text

class RegexCriterion(Criterion):
 def __init__(self, pattern: str, flags: int = re.IGNORECASE):
  self.regex = re.compile(pattern, flags)

 async def matches(self, event: Any) -> bool:
  text = str(getattr(event, 'text', ""))
  return bool(self.regex.search(text))

class IdentityCriterion(Criterion):
 def __init__(self, ids: Union[str, List[str]], field: str = 'chat_id'):
  self.ids = {ids} if isinstance(ids, str) else set(ids)
  self.field = field

 async def matches(self, event: Any) -> bool:
  val = getattr(event, self.field, None)
  return str(val) in self.ids

class DirectionCriterion(Criterion):
 def __init__(self, outgoing: bool):
  self.outgoing = outgoing

 async def matches(self, event: Any) -> bool:
  from_me = getattr(event, 'from_me', None)
  if from_me is None and hasattr(event, '_event'):
   from_me = getattr(event._event, 'from_me', False)
  return bool(from_me) is self.outgoing

class TypeCriterion(Criterion):
 def __init__(self, attr: str, value: Any = True):
  self.attr = attr
  self.value = value

 async def matches(self, event: Any) -> bool:
  actual = getattr(event, self.attr, None)
  if hasattr(actual, 'value'): actual = actual.value
  return actual == self.value

class CommandCriterion(Criterion):
 def __init__(self, command: str, prefixes: str = "/."):
  self.command = command
  self.prefixes = prefixes

 async def matches(self, event: Any) -> bool:
  from .context import EventContext
  if isinstance(event, EventContext):
   # 1. Check command name match
   if event.command != self.command:
    return False
   # 2. Check prefix match (if prefixes defined)
   if self.prefixes and event.prefix not in self.prefixes:
    return False
   return True
  return False

# --- Human-Friendly Namespace ---

class Filters:
 """
 Collection of event matching criteria.
 """

 # --- Direction & Identity ---
 incoming = DirectionCriterion(outgoing=False)
 outgoing = DirectionCriterion(outgoing=True)
 me = DirectionCriterion(outgoing=True)

 private = ChatTypeCriterion(is_group=False)
 group = ChatTypeCriterion(is_group=True)

 # --- Media Types ---
 media = TypeCriterion("is_media", True)
 photo = TypeCriterion("type", "image")
 video = TypeCriterion("type", "video")
 audio = TypeCriterion("type", "audio")
 voice = TypeCriterion("type", "ptt")
 document = TypeCriterion("type", "document")
 sticker = TypeCriterion("type", "sticker")
 location = TypeCriterion("type", "location")
 contact = TypeCriterion("type", "vcard")
 poll = TypeCriterion("type", "poll_creation")

 # --- Structural ---
 service = TypeCriterion("is_service", True)
 forwarded = TypeCriterion("is_forwarded", True)
 quoted = TypeCriterion("has_quoted_msg", True)

 @staticmethod
 def command(name: str, prefixes: str = "/.") -> Criterion:
  """
  Matches if the message is a specific command.

  Example:
   command("ping", ".") -> Matches ".ping"
   command(".ping")  -> Matches ".ping" (infer prefix from name)
  """
  # Surgical normalization: if name starts with a known prefix,
  # we treat that char as the only valid prefix.
  for p in prefixes:
   if name.startswith(p):
    return CommandCriterion(name[len(p):], p)

  return CommandCriterion(name, prefixes)

 @staticmethod
 def text_contains(text: str, ignore_case: bool = True) -> Criterion:
  """Matches if the message text contains the given substring."""
  return TextMatchCriterion(text, exact=False, ignore_case=ignore_case)

 @staticmethod
 def text_is(text: str, ignore_case: bool = True) -> Criterion:
  """Matches if the message text exactly matches the given string."""
  return TextMatchCriterion(text, exact=True, ignore_case=ignore_case)

 @staticmethod
 def regex(pattern: str) -> Criterion:
  """Matches message text against a regular expression."""
  return RegexCriterion(pattern)

 @staticmethod
 def chat(chat_id: Union[str, List[str]]) -> Criterion:
  """Matches events from specific chat JIDs."""
  return IdentityCriterion(chat_id, field='chat_id')

 @staticmethod
 def sender(user_id: Union[str, List[str]]) -> Criterion:
  """Matches events from specific user JIDs."""
  return IdentityCriterion(user_id, field='sender_id')

 @staticmethod
 def has_attribute(attribute: str, value: Any = True) -> Criterion:
  """Custom attribute matcher for advanced use cases."""
  return TypeCriterion(attribute, value)

 @staticmethod
 def create(func: Callable[[Any], Union[bool, Any]]) -> Criterion:
  """
  Creates a custom filter from a callable.
  """
  class CustomCriterion(Criterion):
   async def matches(self, event: Any) -> bool:
    import asyncio
    return await func(event) if asyncio.iscoroutinefunction(func) else bool(func(event))
  return CustomCriterion()
