.. _index:

Astra Engine
============

**A high-performance WhatsApp Web automation framework for Python.**

Astra Engine is designed to make building bots and integrations on WhatsApp
Web straightforward without having to interact with the browser directly.
It encapsulates Playwright, the WhatsApp Web bridge, and a rich set of
helpers so you can focus on your business logic rather than scraping or
reverse engineering the client.

Astra Engine provides a clean, async Python interface to WhatsApp Web.
It handles authentication, message sending, group management, media, and
real-time event listening -- all through a single ``Client`` object that
manages the underlying browser session for you.

.. image:: _static/AstraClient.png
 :alt: Astra Client Interface
 :width: 600
 :align: center

.. code-block:: python

 import asyncio
 from astra import Client, Filters

 async def main():
  async with Client(session_id="mybot", phone="+911234567890") as client:

   @client.on_message(Filters.command(".ping"))
   async def on_ping(msg):
    await msg.respond("Pong!")

   await client.run_forever()

 asyncio.run(main())

Why Astra?
----------

- **One import, full control.** Everything you need lives under ``from astra import Client``.
- **Async from the ground up.** Built on ``asyncio`` and Playwright -- no blocking calls.
- **Typed errors.** 71 error codes across 8 categories, so you know *exactly* what went wrong.
- **Self-healing.** Automatic bridge recovery, reconnection with exponential backoff, and stall detection.
- **Session persistence.** Authenticate once, run headless forever.

.. toctree::
 :maxdepth: 2
 :caption: Getting Started

 introduction
 installation
 quickstart

.. toctree::
 :maxdepth: 2
 :caption: User Guide

 core_concepts
 usage
 commands_and_handlers
 filters
 event_system
 error_codes
 examples
 cookbook

.. toctree::
 :maxdepth: 2
 :caption: Architecture

 design_and_architecture
 performance
 security

.. toctree::
 :maxdepth: 2
 :caption: Operations

 deployment
 migration
 testing
 faq
 troubleshooting

.. toctree::
 :maxdepth: 2
 :caption: Reference

 api_reference/index
 developer_guide
 readthedocs
 author
 license

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
