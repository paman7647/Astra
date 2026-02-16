Models (astra.models)
======================

Overview
--------

Models provide typed views of bridge payloads. Main models are exposed below
and documented via autodoc for quick reference.

.. autoclass:: astra.models.message.Message
 :members:

.. autoclass:: astra.models.chat.Chat
 :members:

.. autoclass:: astra.models.user.User
 :members:

.. autoclass:: astra.models.user.JID
 :members:

Important fields
----------------

- ``Message.body`` / ``Message.text`` — message text
- ``Message.id`` / ``Message.chat_id`` — identifiers
- ``Chat.title`` / ``Chat.is_group`` — thread metadata

Example: converting a payload
-----------------------------

.. code-block:: python

 from astra.protocol.serializers import DataTransformer
 message = DataTransformer.to_message(raw_payload, client)

Async notes
-----------

- Model constructors are synchronous; hydration occurs from bridge results
 (synchronous mapping in Python after an async bridge call).
