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
- Handler functions should be `async def` unless performing trivial sync work.
