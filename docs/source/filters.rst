.. _filters:

Filters
=======

Filters control which messages trigger which handlers. They are composable,
reusable predicates that you pass to ``@client.on_message()``.

Built-in filters
----------------

.. list-table::
 :header-rows: 1
 :widths: 35 65

 * - Filter
  - Matches when...
 * - ``Filters.command(".ping")``
  - Message starts with ``.ping``
 * - ``Filters.text_contains("hello")``
  - Message body contains ``hello`` (case-insensitive)
 * - ``Filters.regex(r"\d{6}")``
  - Message matches the regular expression
 * - ``Filters.from_me``
  - Message was sent by the authenticated user
 * - ``Filters.is_group``
  - Message came from a group chat
 * - ``Filters.is_private``
  - Message came from a 1-on-1 chat
 * - ``Filters.media``
  - Message contains media (image, video, document)
 * - ``Filters.all``
  - Matches every message (catch-all)

Using filters
-------------

Pass a filter as the argument to ``@client.on_message()``:

.. code-block:: python

 from astra import Filters

 @client.on_message(Filters.command(".help"))
 async def help_cmd(msg):
  await msg.respond("Here's the help text...")

 @client.on_message(Filters.text_contains("thanks"))
 async def thanks(msg):
  await msg.react("❤️")

Combining filters
-----------------

Filters can be combined with ``&`` (AND), ``|`` (OR), and ``~`` (NOT):

.. code-block:: python

 # Only group messages that start with .admin
 @client.on_message(Filters.is_group & Filters.command(".admin"))
 async def admin_in_group(msg):
  ...

 # Private messages OR messages from me
 @client.on_message(Filters.is_private | Filters.from_me)
 async def private_or_self(msg):
  ...

 # Any message that is NOT from me
 @client.on_message(~Filters.from_me)
 async def from_others(msg):
  ...

Command filter details
----------------------

``Filters.command(prefix)`` checks if the message text starts with the given
prefix string. It is case-sensitive and matches from the beginning:

.. code-block:: python

 Filters.command(".ping") # matches ".ping", ".ping extra args"
 Filters.command("!ban")  # matches "!ban user123"

To extract the argument after the command:

.. code-block:: python

 @client.on_message(Filters.command(".say"))
 async def say(msg):
  # msg.text is ".say Hello world"
  args = msg.text.split(None, 1)
  text = args[1] if len(args) > 1 else ""
  await msg.respond(text)

Regex filter
------------

``Filters.regex(pattern)`` compiles a regular expression and matches it
against the full message body:

.. code-block:: python

 import re

 @client.on_message(Filters.regex(r"(?i)good\s*(morning|evening)"))
 async def greeting(msg):
  await msg.respond("Hey, good to see you!")

Catch-all
---------

``Filters.all`` matches every single message. Useful for logging:

.. code-block:: python

 @client.on_message(Filters.all)
 async def log_all(msg):
  print(f"[{msg.chat_id}] {msg.sender}: {msg.text}")
