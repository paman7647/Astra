.. _performance:

Performance
===========

Astra is designed to be lightweight and efficient. This page covers what to
expect and how to tune things.

Resource footprint
------------------

A typical Astra instance uses:

- **~300 MB RAM** -- mostly the Chromium browser with WhatsApp Web loaded.
- **Minimal CPU** -- near zero when idle; brief spikes during message processing.
- **~200 MB disk** -- Chromium binaries (~150 MB) plus session/cache data.

These numbers stay roughly constant regardless of how many handlers you register.

Startup time
------------

Cold start (first run, no session): **8-15 seconds** including browser launch,
navigation to WhatsApp Web, and bridge injection.

Warm start (existing session): **5-10 seconds** since authentication is skipped.

The connected banner appears once the WA version is detected (up to 20 seconds
after auth completes).

Async performance
-----------------

All Astra operations are async. This means:

- Multiple handlers can run concurrently without blocking each other.
- You can ``await`` multiple operations in parallel with ``asyncio.gather()``.
- The event loop stays responsive even during long-running operations.

.. code-block:: python

 # Send to multiple chats concurrently
 import asyncio

 jids = ["111@c.us", "222@c.us", "333@c.us"]
 await asyncio.gather(*(
  client.chat.send_message(jid, "Broadcast!")
  for jid in jids
 ))

Caching
-------

Astra maintains a local SQLite cache of chats and contacts. This reduces
bridge calls and speeds up repeated lookups. The cache is synced automatically
by the SyncEngine.

You can inspect cache stats:

.. code-block:: python

 stats = client.store.get_stats()
 # {'chats': 145, 'contacts': 479, 'messages': 20, 'db_size_kb': 256}

Tuning tips
-----------

- **Headless mode** uses slightly less memory than headful mode.
- **Increase ``SYNC_HEARTBEAT_INTERVAL``** (in ``constants.py``) if you want
 less frequent health checks in low-traffic scenarios.
- **Use ``uvloop``** for a faster asyncio event loop:

 .. code-block:: python

  import uvloop
  uvloop.install()
