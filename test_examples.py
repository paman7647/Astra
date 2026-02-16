# -----------------------------------------------------------
# Astra - WhatsApp Client Framework
# Licensed under the Apache License 2.0.
# -----------------------------------------------------------

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from astra import Client


def test_echo_create_client():
 from examples.echo_bot import create_client

 client = create_client()
 assert isinstance(client, Client)
 assert client.session_id == "echo_demo"


def test_scheduled_sender_monkeypatch(monkeypatch):
 from examples.scheduled_message import create_client, scheduled_sender

 client = create_client()

 sent = {}

 async def fake_send(chat_id, text, **kw):
  sent['chat_id'] = chat_id
  sent['text'] = text
  return True

 monkeypatch.setattr(client, "send_message", fake_send)

 # run the scheduled_sender for an immediate time
 when = datetime.now(timezone.utc) + timedelta(seconds=0)
 asyncio.run(scheduled_sender(client, "1@c.us", "hi", when))

 assert sent['text'] == "hi"
 assert sent['chat_id'] == "1@c.us"


def test_plugin_template_registers():
 from examples.plugin_template import ExamplePlugin

 client = Client(session_id="test_plugin")
 plugin = ExamplePlugin(client, prefix="$")
 # ensure register() does not raise and returns None
 plugin.register()
 assert hasattr(plugin, "register")
