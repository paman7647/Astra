.. _design_and_architecture:

Design and Architecture
=======================

This page goes deeper into how Astra is structured internally. If you just
want to use the library, :doc:`core_concepts` is enough. This page is for
contributors and people who want to understand the design decisions.

Layer diagram
-------------

.. code-block:: text

 +---------------------------------------------------+
 | Your application (app.py / bot.py)    |
 +---------------------------------------------------+
 | astra.Client          |
 | .chat .group .account (method mixins)  |
 +---------------------------------------------------+
 | astra.protocol.ProtocolBridge (gateway.py)  |
 | - call() - ensure_bridge() - diagnostics  |
 +---------------------------------------------------+
 | astra.core.bridge.* (domain bridges)   |
 | chat.py group.py media.py account.py ... |
 +---------------------------------------------------+
 | astra.protocol.js_engine (injected JS)   |
 +---------------------------------------------------+
 | Playwright (page.evaluate)      |
 +---------------------------------------------------+
 | Chromium browser --> WhatsApp Web servers  |
 +---------------------------------------------------+

Module breakdown
----------------

**astra.client**
 The public-facing ``Client`` class and its supporting infrastructure:

 - ``client.py`` -- the main Client class with ``start()``, ``stop()``,
  ``run_forever()``, and the startup banner.
 - ``authenticator.py`` -- QR and phone-pairing authentication flow.
 - ``sync_engine.py`` -- background heartbeat, stall detection, reconnection.
 - ``lifecycle.py`` -- state machine (OFFLINE, STARTING, READY, etc.).
 - ``session_store.py`` -- cookie and local-storage persistence.
 - ``methods/`` -- chat, group, account method mixins.

**astra.protocol**
 The transport layer between Python and JavaScript:

 - ``gateway.py`` -- ``ProtocolBridge.call()`` with automatic retry,
  error classification, and self-healing.
 - ``js_engine.py`` -- the JavaScript source injected into WhatsApp Web.
 - ``validators.py`` -- JID and input validation.

**astra.core.bridge**
 Domain-specific bridges that translate high-level Python calls into
 specific JS method invocations:

 - ``chat.py``, ``group.py``, ``media.py``, ``account.py``,
  ``contact.py``, ``privacy.py``, ``status.py``, ``diagnostic.py``

**astra.errors**
 Structured error handling:

 - ``codes.py`` -- 71 error codes in 8 categories.
 - ``base.py`` -- ``AstraError`` with severity, retryable, cause, to_dict.
 - ``exceptions.py`` -- 40+ typed exception classes.

**astra.events**
 The event pipeline:

 - ``dispatcher.py`` -- routes browser events to registered handlers.
 - ``emitter.py`` -- fire-and-forget event emission.
 - ``filters.py`` -- composable message matchers (command, regex, etc.).
 - ``context.py`` -- ``EventContext`` wrapping each incoming event.

**astra.models**
 Data classes representing WhatsApp entities:

 - ``message.py`` -- ``Message`` with reply, react, delete helpers.
 - ``chat.py`` -- ``Chat`` with title, participants, metadata.
 - ``user.py`` -- ``User`` and ``JID``.
 - ``enums.py`` -- ``ClientStatus`` and other enumerations.

**astra.connection**
 Browser lifecycle:

 - ``browser_manager.py`` -- launch, lock, crash recovery, console relay.
 - ``page_controller.py`` -- navigation, cache clearing, page health.
 - ``reconnect_policy.py`` -- exponential backoff with jitter.

Error classification in the gateway
------------------------------------

When a JS bridge call fails, the gateway doesn't just re-raise the raw
Playwright error. It classifies it:

.. code-block:: text

 JS exception text   --> Python exception
 -------------------------------------------------------
 "method not found"   --> BridgeMethodNotFoundError
 "timeout"     --> MessageTimeoutError
 "rate" / "too many"   --> RateLimitedError
 "target closed" / "page"  --> ConnectionLostError
 anything else    --> BridgeCallError

This means your code can catch specific errors and react appropriately.

Self-healing bridge
-------------------

The bridge connection can break for several reasons: page reload, navigation,
Chromium garbage collection. Astra handles this automatically:

1. A ``call()`` fails with a recoverable error.
2. The gateway calls ``ensure_bridge()`` to check if the JS engine is alive.
3. If not, it re-injects the engine and retries the call once.
4. If that also fails, it raises a typed exception.

The SyncEngine adds another layer: if no events arrive for 90 seconds, it
assumes the bridge is stale and triggers a recovery cascade (re-bind listeners,
re-init Store, full restart).

Design principles
-----------------

**No protocol RE.**
 Astra never reverse-engineers the WhatsApp binary protocol. It drives the
 official web client, which means it stays compatible as WhatsApp updates.

**Fail loud, fail typed.**
 Every failure path has a named exception with a code, hint, and retry flag.
 No bare ``except Exception`` blocks in the library.

**Async all the way.**
 Every I/O operation is ``async``. No sync wrappers, no threading hacks.

**Single source of truth.**
 Error codes live in ``codes.py``. Version lives in ``pyproject.toml``
 and is synced to ``__init__.__version__``.