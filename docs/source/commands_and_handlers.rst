.. _commands_and_handlers:

Commands and Handlers
=====================

Astra uses a decorator pattern to register message handlers. Each handler is
an async function that runs when an incoming message matches a filter.

Registering a handler
---------------------

Use the ``@client.on_message()`` decorator with a filter:

.. code-block:: python

 from astra import Client, Filters

 async with Client(session_id="bot") as client:

  @client.on_message(Filters.command(".ping"))
  async def ping(msg):
   await msg.respond("Pong!")

  @client.on_message(Filters.command(".help"))
  async def help_cmd(msg):
   await msg.respond(
    "*Commands*\n"
    "`.ping` -- check if bot is alive\n"
    "`.echo <text>` -- echo your text back\n"
    "`.help` -- show this message"
   )

  await client.run_forever()

Automated Plugin Loading
------------------------

For complex projects, you can organize your handlers into a directory (e.g., ``commands/``)
and load them all at once:

.. code-block:: python

 import os
 from astra import Client

 async with Client(session_id="bot") as client:
  # Load all plugin modules in the 'commands' folder
  client.load_plugins("commands")
  
  await client.run_forever()

In your plugin files, use the class-level ``@Client.on_message`` decorator:

.. code-block:: python

 from astra import Client, Filters

 @Client.on_message(Filters.command(".hello"))
 async def hello(client, msg):
  await msg.respond("Hello from a plugin!")

The ``msg`` parameter
---------------------

Every handler receives a ``Message`` object with these useful attributes:

.. list-table::
 :header-rows: 1

 * - Attribute
  - Type
  - Description
 * - ``msg.text``
  - ``str``
  - Raw message body
 * - ``msg.chat_id``
  - ``str``
  - JID of the chat (e.g. ``123@c.us``)
 * - ``msg.sender``
  - ``str``
  - JID of the sender
 * - ``msg.is_group``
  - ``bool``
  - Whether this is a group message
 * - ``msg.quoted``
  - ``Message | None``
  - The message being replied to, if any

And these helper methods:

.. code-block:: python

 await msg.respond("text")  # Send in the same chat
 await msg.reply("text")   # Quote-reply the original message
 await msg.react("👍")   # React with an emoji
 await msg.delete(for_everyone=True) # Delete the message

Building a command system
-------------------------

A practical pattern for bots with many commands:

.. code-block:: python

 @client.on_message(Filters.command(".echo"))
 async def echo(msg):
  # Strip the command prefix to get the argument
  text = msg.text.replace(".echo", "", 1).strip()
  if not text:
   await msg.respond("Usage: `.echo <text>`")
   return
  await msg.reply(text)

 @client.on_message(Filters.command(".react"))
 async def react(msg):
  emoji = msg.text.replace(".react", "", 1).strip() or "👍"
  if msg.quoted:
   await msg.quoted.react(emoji)
  else:
   await msg.respond("Reply to a message with `.react <emoji>`")

 @client.on_message(Filters.command(".delete"))
 async def delete(msg):
  if msg.quoted:
   await msg.quoted.delete(for_everyone=True)
   await msg.delete(for_everyone=True)

Multiple filters
-----------------

You can register multiple handlers -- they are checked in registration order
and the first matching handler runs:

.. code-block:: python

 @client.on_message(Filters.command(".admin"))
 async def admin_only(msg):
  """Only fires if message starts with .admin"""
  ...

 @client.on_message(Filters.text_contains("hello"))
 async def greet(msg):
  """Fires for any message containing 'hello'"""
  await msg.respond("Hey!")

Error handling in handlers
--------------------------

If a handler raises an exception, Astra logs it but keeps running. For
critical operations, wrap your logic in try/except:

.. code-block:: python

 from astra.errors import MessageSendError

 @client.on_message(Filters.command(".send"))
 async def send(msg):
  try:
   await client.chat.send_message("target@c.us", "Hello")
   await msg.respond("Sent!")
  except MessageSendError as e:
   await msg.respond(f"Failed: {e.hint}")
