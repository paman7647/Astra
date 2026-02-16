import asyncio
from astra import Client

async def main():
 # Running background tasks alongside the client
 async with Client(session_id="bg_example") as client:

  async def worker():
   while True:
    if client.is_authenticated:
     # Do some periodic work
     print("Background worker heartbeat")
    await asyncio.sleep(600)

  # Start the background task
  asyncio.create_task(worker())

  await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
