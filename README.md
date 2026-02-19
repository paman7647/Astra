<div align="center">

 <img src="AstraClient.png" alt="Astra Engine Logo" width="600" />

 # Astra Engine

 **High-performance WhatsApp Web Automation Library for Python**

 [![Python Version](https://img.shields.io/badge/python-3.9%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
 [![License](https://img.shields.io/badge/license-Apache%202.0-green?style=for-the-badge)](LICENSE)
 [![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?style=for-the-badge)](https://github.com/astral-sh/ruff)
 [![Documentation](https://img.shields.io/badge/docs-read%20the%20docs-8ca1af?style=for-the-badge)](https://astra-engine.readthedocs.io/)

</div>

---

Astra Engine is a Python library that lets you automate WhatsApp Web. It uses Playwright to run a real browser instance, which means it works exactly like a real user. No hidden APIs, no ban risks from modified protocols—just meaningful automation.

We built this because existing libraries were either too slow, too brittle, or abandoned. Astra is designed to be the tool we wanted to use ourselves: **written from scratch**, typed, documented, and reliable.

## ⚡ What makes it different?

* **It's a Real Browser**: We don't try to reverse-engineer the encrypted WebSocket protocol. We drive the official WhatsApp Web client, so if it works in Chrome, it works in Astra.
* **Privacy Focused**: The engine automatically strips telemetry and tracking metrics. Your bot looks just like a normal user to WhatsApp's servers.
* **Developer Friendly**: Full type hints, proper documentation, and sensible error messages. You won't have to guess what methods do.
* **Stays Connected**: The connection manager handles QR code refreshes, internet dropouts, and browser crashes without you needing to write retry loops.

---

## 🚀 Features

| Feature | Status | Notes |
| :--- | :---: | :--- |
| **Multi-Device** | ✅ | Works with the latest MD (Multi-Device) beta and stable. |
| **Messaging** | ✅ | Send text, reply to messages, mention users, edit sent messages. |
| **Media** | ✅ | Send and receive Images, Videos, Audio, Documents, and Stickers. |
| **Interaction** | ✅ | Create Polls, react to messages with emojis, delete messages. |
| **Groups** | ✅ | Extensive admin controls: promote/demote, change settings, manage participants. |
| **Privacy** | ✅ | Detailed control over who sees your profile, status, and last seen. |
| **Events** | ✅ | Real-time event loop to listen for new messages, status updates, and more. |
| **Phone Pairing** | ✅ | Login using your phone number instead of scanning a QR code. |

---

## 📦 Installation

You need Python 3.9 or newer.

```bash
# 1. Install Astra Engine
pip install astra-engine

# 2. Install the browser binaries (Chromium)
python -m playwright install chromium
```

---

## 🛠️ Quick Start

### Option A: QR Code Login

Here is the shortest way to get a bot running. This will print a QR code in your terminal—scan it with WhatsApp on your phone.

```python
import asyncio
from astra import Client, Filters

async def main():
 # session_id saves your login so you don't have to scan every time
 async with Client(session_id="my_bot") as client:

  # Respond to "!ping"
  @client.on_message(Filters.command("ping"))
  async def ping(msg):
   await msg.respond("Pong! 🚀")

  # React to any message containing "hello"
  @client.on_message(Filters.text_contains("hello"))
  async def greet(msg):
   await msg.react("👋")

  print("Bot is running... Press Ctrl+C to stop.")
  await client.run_forever()

if __name__ == "__main__":
 asyncio.run(main())
```

### Option B: Phone Number Pairing

If you can't scan a QR code, you can use phone number pairing. Astra will print an 8-character code that you enter on your phone.

```python
from astra import Client

client = Client(session_id="pairing_bot", phone="919876543210")
client.run_forever_sync()
```
👉 Enter the code printed in the terminal into WhatsApp > Linked Devices > Link with phone number.
👉 **[Check out the examples folder](examples/)** for more scripts like Group Management, Media Sending, and Background Tasks.

---

## 🤝 Want to Contribute?

We'd love your help! Astra is an open project. Whether you want to fix a bug, add a new feature, or just improve the docs, here is how you can get started.

1. **Fork the repo** on GitHub.
2. **Clone it** to your machine.
3. **Set up your environment**:

 ```bash
 # Create a virtual environment
 python -m venv .venv
 source .venv/bin/activate # or .venv\Scripts\activate on Windows

 # Install in editable mode with dev dependencies
 pip install -e ".[dev]"
 python -m playwright install chromium
 ```

4. **Make your changes**.
5. **Run the checks** to make sure everything is clean:

 ```bash
 # format code
 ruff check . --fix

 # check types
 mypy astra
 ```

6. **Submit a Pull Request**! We'll review it and get it merged.

---

## ⚖️ Disclaimer

This project is **not** affiliated, associated, authorized, endorsed by, or in any way officially connected with WhatsApp or any of its subsidiaries or its affiliates. The official WhatsApp website can be found at https://www.whatsapp.com.

**This software is for educational purposes only.** Automating user accounts may violate WhatsApp's Terms of Service. Use it responsibly and at your own risk.

---

<div align="center">
 <sub>Built with ❤️ by Aman Kumar Pandey</sub>
</div>
