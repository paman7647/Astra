.. _error_codes:

Error Codes
===========

Astra uses structured error codes so you always know *exactly* what went wrong
and what to do about it. Every exception is a subclass of
:class:`~astra.errors.AstraError` and carries a human-readable code, message,
hint, and retry flag.

Code format
-----------

All codes follow the pattern ``Exxxx`` where the first digit identifies the
category:

.. list-table::
 :header-rows: 1
 :widths: 15 25 60

 * - Range
  - Category
  - Description
 * - ``E1xxx``
  - Authentication
  - QR timeout, pairing failures, session problems
 * - ``E2xxx``
  - Connection
  - Browser launch, startup, bridge injection
 * - ``E3xxx``
  - Messaging
  - Send failures, poll errors, media upload
 * - ``E4xxx``
  - Groups
  - Create, invite, promote/demote, settings
 * - ``E5xxx``
  - Account
  - Profile updates, status, privacy settings
 * - ``E6xxx``
  - Media
  - Upload, download, encoding
 * - ``E7xxx``
  - Protocol
  - Bridge calls, JS execution, validation
 * - ``E8xxx``
  - Internal
  - Cache, sync engine, unhandled errors

Catching errors
---------------

You can catch specific error types:

.. code-block:: python

 from astra.errors import MessageSendError, RateLimitedError

 try:
  await client.chat.send_message(jid, "Hello")
 except RateLimitedError as e:
  print(f"[{e.code}] Rate limited. Retry: {e.retryable}")
  print(f"Hint: {e.hint}")
  await asyncio.sleep(30)
 except MessageSendError as e:
  print(f"[{e.code}] Failed: {e.message}")

Or catch the base class for a general handler:

.. code-block:: python

 from astra.errors import AstraError

 try:
  await do_something()
 except AstraError as e:
  log.error(f"[{e.code}] {e.message} | hint: {e.hint}")
  if e.retryable:
   await retry(do_something)

Common error codes
------------------

Authentication (E1xxx)
~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
 :header-rows: 1
 :widths: 10 30 30 10

 * - Code
  - Exception
  - Description
  - Retry?
 * - E1001
  - ``LoginFailedError``
  - Authentication failed
  - Yes
 * - E1002
  - ``QRTimeoutError``
  - QR code expired before scan
  - Yes
 * - E1003
  - ``PairingError``
  - Phone pairing failed
  - Yes
 * - E1004
  - ``SessionExpiredError``
  - Saved session is no longer valid
  - Yes
 * - E1006
  - ``AuthRateLimitError``
  - Too many auth attempts
  - No

Connection (E2xxx)
~~~~~~~~~~~~~~~~~~

.. list-table::
 :header-rows: 1
 :widths: 10 30 30 10

 * - Code
  - Exception
  - Description
  - Retry?
 * - E2001
  - ``BrowserStartError``
  - Browser failed to launch
  - Yes
 * - E2002
  - ``BrowserCrashError``
  - Browser process crashed
  - Yes
 * - E2003
  - ``ConnectionLostError``
  - Lost connection to browser page
  - Yes
 * - E2008
  - ``StartupError``
  - Client startup sequence failed
  - Yes

Messaging (E3xxx)
~~~~~~~~~~~~~~~~~

.. list-table::
 :header-rows: 1
 :widths: 10 30 30 10

 * - Code
  - Exception
  - Description
  - Retry?
 * - E3001
  - ``MessageSendError``
  - Message failed to send
  - Yes
 * - E3004
  - ``MediaUploadError``
  - Media attachment failed
  - Yes
 * - E3010
  - ``PollError``
  - Poll creation failed
  - No
 * - E3020
  - ``ChatOperationError``
  - General chat operation failure
  - No

Protocol (E7xxx)
~~~~~~~~~~~~~~~~

.. list-table::
 :header-rows: 1
 :widths: 10 30 30 10

 * - Code
  - Exception
  - Description
  - Retry?
 * - E7001
  - ``BridgeCallError``
  - JS bridge call failed
  - Yes
 * - E7002
  - ``MessageTimeoutError``
  - Bridge call timed out
  - Yes
 * - E7003
  - ``RateLimitedError``
  - WhatsApp rate limiting detected
  - Yes
 * - E7005
  - ``BridgeMethodNotFoundError``
  - JS method does not exist
  - No

Full reference
--------------

For the complete list of all 71 error codes, see the
`ERROR_CODES.md <https://github.com/paman7647/Astra/blob/main/ERROR_CODES.md>`_
file in the repository.

Error anatomy
-------------

Every ``AstraError`` has these attributes:

.. code-block:: python

 error.code  # "E3001"
 error.message  # "Message failed to send"
 error.hint  # "Check the JID format and your connection"
 error.severity # Severity.ERROR
 error.retryable # True
 error.cause  # Original exception, if any
 error.to_dict() # Serializable dict for logging / APIs
