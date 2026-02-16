import asyncio
from astra import Client, Filters

async def main():
 """
 Shows more API methods in one place.
 """
 async with Client(session_id="detailed_test") as client:

  @client.on_message(Filters.command(".test"))
  async def full_test(msg):
   # 1. Reaction
   await msg.react("✅")
   
   # 2. Reply and Edit
   rep = await msg.reply("Testing edit...")
   await asyncio.sleep(1)
   await client.chat.edit_message(rep.id, "Edit successful")

   # 3. Mute chat
   await client.chat.mute(msg.chat_id, 3600)
   await msg.respond("Chat muted for 1 hour.")

  print("Detailed example running...")
  await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
