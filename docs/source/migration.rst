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

General migration tips
----------------------

1. Check the `CHANGELOG <https://github.com/paman7647/Astra/blob/dev/CHANGELOG.md>`_
 for the full list of changes.
2. Run ``python -c "from astra import Client"`` to check basic imports.
3. Search your code for deprecated patterns listed above.
4. Run your test suite and fix any ``ImportError`` or ``AttributeError`` issues.
