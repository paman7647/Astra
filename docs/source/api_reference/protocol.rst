Protocol (astra.protocol)
=========================

Overview
--------

The protocol layer is the bridge between Python and the injected JavaScript
engine running inside the browser page. It exposes two main primitives:

.. autoclass:: astra.protocol.gateway.ProtocolBridge
 :members:

.. autoclass:: astra.protocol.actions.EngineAPI
 :members:

Public highlights
-----------------

- ``ProtocolBridge.connect()`` — inject engine and expose uplink
- ``ProtocolBridge.call(method, params)`` — remote call to JS engine
- ``EngineAPI.send_text`` / ``send_media`` / ``get_chats`` etc.

Example
-------

.. code-block:: python

 bridge = ProtocolBridge()
 await bridge.connect()
 result = await bridge.call('getChats')

Notes
-----

- Bridge calls are proxied to the JS engine and return serializable JSON-like
 results. ``DataTransformer`` maps the payloads into Python models.
- Call timeouts and progress callbacks are supported by ``ProtocolBridge``.
