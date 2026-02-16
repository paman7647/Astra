Connection (astra.connection)
=============================

Overview
--------

Connection components manage the browser process and Playwright context. They
are responsible for session locking, crash detection and page state monitoring.

BrowserController
-----------------

.. autoclass:: astra.connection.browser_manager.BrowserController
 :members:

Page monitor & retry
--------------------

.. autoclass:: astra.connection.page_controller.PageMonitor
 :members:

.. autoclass:: astra.connection.reconnect_policy.RetryStrategy
 :members:

Usage example
-------------

.. code-block:: python

 controller = BrowserController(session_path="./.sessions/default", headless=True)
 page = await controller.start()
 state = await controller.get_state()

Async notes
-----------

- Browser start/stop operations are async and must be awaited.
- Page interactions use Playwright's async API (``await page.evaluate(...)``).
