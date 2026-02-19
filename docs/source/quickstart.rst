.. _quickstart:

Quick Start
===========

This page gets you from zero to a working WhatsApp bot in about five minutes.

Prerequisites
-------------

Make sure you have completed the :doc:`installation` steps -- in particular
``pip install astra-engine`` and ``python -m playwright install chromium``.

Your first bot
--------------

Create a file called ``bot.py``:

.. code-block:: python

 import asyncio
 from astra import Client, Filters

 async def main():
  # session_id saves your auth so you only scan QR once
  async with Client(
   session_id="mybot",
   headless=False   # set True after first auth
  ) as client:

   @client.on_message(Filters.command(".ping"))
   async def ping(msg):
    await msg.respond("Pong!")

   @client.on_message(Filters.command(".echo"))
   async def echo(msg):
    text = msg.text.replace(".echo", "").strip()
    await msg.reply(text or "Say something after .echo")

   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Run it:

.. code-block:: bash

 python bot.py

Authentication
--------------

Astra supports two primary ways to link your WhatsApp account. On the first run,
the browser session is unauthenticated, and you must perform one of these steps:

1. QR Code (Default)
~~~~~~~~~~~~~~~~~~~~

If you initialize the client without a ``phone`` argument, Astra generates a
QR code in your terminal.

.. code-block:: python

  async with Client(session_id="mybot") as client:
    # ...

**Steps:**
- Run your script.
- A QR code will appear in the terminal.
- Open WhatsApp on your phone.
- Go to **Linked Devices** > **Link a Device**.
- Scan the terminal QR code.

2. Pairing Code
~~~~~~~~~~~~~~~

If you provide a ``phone`` number in international format (without the ``+``),
Astra will request a 8-character pairing code from WhatsApp.

.. code-block:: python

  async with Client(session_id="mybot", phone="911234567890") as client:
    # ...

**Steps:**
- Run your script.
- Astra will print an 8-character code (e.g., ``ABC1-DE23``) in the terminal.
- Open WhatsApp on your phone.
- Go to **Linked Devices** > **Link a Device** > **Link with phone number instead**.
- Enter the code displayed in your terminal.

Once authenticated, your session keys and local cache are stored in
``.astra_sessions/<session_id>/``. Subsequent runs will use these files to
log in automatically, allowing you to set ``headless=True``.

Sending a message
-----------------

Inside any handler, you can send messages through the client:

.. code-block:: python

 # Reply in the same chat
 await msg.respond("Hello!")

 # Reply quoting the original message
 await msg.reply("Replying to you!")

 # Send to a specific chat by JID
 await client.chat.send_message("1234567890@c.us", "Hi there")

What is a JID?
--------------

WhatsApp identifies every chat with a **JID** (Jabber ID):

- **Personal chats**: ``<phone>@c.us`` -- e.g. ``911234567890@c.us``
- **Groups**: ``<id>@g.us`` -- e.g. ``120363012345678@g.us``
- **Linked devices**: ``<id>@lid`` -- internal device JID

You get the JID from ``msg.chat_id`` in any handler.

Stopping the bot
----------------

Press ``Ctrl+C`` in the terminal. Astra shuts down the browser and saves
session state automatically.

Environment Variables
---------------------

Astra supports environment variables for zero-config starting:

- ``PHONE_NUMBER``: Set this to your phone number (international format) to
  automatically trigger pairing code authentication without modifying your script.
- ``ASTRA_PHONE_PAIRING``: Set to ``True`` to force the "Link with phone number" UI
  even if no phone number is provided in the script (aliased as ``PHONEPAIRING``).

Example:

.. code-block:: bash

  PHONE_NUMBER=911234567890 python bot.py

Next steps
----------

- :doc:`core_concepts` -- understand the lifecycle, bridge, and session model
- :doc:`usage` -- chat, group, account, and media operations
- :doc:`filters` -- advanced message matching
- :doc:`error_codes` -- every error code explained
