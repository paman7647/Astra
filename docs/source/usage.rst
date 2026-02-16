.. _usage:

Usage Guide
===========

This page covers the main operations you can perform with Astra.

Client Configuration
--------------------

The :class:`~astra.client.client.Client` constructor accepts several parameters to customize its behavior:

.. list-table::
  :header-rows: 1
  :widths: 20 20 60

  * - Parameter
   - Default
   - Description
  * - ``session_id``
   - ``"default"``
   - Unique ID for the session. Saves data in ``.astra_sessions/<id>``.
   * - ``phone``
     - ``None``
     - If set, triggers Pairing Code auth. Can also be set via ``PHONE_NUMBER``
       or enforced via ``PHONEPAIRING=True`` environment variables.
  * - ``headless``
   - ``True``
   - Whether to run the browser without a visible window. Use ``False`` for first-time auth.
  * - ``browser_type``
   - ``"chromium"``
   - Browser to use: ``chromium``, ``firefox``, or ``webkit``.
  * - ``proxy``
   - ``None``
   - Proxy server URL (e.g., ``http://user:pass@host:port``).
  * - ``qr_callback``
   - Terminal log
   - Optional async function to handle the raw QR string.
  * - ``pairing_code_callback``
   - Terminal log
   - Optional async function to handle the 8-character pairing code.

Example with explicit configuration:

.. code-block:: python

  from astra import Client

  client = Client(
    session_id="bot123",
    phone="919988776655", # trigger pairing code
    headless=False,
    browser_type="firefox"
  )

Chat operations
---------------

**Send a message to a specific chat:**

.. code-block:: python

 await client.chat.send_message("911234567890@c.us", "Hello from Astra!")

**Send a text reply inside a handler:**

.. code-block:: python

 @client.on_message(Filters.command(".greet"))
 async def greet(msg):
  await msg.respond("Hey there!")  # same chat, no quote
  await msg.reply("Quoting you!")  # quote-reply

**React to a message:**

.. code-block:: python

 await msg.react("👍")

**Create a poll:**

.. code-block:: python

 await client.chat.send_poll(
  chat_id="911234567890@c.us",
  title="Lunch?",
  options=["Pizza", "Sushi", "Burgers"]
 )

**Delete a message:**

.. code-block:: python

 await msg.delete(for_everyone=True)

**Edit a sent message:**

.. code-block:: python

 sent = await client.chat.send_message(jid, "Helo")
 await client.chat.edit_message(sent.id, "Hello")

**Mark a chat as read:**

.. code-block:: python

 await client.chat.mark_read(msg.chat_id)

**Archive / unarchive:**

.. code-block:: python

 await client.chat.archive(chat_id, True) # archive
 await client.chat.archive(chat_id, False) # unarchive

**Mute a chat:**

.. code-block:: python

 await client.chat.mute(chat_id, duration_seconds=3600)

Group operations
----------------

**Create a group:**

.. code-block:: python

 group = await client.group.create(
  name="Study Group",
  participants=["911111111111@c.us", "912222222222@c.us"]
 )

**Add or remove members:**

.. code-block:: python

 await client.group.add_member(group_id, "913333333333@c.us")
 await client.group.remove_member(group_id, "913333333333@c.us")

**Promote / demote admins:**

.. code-block:: python

 await client.group.promote(group_id, "911111111111@c.us")
 await client.group.demote(group_id, "911111111111@c.us")

**Update group info:**

.. code-block:: python

 await client.group.set_subject(group_id, "New Group Name")
 await client.group.set_description(group_id, "Updated description")

**Get group info:**

.. code-block:: python

 info = await client.group.get_info(group_id)
 print(info.title, len(info.participants))

**Join a group via invite link:**

.. code-block:: python

 await client.group.join("https://chat.whatsapp.com/ABC123...")

Account operations
------------------

**Get your profile:**

.. code-block:: python

 me = await client.get_me()
 print(me.name, me.id.serialized)

**Update display name:**

.. code-block:: python

 await client.account.set_display_name("Astra Bot")

**Update about text:**

.. code-block:: python

 await client.account.set_about("Powered by Astra Engine")

**Block / unblock contacts:**

.. code-block:: python

 await client.account.block("911234567890@c.us")
 await client.account.unblock("911234567890@c.us")

**Set privacy settings:**

.. code-block:: python

 await client.account.set_last_seen("contacts")  # contacts, all, none
 await client.account.set_read_receipts(False)

Media operations
----------------

**Send media with caption:**

.. code-block:: python

 await client.chat.send_media(
  chat_id="911234567890@c.us",
  file_path="/path/to/photo.jpg",
  caption="Check this out!"
 )

**Post a status/story:**

.. code-block:: python

 # Text status
 await client.account.post_text_status("Hello from Astra!")

 # Media status
 await client.chat.send_media_status(
  file_path="/path/to/image.png",
  caption="My status update"
 )

**Get a contact's profile picture URL:**

.. code-block:: python

 url = await client.account.get_profile_pic("911234567890@c.us")

Diagnostics
-----------

**Get engine diagnostics:**

.. code-block:: python

 diag = client.sync_engine.get_diagnostics()
 print(f"Uptime: {diag['uptime_s']}s")
 print(f"WA Version: {diag['wa_version']}")
 print(f"Heartbeats: {diag['total_heartbeats']}")

**Get cache statistics:**

.. code-block:: python

 stats = client.store.get_stats()
 print(f"{stats['chats']} chats, {stats['contacts']} contacts")

**Force a sync:**

.. code-block:: python

 await client.sync()
