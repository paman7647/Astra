.. _introduction:

Introduction
============

Welcome to **Astra Engine** – a Python framework designed to automate and
interact with WhatsApp Web in a reliable, extensible, and async-friendly way.

Astra exists to provide a programmable interface to WhatsApp Web when no
official API is available or sufficient. It enables developers to automate
common tasks such as message sending, group moderation, and integration with
backend services while abstracting away the underlying browser automation,
session management, and data synchronization details.

Key problems Astra solves:

* **Headless browser orchestration** – Playwright drives a real WebKit/
  Chromium instance under the hood; Astra wraps it so you never have to
  write the glue code yourself.
* **Authentication lifecycles** – QR codes, pairing codes, session
  persistence, logout, and recovery are all built‑in.
* **Rich messaging API** – send, edit, delete, react, forward, and poll
  messages with first‑class Python coroutines.
* **Group and account management** – create groups, manage participants,
  adjust privacy settings, block/unblock users, and more.
* **Event-driven architecture** – listen to incoming messages, reactions,
  presence updates, and other events with flexible matching filters.
* **Resilient bridge protocol** – a bidirectional channel between Python
  and the WhatsApp Web JS runtime; automatically recovers from disconnects
  and queues calls when the page reloads.
* **Pluggable plugin system** – extend the client via class decorators with
  minimal boilerplate (useful for userbot ecosystems).

Terminology
-----------

Here are a few terms you'll see repeatedly in the documentation and code:

* **Client** – the main entry point (``astra.client.client.Client``). It
  owns the browser, bridge, event emitter, and utility mixins.
* **JID** – Jabber ID; a string that uniquely identifies a chat. Examples
  include ``12345@c.us`` (personal), ``1203630...@g.us`` (group), and
  ``<device>@lid`` (linked device). Methods that accept a chat refer to JIDs.
* **Message payload** – raw JSON object received from WhatsApp. ``Message``
  model classes hydrate and expose high‑level properties.
* **Bridge** – the mechanism that runs a small JavaScript engine inside the
  page and allows Python to call functions there (``EngineAPI``).
* **Event** – a notification emitted by the bridge; sent to handlers via
  ``EventEmitter``/``EventDispatcher``.
* **Sync engine** – background task that drains the event queue and updates
  internal caches; helps give synchronous lookups to asynchronous data.

The framework follows a familiar pattern to many Python async SDKs: an
asynchronous client object, decorator-based event registration, flexible
filters, and a well-defined startup/shutdown lifecycle.

With that foundation, let's move on to installing Astra and running your
first bot!