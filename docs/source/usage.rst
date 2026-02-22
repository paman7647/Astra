.. _usage:

Usage Guide
===========

This document walks you through the most common operations you'll perform
once you have an ``astra.Client`` instance. It is not a reference list of every
method (that lives in the API reference), but rather a narrative tour
showing how to send messages, respond to events, manage groups and accounts,
and build more complex workflows. Think of it as the "daily driver" guide.

Start here if you're trying to accomplish something with Astra and you
just need to know which methods to call and how they fit together.

Client Configuration
--------------------

Before you can do anything with Astra you must instantiate a ``Client``.
This object represents a single WhatsApp session and holds the browser,
protocol bridge, event dispatcher and convenience method mixins. Most
applications will create exactly one client; if you need multiple bots on
the same machine you can simply create multiple clients with different
``session_id`` values.

The constructor takes a handful of optional arguments that control how the
browser launches and how authentication works. You can also override these
values with environment variables, which is handy for deployment.

The following table summarises the most important parameters:

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

Once the client is running (``await client.start()`` or inside an
``async with`` block) you can read and write to any chat by using the
``client.chat`` mixin. All methods are asynchronous and raise
``AstraError`` subclasses on failure; you can catch these errors if you
need to retry or log issues.

**Note**: WhatsApp identifies chats by a string called a **JID** (Jabber
ID). The library doesn't try to guess human‑friendly names; you obtain
JIDs from incoming messages via ``msg.chat_id`` or by resolving contacts
with ``await client.get_entity(...)``.

**Send a message to a specific chat:**

Use ``chat.send_message`` when you know the recipient's JID. This method
works whether the target is a private one‑on‑one chat or a group, and it
returns a ``Message`` object representing the message you just sent.

.. code-block:: python

 await client.chat.send_message("911234567890@c.us", "Hello from Astra!")

You can also omit the return value if you don't care about the sent message
id.

.. code-block:: python

 await client.chat.send_message("911234567890@c.us", "Hello from Astra!")

**Send a text reply inside a handler:**

Inside an event handler the ``msg`` argument is an instance of
``astra.models.message.Message`` (see :doc:`api_reference/models`). It has
convenience methods such as ``respond`` and ``reply`` that automatically
send the reply to the current chat, and ``reply`` quotes the original
message for you.

.. code-block:: python

 @client.on_message(Filters.command(".greet"))
 async def greet(msg):
  await msg.respond("Hey there!")  # same chat, no quote
  await msg.reply("Quoting you!")  # quote-reply

This is the form you'll use in the vast majority of handlers.

.. code-block:: python

 @client.on_message(Filters.command(".greet"))
 async def greet(msg):
  await msg.respond("Hey there!")  # same chat, no quote
  await msg.reply("Quoting you!")  # quote-reply

**React to a message:**

Emoji reactions are part of the chat model. Call the ``react`` method on
a ``Message`` object and supply any Unicode emoji.

.. code-block:: python

 await msg.react("👍")

If the bridge is temporarily disconnected the call will raise a
``ConnectionLostError``; catching and retrying is a reasonable pattern.

.. code-block:: python

 await msg.react("👍")

**Create a poll:**

WhatsApp allows simple multi‑choice polls. ``send_poll`` accepts a title and
an array of option strings. The returned ``Message`` object can be used to
read poll results later.

.. code-block:: python

 await client.chat.send_poll(
  chat_id="911234567890@c.us",
  title="Lunch?",
  options=["Pizza", "Sushi", "Burgers"]
 )

You can only create polls in groups.

.. code-block:: python

 await client.chat.send_poll(
  chat_id="911234567890@c.us",
  title="Lunch?",
  options=["Pizza", "Sushi", "Burgers"]
 )

**Delete a message:**

The ``Message.delete`` helper removes a message. By default it deletes for
everyone in the chat; pass ``for_everyone=False`` to delete only for the
current account (useful for cleaning up bot chatter).

.. code-block:: python

 await msg.delete(for_everyone=True)

If WhatsApp's rate limiter is hit, this call may raise a ``RateLimitedError``
with ``retryable=True``.

.. code-block:: python

 await msg.delete(for_everyone=True)

**Edit a sent message:**

Editing is supported for up to a short window after sending (WhatsApp
policy). Astra introduces an automatic 0.5 s delay when editing to avoid
triggering server rate limits; you don't need to add your own sleep unless
you are performing many edits back‑to‑back.

.. code-block:: python

 sent = await client.chat.send_message(jid, "Helo")
 await client.chat.edit_message(sent.id, "Hello")

The original text will be replaced and the message will be marked
"edited" in the chat.

.. code-block:: python

 sent = await client.chat.send_message(jid, "Helo")
 await client.chat.edit_message(sent.id, "Hello")

.. note::
  As of v0.0.1b4, Astra includes a mandatory 0.5s stability delay for all message editing 
  operations to prevent WhatsApp rate limiting. This delay is handled automatically 
  by the library.

**Mark a chat as read:**

Sometimes you want to clear the unread badge without actually fetching or
sending a message. ``mark_read`` tells WhatsApp you've seen the latest
message in a chat.

.. code-block:: python

 await client.chat.mark_read(msg.chat_id)

.. code-block:: python

 await client.chat.mark_read(msg.chat_id)

**Archive / unarchive:**

Archives are a per‑account feature; archiving a chat simply hides it from the
main list. The API mirrors the WhatsApp UI flag via a boolean argument.

.. code-block:: python

 await client.chat.archive(chat_id, True) # archive
 await client.chat.archive(chat_id, False) # unarchive

This is useful for bots that need to clean up after themselves or implement
"snooze" behaviour.

.. code-block:: python

 await client.chat.archive(chat_id, True) # archive
 await client.chat.archive(chat_id, False) # unarchive

**Mute a chat:**

Mute prevents notifications for a period. The library takes a duration in
seconds (use ``0`` to unmute).

.. code-block:: python

 await client.chat.mute(chat_id, duration_seconds=3600)

Note that WhatsApp enforces a minimum mute interval; attempting to mute for
less than a minute may be ignored.

.. code-block:: python

 await client.chat.mute(chat_id, duration_seconds=3600)

Group operations
----------------

Groups are very common on WhatsApp. Astra’s ``client.group`` mixin exposes
all the usual administrative actions. You must be a group admin to modify
participants or change metadata; attempting an unauthorized action will
raise a ``GroupError`` with code ``E3XXX`` (see :ref:`error_codes`).

**Create a group:**

Pass a list of initial participants (their JIDs). The returned object has
``id`` and ``title`` attributes.

.. code-block:: python

 group = await client.group.create(
  name="Study Group",
  participants=["911111111111@c.us", "912222222222@c.us"]
 )

The library will automatically handle the invitation messages that WhatsApp
sends to the participants.

.. code-block:: python

 group = await client.group.create(
  name="Study Group",
  participants=["911111111111@c.us", "912222222222@c.us"]
 )

**Add or remove members:**

Admins can invite or kick users by specifying their phone JID.

.. code-block:: python

 await client.group.add_member(group_id, "913333333333@c.us")
 await client.group.remove_member(group_id, "913333333333@c.us")

These methods return ``True`` on success. If the user is already in the
group, ``add_member`` raises an error.

.. code-block:: python

 await client.group.add_member(group_id, "913333333333@c.us")
 await client.group.remove_member(group_id, "913333333333@c.us")

**Promote / demote admins:**

Use these helpers to change a member’s role.

.. code-block:: python

 await client.group.promote(group_id, "911111111111@c.us")
 await client.group.demote(group_id, "911111111111@c.us")

They behave just like the UI; the target must already be a member of the
group.

.. code-block:: python

 await client.group.promote(group_id, "911111111111@c.us")
 await client.group.demote(group_id, "911111111111@c.us")

**Update group info:**

You can update the subject (group name) and description. These actions
are throttled by WhatsApp, so avoid calling them more than once every few
seconds.

.. code-block:: python

 await client.group.set_subject(group_id, "New Group Name")
 await client.group.set_description(group_id, "Updated description")

.. code-block:: python

 await client.group.set_subject(group_id, "New Group Name")
 await client.group.set_description(group_id, "Updated description")

**Get group info:**

Retrieve a snapshot of the group’s metadata, including participant
objects. The ``Participant`` model has attributes like ``id`` and
``is_admin``.

.. code-block:: python

 info = await client.group.get_info(group_id)
 print(info.title, len(info.participants))

.. code-block:: python

 info = await client.group.get_info(group_id)
 print(info.title, len(info.participants))

**Join a group via invite link:**

If you have a valid invite URL, the bot can join automatically.

.. code-block:: python

 await client.group.join("https://chat.whatsapp.com/ABC123...")

This is handy for onboarding a bot to many groups at once, e.g. by scanning
QR codes.

.. code-block:: python

 await client.group.join("https://chat.whatsapp.com/ABC123...")

Account operations
------------------

The ``client.account`` mixin exposes settings and actions that affect the
bot’s own WhatsApp account rather than individual chats. These calls map
closely to the options you see in the mobile app’s "Settings" screen.

**Get your profile:**

Fetches the authenticated user’s profile. Useful when you need the full JID
or display name programmatically.

.. code-block:: python

 me = await client.get_me()
 print(me.name, me.id.serialized)

.. code-block:: python

 me = await client.get_me()
 print(me.name, me.id.serialized)

**Update display name:**

.. code-block:: python

 await client.account.set_display_name("Astra Bot")

This change is propagated to all of your contacts.

.. code-block:: python

 await client.account.set_display_name("Astra Bot")

**Update about text:**

.. code-block:: python

 await client.account.set_about("Powered by Astra Engine")

About text is often used by bots to show status or version information.

.. code-block:: python

 await client.account.set_about("Powered by Astra Engine")

**Block / unblock contacts:**

``block`` prevents messages from the specified JID; ``unblock`` reverses it.
Be aware that blocking is account‑wide and persists across restarts.

.. code-block:: python

 await client.account.block("911234567890@c.us")
 await client.account.unblock("911234567890@c.us")

.. code-block:: python

 await client.account.block("911234567890@c.us")
 await client.account.unblock("911234567890@c.us")

Advanced patterns
-----------------

Once you're comfortable with the basic operations, you can combine them to
build more interesting, stateful behavior. These recipes are the sort of
things you find yourself writing once your bot is past the "hello world"
stage.

Once you're comfortable with the basic operations, Astra lets you build
stateful workflows and integrate with external systems.

**Conversations**

Use :meth:`Client.conversation` to create a short-lived inbox where you can
`wait_for` specific replies or collect a series of messages.

.. code-block:: python

 async def handle_survey(client, chat_id):
  conv = client.conversation(chat_id, timeout=30)
  await conv.send("What is your name?")
  name_msg = await conv.wait_for("message")
  await conv.send("How old are you?")
  age_msg = await conv.wait_for("message")
  await conv.send(f"Thanks {name_msg.text}, age {age_msg.text}")

@client.on_message(Filters.command(".survey"))
async def survey_handler(msg):
 await handle_survey(client, msg.chat_id)

**Batch operations**

You can iterate over chats or contacts by querying the session store directly:

.. code-block:: python

 # print the titles of every known chat
 for chat in await client.store.iter_chats():
  print(chat.id, chat.title)

 # bulk-delete the last 20 messages from a chat
 msgs = await client.chat.fetch_messages(chat_id, limit=20)
 for m in msgs:
  await m.delete()

**Error handling**

Every network or bridge failure surfaces as an ``AstraError`` subclass. Use
``retryable`` to decide whether to retry automatically, or log and ignore:

.. code-block:: python

 from astra.errors import AstraError

 async def safe_send(jid, text):
  try:
   return await client.chat.send_message(jid, text)
  except AstraError as exc:
   if exc.retryable:
    await asyncio.sleep(1)
    return await safe_send(jid, text)
   else:
    logger.error("permanent send failure: %s", exc)
    raise


**Set privacy settings:**

You can programmatically adjust privacy options such as last‑seen visibility
or read receipts, just like in the mobile app.

.. code-block:: python

 await client.account.set_last_seen("contacts")  # contacts, all, none
 await client.account.set_read_receipts(False)

.. code-block:: python

 await client.account.set_last_seen("contacts")  # contacts, all, none
 await client.account.set_read_receipts(False)

**Message Attributes**

Every ``Message`` object exposes a handful of useful boolean flags and
helpers that let you inspect the contents without parsing raw payloads. The
properties listed below are the ones you’ll check most often when writing
filters and handlers.

The ``Message`` object contains several properties for quick content inspection:

.. list-table::
 :header-rows: 1

 * - Property
  - Description
 * - ``is_media``
  - True if the message contains an image, video, sticker, etc.
 * - ``is_group``
  - True if the message was sent in a group chat.
 * - ``is_service``
  - True for system messages (e.g., "Aman added you").
 * - ``quoted``
  - The quoted message object (or None).

**Checking for media:**

.. code-block:: python

 @client.on_message(Filters.all)
 async def check_media(msg):
  if msg.is_media:
   print(f"Message {msg.id} contains media of type: {msg.type}")

Media operations
----------------

WhatsApp supports sending images, video, audio, documents, stickers, and
more. Astra wraps all of the underlying complexity (uploading to the WA
server, handling types, etc.) in convenient helper methods. Media
operations return a ``Message`` object just like text messages.

**Send media with caption:**

Any file path supported by WhatsApp can be uploaded via
``chat.send_media``. The method auto-detects the type by file extension,
but you can also force a specific kind (e.g. ``file`` vs ``image``) with
keyword arguments.

.. code-block:: python

 await client.chat.send_media(
  chat_id="911234567890@c.us",
  file_path="/path/to/photo.jpg",
  caption="Check this out!"
 )

If the upload fails due to a transient network error, the underlying
``retry`` logic will automatically attempt a few times before raising.

.. code-block:: python

 await client.chat.send_media(
  chat_id="911234567890@c.us",
  file_path="/path/to/photo.jpg",
  caption="Check this out!"
 )

**Post a status/story:**

Astra can also update your account’s status (the feature known as "stories"
on mobile). Text statuses are posted via ``post_text_status``; media
statuses behave like normal media uploads but are visible only for 24 hours.

.. code-block:: python

 # Text status
 await client.account.post_text_status("Hello from Astra!")

 # Media status
 await client.chat.send_media_status(
  file_path="/path/to/image.png",
  caption="My status update"
 )

.. code-block:: python

 # Text status
 await client.account.post_text_status("Hello from Astra!")

 # Media status
 await client.chat.send_media_status(
  file_path="/path/to/image.png",
  caption="My status update"
 )

**Get a contact's profile picture URL:**

You can request the URL of a contact’s profile picture; this is useful if
you want to download or display it in an external application.

.. code-block:: python

 url = await client.account.get_profile_pic("911234567890@c.us")

The URL is temporary and may expire after a few minutes.

.. code-block:: python

 url = await client.account.get_profile_pic("911234567890@c.us")

Diagnostics
-----------

Astra exposes several introspection helpers that are useful when debugging or
collecting metrics. These calls do not require the bridge to be active – they
use local state when possible.

**Get engine diagnostics:**

This returns a dictionary with information such as uptime, WhatsApp Web
version, heartbeats sent/received, and cache statistics. It’s the first thing
you should log when investigating connectivity issues.

.. code-block:: python

 diag = client.sync_engine.get_diagnostics()
 print(f"Uptime: {diag['uptime_s']}s")
 print(f"WA Version: {diag['wa_version']}")
 print(f"Heartbeats: {diag['total_heartbeats']}")

.. code-block:: python

 diag = client.sync_engine.get_diagnostics()
 print(f"Uptime: {diag['uptime_s']}s")
 print(f"WA Version: {diag['wa_version']}")
 print(f"Heartbeats: {diag['total_heartbeats']}")

**Get cache statistics:**

The session store keeps simple counts of how many chats, contacts and
messages it knows about. This is handy for monitoring or throttle logic.

.. code-block:: python

 stats = client.store.get_stats()
 print(f"{stats['chats']} chats, {stats['contacts']} contacts")

.. code-block:: python

 stats = client.store.get_stats()
 print(f"{stats['chats']} chats, {stats['contacts']} contacts")

**Force a sync:**

Normally Astra synchronizes automatically when events arrive. If you need to
manually push a sync (for example, after modifying the local cache), call
``client.sync()``. This resets the internal stall timer as well.

.. code-block:: python

 await client.sync()

.. code-block:: python

 await client.sync()
