import asyncio
from astra import Client, Filters

async def main():
 # Example for promoting users and getting group information
 async with Client(session_id="group_example") as client:

   @client.on_message(Filters.is_group & Filters.command(".admins"))
   async def list_admins(msg):
    info = await client.group.get_info(msg.chat_id)
    admins = [p.id.user for p in info.participants if p.is_admin]
    await msg.respond("Admins:\n" + "\n".join(admins))

   @client.on_message(Filters.is_group & Filters.command(".promote"))
   async def promote_user(msg):
    if msg.quoted:
     try:
      await client.group.promote(msg.chat_id, msg.quoted.sender)
      await msg.respond("Promoted.")
     except Exception as e:
      await msg.respond(f"Error: {e}")

   print("Group example running...")
   await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
