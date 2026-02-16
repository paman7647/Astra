import asyncio
import os
from astra import Client, Filters

async def main():
 # Working with media, polls, and reactions
 async with Client(session_id="media_example") as client:

  @client.on_message(Filters.command(".send_img"))
  async def send_image(msg):
   # Requires a valid image file
   path = "assets/logo.png"
   if os.path.exists(path):
    await client.chat.send_media(msg.chat_id, path, caption="Sent via Astra")

  @client.on_message(Filters.command(".poll"))
  async def create_poll(msg):
   await client.chat.send_poll(
    msg.chat_id, 
    "Poll Example", 
    ["Option A", "Option B"]
   )

  @client.on_message(Filters.command(".react"))
  async def react(msg):
   target = msg.quoted if msg.quoted else msg
   await target.react("🔥")

  print("Media example running...")
  await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
