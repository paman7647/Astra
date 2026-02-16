.. _event_system:

Event System
============

Astra's event system lets you react to things that happen in WhatsApp: new
messages, group changes, connection state transitions, and more.

How events flow
---------------

.. code-block:: text

 WhatsApp Web (browser)
  | JS event fires
  v
 AstraEngine (injected JS)
  | Serializes event data
  v
 ProtocolBridge (Python)
  | Deserializes into model objects
  v
 EventDispatcher
  | Matches against registered filters
  v
 Your handler function

Registering event handlers
--------------------------

The most common way is with ``@client.on_message()``:

.. code-block:: python

 @client.on_message(Filters.command(".ping"))
 async def on_ping(msg):
  await msg.respond("Pong!")

For lower-level events, use ``@client.on(event_name)``:

.. code-block:: python

 @client.on("ready")
 async def on_ready():
  print("Client is connected and ready!")

 @client.on("disconnected")
 async def on_disconnect():
  print("Connection lost")

Available events
----------------

.. list-table::
 :header-rows: 1
 :widths: 25 75

 * - Event
  - Description
 * - ``message``
  - A new message was received
 * - ``ready``
  - Client is fully connected and authenticated
 * - ``disconnected``
  - Connection to WhatsApp was lost
 * - ``sync_recovered``
  - Bridge recovered after a stall
 * - ``sync_failed``
  - Recovery failed after max attempts
 * - ``bridge_reinjected``
  - JS engine was re-injected after a crash

Programmatic listeners
----------------------

You can also add listeners without decorators, which is useful for dynamic
registration:

.. code-block:: python

 async def my_handler(msg):
  await msg.respond("Got it!")

 client.events.on("message", my_handler)

 # Remove later
 client.events.off("message", my_handler)

The EventEmitter
----------------

Under the hood, ``client.events`` is an :class:`~astra.events.emitter.EventEmitter`.
It supports:

- ``on(event, handler)`` -- register a persistent handler
- ``once(event, handler)`` -- register a one-shot handler
- ``off(event, handler)`` -- remove a handler
- ``emit(event, data)`` -- fire an event (used internally)

Handler execution
-----------------

- Handlers are async functions and run concurrently.
- If a handler raises an exception, Astra logs it and continues processing
 other handlers -- one bad handler does not crash the bot.
- Handlers run in registration order for deterministic behavior.
