import asyncio
from astra import Client, Filters
from astra.errors import MessageSendError

async def main():
 # Example using commands, editing messages and handling errors
 async with Client(session_id="command_example") as client:

  @client.on_message(Filters.command(".ping"))
  async def ping(msg):
   import time
   start = time.monotonic()
   
   # Send a placeholder and edit it with the result
   temp = await msg.respond("...")
   latency = (time.monotonic() - start) * 1000
   await client.chat.edit_message(temp.id, f"Latency: {latency:.0f}ms")

  @client.on_message(Filters.command(".me"))
  async def me(msg):
   # Get current account info
   me = await client.get_me()
   await msg.reply(f"Name: {me.name}\nID: {me.id.serialized}")

  print("Command example running...")
  await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
