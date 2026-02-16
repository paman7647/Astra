.. _deployment:

Deployment
==========

This page covers how to run Astra in production environments.

Running on a server
-------------------

Astra needs a browser to function, so you must install browser binaries on your
server. On headless Linux servers:

.. code-block:: bash

 pip install astra-engine
 python -m playwright install --with-deps chromium

The ``--with-deps`` flag installs required system libraries (libatk, libnss,
etc.) automatically on Debian/Ubuntu.

Always run in headless mode on servers:

.. code-block:: python

 client = Client(session_id="prod", headless=True)

Session persistence
-------------------

Authenticate **locally** first (with ``headless=False``), then copy the
``.astra_sessions/`` directory to your server. The session will be reused
without requiring another QR scan.

.. code-block:: bash

 # On your local machine
 python bot.py # scan QR, then Ctrl+C

 # Copy session to server
 scp -r .astra_sessions/ user@server:/app/.astra_sessions/

Process management
------------------

Use a process manager to keep your bot running and restart on crashes:

**systemd** (Linux):

.. code-block:: ini

 [Unit]
 Description=Astra WhatsApp Bot
 After=network.target

 [Service]
 User=astra
 WorkingDirectory=/opt/astra
 ExecStart=/opt/astra/.venv/bin/python bot.py
 Restart=always
 RestartSec=10

 [Install]
 WantedBy=multi-user.target

**Docker**:

.. code-block:: dockerfile

 FROM python:3.12-slim

 RUN pip install astra-engine && \
  python -m playwright install --with-deps chromium

 WORKDIR /app
 COPY bot.py .
 COPY .astra_sessions/ .astra_sessions/

 CMD ["python", "bot.py"]

Environment variables
---------------------

Astra reads these from the environment (or ``.env`` via ``python-dotenv``):

.. list-table::
 :header-rows: 1

 * - Variable
  - Description
  - Default
 * - ``ASTRA_SESSION``
  - Session ID
  - ``ASTRAUB``
 * - ``PHONE_NUMBER``
  - Phone for pairing auth
  - None (QR mode)
 * - ``HEADLESS``
  - Run headless (``true``/``false``)
  - ``true``

Resource requirements
---------------------

- **RAM**: ~300 MB (Chromium + WhatsApp Web)
- **CPU**: Minimal -- mostly idle between events
- **Disk**: ~200 MB for Chromium binaries + session data
- **Network**: Stable connection to WhatsApp servers
