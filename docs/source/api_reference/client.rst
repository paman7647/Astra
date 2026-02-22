Client (astra.client)
======================

Overview
--------

`Client` is the main entrypoint for Astra. It manages lifecycle, session
persistence, the bridge to WhatsApp Web, and exposes mixin-based behavioral
APIs (`chat`, `group`, `media`, `account`).

.. autoclass:: astra.client.client.Client
 :members:
 :undoc-members:
 :show-inheritance:

Conversation helper
-------------------

.. autoclass:: astra.client.conversation.Conversation
 :members:

Quick usage example
-------------------

.. code-block:: python

 from astra import Client, Filters

 client = Client(session_id="bot-01")

 @client.on("message", Filters.command("hello"))
 async def hello(ctx):
  await ctx.reply("Hi — I'm Astra")

Notes on async/await
--------------------

- ``start`` / ``stop`` / engine calls are asynchronous — call them from an
  async context or use ``run_forever()`` for a simple blocking loop.
- Handler functions should be ``async def`` unless performing trivial sync work.

Advanced snippet: waiting for a result
--------------------------------------

Sometimes you need to wait for a particular event outside of a handler. Use
``client.wait_for`` combined with filters:

.. code-block:: python

 async def wait_for_reply(client):
  # send a message and wait for the first reply in the same chat
  sent = await client.chat.send_message(jid, "what's up?")
  reply = await client.wait_for(
    "message",
    criteria=(Filters.reply & Filters.chat_id(jid)),
    timeout=30,
  )
  return reply

Decorator shorthands
--------------------

Client offers convenience decorators for common events, e.g. ``on_message``
``on_reaction`` and ``on_ready``; they can be used at the class level to
register global handlers in plugin modules.

.. code-block:: python

 from astra import Client

 @Client.on_message(Filters.command(".announce"))
 async def announce(msg):
  ...

