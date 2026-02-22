.. _cookbook:

Cookbook
========

This section presents a collection of practical, longer‑form scripts that
you can reuse or adapt. Each recipe demonstrates how to combine several
Astra building blocks to address a concrete problem; you can incorporate
these examples directly into your project or use them as a foundation for
your own functionality.



Ticketing bot with SQLite
-------------------------

Here’s a simple support‑ticket system. When someone quotes a message with
``.ticket``, we save it to a local SQLite database and reply with a ticket
number. Use this pattern whenever you need durable storage of incoming chat
content—``SessionStore`` helps you access past chats, but any database will
do.

.. code-block:: python

 import asyncio
 import sqlite3
 from astra import Client, Filters

 DB_PATH = "tickets.db"

 def init_db():
  conn = sqlite3.connect(DB_PATH)
  conn.execute(
   """
   CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT,
    message_id TEXT,
    text TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
   )"""
  )
  conn.commit()
  return conn

 async def main():
  init_db()
  async with Client(session_id="tickets") as client:

   @client.on_message(Filters.command(".ticket"))
   async def ticket(msg):
    # store the quoted message as a ticket
    if not msg.quoted:
     await msg.reply("Quote a message to create a ticket.")
     return
    conn = init_db()
    conn.execute(
     "INSERT INTO tickets (chat_id, message_id, text) VALUES (?, ?, ?)",
     (msg.chat_id, msg.quoted.id, msg.quoted.text),
    )
    ticket_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    await msg.reply(f"Ticket #{ticket_id} created.")

   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Integrating with an HTTP API
----------------------------

Most real bots talk to other services. This snippet shows a tiny weather bot
that calls an HTTP API using ``aiohttp`` and sends the result back to the
user. It’s a good template for any external‑service integration.

.. code-block:: python

 import asyncio
 import aiohttp
 from astra import Client, Filters

 async def get_weather(city: str) -> str:
  async with aiohttp.ClientSession() as sess:
   async with sess.get(f"https://api.weather.example/{city}") as resp:
    data = await resp.json()
    return f"{data['temp']}Â°C, {data['condition']}"

 async def main():
  async with Client(session_id="weather") as client:

   @client.on_message(Filters.command(".weather"))
   async def weather_cmd(msg):
    parts = msg.text.split(None, 1)
    if len(parts) < 2:
     await msg.reply("Usage: .weather <city>")
     return
    forecast = await get_weather(parts[1])
    await msg.reply(f"Forecast for {parts[1]}: {forecast}")

   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Advanced sync with backlog
--------------------------

Maybe you just deployed a new bot and want to scan the history for
important messages. ``SessionStore`` keeps a local cache of chats and
supports asynchronous iteration via ``iter_messages``. The example below
walks every known chat at startup and prints any message containing the word
"urgent".

.. code-block:: python

 async def scan_history(client: Client, chat_id: str):
  async for msg in client.store.iter_messages(chat_id):
   if "urgent" in msg.text.lower():
    print("Found urgent message", msg.id, msg.text)

 async def main():
  async with Client(session_id="scanner") as client:
   # process every chat at startup
   for chat in await client.store.iter_chats():
    await scan_history(client, chat.id)
   await client.run_forever()


Feel free to mix and match these snippets with filters, conversation
helpers, retries, etc. They’re meant to illustrate patterns; you’ll tweak
them to fit your own workflows.
