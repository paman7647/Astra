.. _installation:

Installation
============

Astra Engine runs on **macOS, Linux, and Windows** wherever Playwright is
supported. Python **3.9 or newer** is required.

Quick install
-------------

The recommended way is to create a virtual environment and install the package
with terminal QR support:

.. code-block:: bash

 python3 -m venv .venv
 source .venv/bin/activate  # macOS / Linux
 pip install astra-engine

Install Playwright browsers
----------------------------

Astra drives a real browser under the hood. After installing the package you
need to download the browser binaries **once**:

.. code-block:: bash

 python -m playwright install

This fetches Chromium, Firefox, and WebKit. If you only need Chromium (the
default and most stable option):

.. code-block:: bash

 python -m playwright install chromium

Install from source
-------------------

For contributors or if you want to hack on Astra itself:

.. code-block:: bash

 git clone https://github.com/paman7647/Astra.git
 cd astra-engine
 python -m venv .venv && source .venv/bin/activate
 pip install -e ".[dev]"
 python -m playwright install chromium

The ``[dev]`` extra includes pytest, Sphinx, ruff, mypy, and build tools.

Dependencies
------------

.. list-table::
 :header-rows: 1

 * - Package
  - Purpose
  - Required?
 * - ``playwright``
  - Browser automation
  - Yes
 * - ``qrcode``
  - Terminal QR codes
  - Yes
 * - ``Pillow``
  - QR image rendering
  - Yes

Verifying your install
----------------------

Run a quick smoke test to make sure everything is wired up:

.. code-block:: bash

 python -c "from astra import Client; print('Astra ready')"

You should see ``Astra ready`` with no import errors.

Troubleshooting
---------------

**"Browser launch failed"**
 Make sure you ran ``python -m playwright install``. On headless Linux
 servers you may also need system libraries -- Playwright prints a helpful
 list of missing packages when this happens.

**Session lock conflicts**
 If another Astra instance is using the same ``session_id``, the browser
 profile directory will be locked. Either stop the other instance or
 choose a different ``session_id``.

Next steps
----------

Head over to :doc:`quickstart` to build your first bot in under five minutes.
