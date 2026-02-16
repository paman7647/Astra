
"""
Phone Pairing Example
---------------------

This script demonstrates how to authenticate using a phone number
instead of scanning a QR code.

The updated Client automatically:
1. Detects the phone number.
2. Formats it correctly (e.g., adds +91).
3. Injects it into WhatsApp Web.
4. Returns the pairing code.
"""

import asyncio
import logging
from astra import Client, Filters

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Client with your phone number
# You can also set valid environmental variables:
# export PHONE_NUMBER="919876543210"
# export ASTRA_PHONE_PAIRING="true"
client = Client(session_id="phone_pairing_demo", phone="919876543210", headless=False)

@client.on_message(Filters.command("ping"))
async def ping(message):
    await message.reply("Pong! 🏓")

async def main():
    print("🚀 Starting Phone Pairing Demo...")
    # The client will print the Pairing Code to the console automatically
    await client.start()
    
    # Run until disconnected
    await client.run_until_disconnected()

if __name__ == "__main__":
    client.run_forever_sync()
