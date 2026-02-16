Events (astra.events)
======================

Overview
--------

Event modules provide the filtering, dispatch and context objects used by the
application layer.

.. autoclass:: astra.events.emitter.EventEmitter
 :members:

.. autoclass:: astra.events.dispatcher.EventDispatcher
 :members:

.. automodule:: astra.events.filters
 :members:

.. autoclass:: astra.events.context.EventContext
 :members:

Example: registering an event
-----------------------------

.. code-block:: python

 from astra import Client
 from astra.events import Filters

 client = Client()

 @client.on("message", Filters.text_contains("urgent"))
 async def on_urgent(ctx):
  await ctx.reply("Received — will review asap")

Async behavior
--------------

- Dispatcher schedules handler invocations as `asyncio` tasks to avoid blocking
 the incoming event loop.
- Filters can be coroutine-backed — they are awaited during dispatch.
