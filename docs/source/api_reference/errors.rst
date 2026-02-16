Errors (astra.errors)
======================

Overview
--------

Centralized exception types used across the Astra codebase. All exceptions
inherit from :py:class:`astra.errors.base.AstraError` and include ``code`` and
``hint`` to make diagnostics actionable.

.. automodule:: astra.errors
 :members: AstraError, Severity, ErrorCode

Common exceptions
-----------------

- ``LoginFailedError`` — login/pairing failed or timed out
- ``SessionExpiredError`` — saved session is invalid
- ``BrowserLimitError`` — profile locked by another process
- ``ConnectionLostError`` — browser or page disconnected
- ``MessageSendError`` — cannot deliver a message

Example: graceful handling
--------------------------

.. code-block:: python

 from astra.errors import MessageSendError

 try:
  await client.send_message(jid, "ping")
 except MessageSendError as e:
  # inform user and retry
  logger.warning(e)
