.. _troubleshooting:

Troubleshooting
===============

This page collects the most common problems you'll encounter while using
Astra and practical steps to resolve them.

Session failures
----------------

* **`LoginFailedError` on every start**: your stored session data may be
  corrupt (usually after an excessive manual browser clean). Delete the
  ``.astra_sessions/<session_id>`` directory or call ``await client.logout()``
  once, then re-authenticate with QR or pairing code.

* **`ConnectionLostError` followed by `BrowserCrashError`**: the underlying
  Playwright browser crashed. This can happen on low-memory systems. Try
  reducing the number of concurrent clients or upgrade to a newer Playwright
  version. Use ``client.sync_engine.get_diagnostics()`` to see crash counts.

* **`ProtocolError: method not found`**: indicates WhatsApp Web updated and
  Astra's injected JS is out of sync. Upgrade to the latest package; if the
  error persists, file an issue with your WA Web version.

Error codes and exceptions
--------------------------

All server-side issues are surfaced as typed exceptions. Inspect the
``code`` attribute to diagnose:

.. code-block:: python

 from astra.errors import AstraError

 try:
  await client.chat.send_message(jid, "hello")
 except AstraError as e:
  print("Error code", e.code)
  if e.retryable:
   print("This operation can be retried")

Look up the code in :doc:`error_codes` for more details. The
repository also contains ``ERROR_CODES.md`` which is kept in sync with
code definitions.

Debug logging
-------------

Set the log level to ``DEBUG`` when creating the client to see bridge
traffic and internal decisions.

.. code-block:: python

 client = Client(log_level=logging.DEBUG)

Logs are emitted using the ``Astra`` logger namespace. You can configure
handlers the usual way:

.. code-block:: python

 import logging

 handler = logging.FileHandler("astra.log")
 logging.getLogger("Astra").addHandler(handler)

Bridge diagnostics
------------------

Use the exposed diagnostics methods to inspect the current session state:

.. code-block:: python

 print(await client.api.getBridgeStats())
 print(await client.sync_engine.get_diagnostics())

These methods are useful when opening issues or debugging connection stalls.

Playwright issues
-----------------

Astra packages ``playwright`` as a dependency, but the browser binaries are
installed separately. If you see an error like ``Could not find chromium
binary``, simply run:

.. code-block:: bash

 python -m playwright install chromium

On Linux servers you may also need the following system libraries (Playwright
prints them when missing):

* libcairo2
* libatk1.0-0
* libgtk-3-0
* libx11-xcb1
* libnss3

Refer to the Playwright documentation for details.

Need more help?
----------------

If you're stuck, the best place to ask is the project's issue tracker. When
opening a ticket, include:

* Astra version (``print(client.__version__)``)
* WhatsApp Web version (shown in browser console or diagnostics)
* Full stack trace
* The output of ``print(await client.sync_engine.get_diagnostics())``

That information will help maintainers reproduce and resolve the problem
faster.
