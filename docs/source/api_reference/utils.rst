Utilities (astra.utils)
=======================

Overview
--------

Utility modules include helpers for logging, QR rendering, and small adapters
used by higher-level APIs.

Notable utilities
-----------------

- QR helpers (terminal rendering)
- Small conversion helpers used by the bridge serializers

Utility modules (manual reference)
----------------------------------

The `astra.utils` package contains small helpers used across the framework.
These modules are lightweight and are intentionally documented here without
`autodoc` to avoid importing runtime-only helpers during the doc build.

`HealthMonitor` (health.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Purpose: aggregate component health (browser, tasks, gateway) into a
 single report.
- Main API:
 - `HealthMonitor.consolidate(client_state, browser_health, tasks_health, gateway_ready)` — returns a dictionary summary.

Example:

.. code-block:: python

 report = HealthMonitor.consolidate("READY", {"engine_active": True}, {"running": 5}, True)

Media helpers (media.py)
~~~~~~~~~~~~~~~~~~~~~~~~

- Purpose: small helpers around media handling and MIME/type inference used
 by the `MediaMethods` layer. These helpers are internal and have thin
 wrappers in the public `client.media` API.

Retry utilities (retry.py, retry_handler.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Purpose: provide retry/backoff strategies and a small retry handler used
 across network and protocol operations.
- Key concepts: exponential backoff, jitter, configurable max attempts.

Task supervisor (task_supervisor.py)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Purpose: helper for supervising background `asyncio` tasks and graceful
 shutdown. Used to centralize lifecycle handling for long-running workers.

Notes
~~~~~

- These utilities are internal implementation details and are intentionally
 documented with short summaries to avoid importing package modules during
 Sphinx builds (some utilities reference runtime-only objects). If you
 need a full programmatic API reference for any of these, I can generate
 small wrapper pages that import them in a safe mocked environment.

Example
-------

.. code-block:: python

 from astra.utils import logging as astra_log
 astra_log.setup(level="INFO")
