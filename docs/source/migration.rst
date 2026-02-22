.. _migration:

Migration Guide
===============

This page helps you migrate between Astra versions when breaking changes occur.

From v0.0.1b3 to v0.0.1b4
---------------------------

**Message Attributes**

The ``has_media`` property has been deprecated and replaced with ``is_media`` for 
better consistency across models.

.. code-block:: diff

 - if message.has_media:
 + if message.is_media:

**Quoted Media**

The ``quoted`` property now accurately detects media types (stickers, images, video) 
even when messages are received as skeletal payloads.

From pre-release to v0.0.1
---------------------------

The initial public release introduces several changes from internal builds:

**Import paths**

.. code-block:: diff

 - from astra.client.astra_client import Client
 + from astra import Client, Filters

**Error handling**

Bare ``except Exception`` blocks have been replaced with typed exceptions:

.. code-block:: diff

 - except Exception as e:
 -  print(f"Failed: {e}")
 + from astra.errors import MessageSendError
 + except MessageSendError as e:
 +  print(f"[{e.code}] {e.hint}")

**Authentication**

Phone pairing is now a constructor argument, not a separate method:

.. code-block:: diff

 - client = Client()
 - client.set_pairing_phone("+91...")
 + client = Client(phone="+91...")

**Context manager**

The recommended pattern is now ``async with``:

.. code-block:: diff

 - client = Client()
 - await client.start()
 - # ... your code ...
 - await client.stop()
 + async with Client(session_id="bot") as client:
 +  # ... your code ...

From v0.0.2b5 through v0.0.2b8
------------------------------

These rapid beta releases focused on stability, but a few API
additions and behaviour changes may affect your code:

* **New shortcut methods on ``Client``**: ``send_image``, ``send_video``,
  ``send_audio``, ``send_sticker`` and ``delete_message`` are now
  available directly on the client object. Existing code using
  ``client.chat.send_message`` continues to work, but you can replace

  .. code-block:: python

    await client.chat.send_message(jid, "hi")
  
  with
  
  .. code-block:: python

    await client.send_message(jid, "hi")

* **Force fetch parameter**: ``client.fetch_messages`` and
  ``client.chat.fetch_messages`` now accept a ``force=True`` keyword to
  bypass the local cache. If you were manually clearing the cache to get
  fresh data, you can drop that logic.

* **Behaviour of ``.history`` and ``.fetch`` in plugins**: calls made
  without quoting a message now return the last 10 messages rather than
  raising a ``TypeError``. If you relied on the old error, wrap your call
  with ``try/except``.

* **Deprecation of ``has_media`` attribute** (continued from 0.0.1b4). Use
  ``is_media`` throughout.

* **Logging changes**: Plugin authors can now call ``Astra.log(...)`` from
  within JS-executed code. See the "Bridge" section of
  :doc:`design_and_architecture` for details.

* **Plugin import convenience**: command modules may now use ``from . import *``
  to automatically import public symbols such as ``Client`` and
  ``Filters``. This simplifies third-party plugin templates.

* **Cache behaviour**: By default ``use_cache`` is ``True``; you may set it
  to ``False`` when creating a client if you want every fetch to hit the
  bridge.

These changes are additive and backwards-compatible in most cases, but
we recommend running your test suite and watching for ``AttributeError``
or ``TypeError`` during the upgrade.

General migration tips
----------------------

1. Check the `CHANGELOG <https://github.com/paman7647/Astra/blob/dev/CHANGELOG.md>`_
 for the full list of changes.
2. Run ``python -c "from astra import Client"`` to check basic imports.
3. Search your code for deprecated patterns listed above.
4. Run your test suite and fix any ``ImportError`` or ``AttributeError`` issues.
