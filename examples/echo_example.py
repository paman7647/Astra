import asyncio
from astra import Client, Filters

async def main():
 # Basic bot that echoes back private messages
 async with Client(session_id="echo_bot") as client:

  @client.on_message(Filters.text & ~Filters.is_group)
  async def on_private_message(msg):
   await msg.respond(f"Echo: {msg.text}")
   print(f"Message from {msg.sender}")

  print("Echo example running...")
  await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
