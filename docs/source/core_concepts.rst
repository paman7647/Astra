.. _core_concepts:

Core Concepts
=============

This page explains the mental model behind Astra: how the pieces fit together,
what happens when you call ``client.start()``, and why things are designed the
way they are.

The Client lifecycle
--------------------

Every Astra program revolves around a single :class:`~astra.client.client.Client`
instance. The client moves through a predictable set of states:

.. code-block:: text

 OFFLINE --> STARTING --> AUTHENTICATING --> READY
              |
             SHUTTING_DOWN

1. **OFFLINE** -- the client object exists but nothing is running.
2. **STARTING** -- the browser is launching, the bridge is being injected.
3. **AUTHENTICATING** -- waiting for QR scan or phone pairing.
4. **READY** -- fully connected. Events flow, commands work.
5. **SHUTTING_DOWN** -- browser and resources are being released.

You can check the current state at any time with ``client.status``.

The Protocol Bridge
-------------------

Astra does not speak the WhatsApp protocol directly. Instead it:

1. Opens WhatsApp Web in a real Chromium browser (via Playwright).
2. Injects a JavaScript engine (``AstraEngine``) into the page.
3. Communicates with that engine through Playwright's ``page.evaluate()`` calls.

This means Astra always speaks to the *same* WhatsApp Web code that your browser
does -- no reverse engineering of encrypted protocols.

.. code-block:: text

 Python (your code)
  |
  v
 Client --> ProtocolBridge --> page.evaluate()
          |
          v
         WhatsApp Web (JS)
          |
          v
         WhatsApp servers

The bridge is self-healing: if the page reloads or the JS context is lost,
Astra re-injects the engine automatically.

Sessions
--------

When you authenticate for the first time, WhatsApp creates a *linked device*
entry on your phone. Astra persists this session on disk (in
``.astra_sessions/<session_id>/``) so you can restart without scanning again.

Each session is identified by its ``session_id`` string. You can run multiple
bots on the same machine by using different session IDs:

.. code-block:: python

 bot_a = Client(session_id="personal")
 bot_b = Client(session_id="business")

The SyncEngine
--------------

After authentication, the **SyncEngine** runs in the background and handles:

- **Heartbeats** -- periodic checks that the bridge is still alive.
- **Stall detection** -- if no events arrive for 90 seconds, Astra re-binds
 listeners and, if needed, restarts the bridge.
- **Cache synchronization** -- keeping a local SQLite cache of chats and contacts
 in sync with the browser.

You rarely interact with the SyncEngine directly, but you can inspect its
diagnostics at any time:

.. code-block:: python

 diag = client.sync_engine.get_diagnostics()
 print(diag) # uptime, WA version, heartbeat counts, etc.

Events and handlers
-------------------

Astra uses a decorator-based event system. You register handlers on the
client and they fire whenever a matching event arrives:

.. code-block:: python

 @client.on_message(Filters.text_contains("hello"))
 async def greet(msg):
  await msg.reply("Hey there!")

The event pipeline:

1. WhatsApp Web fires a JS event (new message, status change, etc.).
2. The bridge forwards it to Python via an exposed callback.
3. The EventDispatcher matches it against registered filters.
4. Your handler function runs with the matched event context.

See :doc:`event_system` and :doc:`filters` for the full story.

Error model
-----------

Every error Astra raises is a subclass of :class:`~astra.errors.AstraError`.
Each exception carries:

- ``code`` -- a structured code like ``E3001`` (message send failed).
- ``hint`` -- a human-readable suggestion for fixing the problem.
- ``retryable`` -- whether the operation can be safely retried.
- ``severity`` -- ``INFO``, ``WARNING``, ``ERROR``, or ``FATAL``.

.. code-block:: python

 from astra.errors import MessageSendError

 try:
  await client.chat.send_message(jid, "Hello")
 except MessageSendError as e:
  print(e.code, e.hint, e.retryable)

See :doc:`error_codes` for the complete catalogue.

The context manager
-------------------

The cleanest way to use Astra is as an ``async with`` block. This ensures
the browser is always closed, even if your code crashes:

.. code-block:: python

 async with Client(session_id="demo") as client:
  # client.start() has been called for you
  await client.run_forever()
 # client.stop() is called automatically here
