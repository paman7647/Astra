.. _examples:

Examples
========

This page contains working examples for common Astra Engine use cases.
All files are available in the ``examples/`` directory.

Echo Example
------------

Basic bot that echoes private messages.

.. code-block:: python

 import asyncio
 from astra import Client, Filters

 async def main():
  async with Client(session_id="echo_bot") as client:

   @client.on_message(Filters.text & ~Filters.is_group)
   async def on_private_message(msg):
    await msg.respond(f"Echo: {msg.text}")

   print("Echo example running...")
   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Command Example
---------------

Handling commands, message editing, and profile info.

.. code-block:: python

 import asyncio
 from astra import Client, Filters

 async def main():
  async with Client(session_id="cmd_example") as client:

   @client.on_message(Filters.command(".ping"))
   async def ping(msg):
    temp = await msg.respond("...")
    await client.chat.edit_message(temp.id, "Pong!")

   @client.on_message(Filters.command(".me"))
   async def me(msg):
    account = await client.get_me()
    await msg.reply(f"Name: {account.name}")

   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Media and Reactions
-------------------

Interaction with polls, stickers, and reactions.

.. code-block:: python

 import asyncio
 from astra import Client, Filters

 async def main():
  async with Client(session_id="media_example") as client:

   @client.on_message(Filters.command(".poll"))
   async def poll(msg):
    await client.chat.send_poll(msg.chat_id, "Test", ["A", "B"])

   @client.on_message(Filters.command(".react"))
   async def react(msg):
    await msg.react("🔥")

   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Group Management
----------------

Participate management and group info.

.. code-block:: python

 import asyncio
 from astra import Client, Filters

 async def main():
  async with Client(session_id="group_example") as client:

   @client.on_message(Filters.is_group & Filters.command(".admins"))
   async def list_admins(msg):
    info = await client.group.get_info(msg.chat_id)
    admins = [p.id.user for p in info.participants if p.is_admin]
    await msg.respond("\n".join(admins))

   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())

Background Services
-------------------

Running periodic tasks alongside the bot.

.. code-block:: python

 import asyncio
 from astra import Client

 async def main():
  async with Client(session_id="bg_example") as client:
   
   async def heartbeat():
    while True:
     if client.is_authenticated:
      print("Online")
     await asyncio.sleep(600)

   asyncio.create_task(heartbeat())
   await client.run_forever()

 if __name__ == "__main__":
  asyncio.run(main())
