.. _faq:

FAQ
===

**Does Astra require a phone to stay connected?**
 Yes. WhatsApp requires a linked phone. If your phone goes offline for
 more than ~14 days, the linked device session expires.

**Can I run multiple bots on the same phone number?**
 Yes -- use different ``session_id`` values. Each session creates a separate
 linked device. WhatsApp allows up to 4 linked devices per account.

**Will I get banned?**
 WhatsApp can ban accounts that exhibit automated behavior (mass messaging,
 rapid-fire operations). Use reasonable delays and do not spam. Astra is
 designed for personal automation, not bulk outreach.

**Does Astra support WhatsApp Business API?**
 No. Astra automates the consumer WhatsApp Web client. For the official

 Business API, see Meta's Cloud API documentation.

**Can I send images and files?**
 Yes. Use ``client.chat.send_media(chat_id, file_path, caption)``.

**What happens if the browser crashes?**
 Astra detects browser crashes (``BrowserCrashError``) and can automatically
 attempt recovery. The SyncEngine will re-inject the bridge if the page
 reloads.

**Can I deploy on a Raspberry Pi?**
 Chromium runs on ARM Linux, so Astra works on Raspberry Pi 4 and newer.
 Expect higher memory usage (~400 MB) due to the browser.

**What Python versions are supported?**
 Python 3.9 and above.

**How do I update Astra?**
 ``pip install --upgrade astra-engine``

**Where are sessions stored?**
 In ``.astra_sessions/<session_id>/`` relative to your working directory.
 This directory contains browser profile data including cookies and
 local storage.

**How do I log out?**

 Call ``await client.logout()`` or delete the session directory.

**Why do I see "Browser launch failed" errors on a CI server?**
This usually means the Playwright browser binaries are missing or the
container lacks required system libraries. Run `python -m playwright install`
inside the environment, and on Linux install the libraries listed in
https://playwright.dev/docs/ci. Headless mode is recommended in CI.

**Can I use a proxy or VPN?**
Yes. Pass a `proxy` URL when constructing the client, e.g.
`Client(proxy="http://user:pass@host:port")`. The proxy is applied to the
entire Playwright browser; WebSocket connections and downloads will travel
through it. Make sure your proxy allows WebSocket traffic.

**How do I transfer a session to another machine?**
Export the session state with `await client.export_session()`; this returns
a dict containing cookies and local storage. On the new machine, create a
client and call `await client.import_session(state)` before `start()`. This
is safer than copying the profile directory (which may contain locks).

**Why are some messages missing from `fetch_messages`?**
By default Astra maintains a local cache and will return messages from that
cache. If you recently cleared the cache or want fresh data from the bridge,
call `await client.fetch_messages(chat_id, force=True)` or set
`use_cache=False` when creating the client.

**What do the error codes mean?**
Every exception has a `code` attribute like `E3001`. Look up the code in
:doc:`error_codes` or in the `ERROR_CODES.md` file for a detailed
description and recommended action. The `hint` attribute gives a quick
suggestion (e.g. "retry later").

**Can I inspect incoming raw payloads?**
Set log level to DEBUG (`Client(log_level=logging.DEBUG)`) and you will see
raw event JSON under the `Astra` logger. Alternatively, use
`@client.on("message")` without filters and print `msg.payload` inside
the handler.

**How do I test my bot without spamming real users?**
Create a secondary WhatsApp account or a group with only yourself. You can
also use the session export/import mechanism to copy the session to another
test phone if you prefer.

**Why does `client.chat.edit_message` sometimes take 0.5 seconds?**
WhatsApp rate‑limits rapid edits. Astra enforces a 0.5 second delay under the
hood to prevent receiving `RateLimitedError`. The delay is automatic and
cannot be disabled.

**Can I run Astra in multiple threads or processes?**
The client is not thread‑safe; run one instance per process and coordinate
via IPC if needed. The underlying Playwright instance holds locks on the
profile directory, so do not share the same `session_id` across processes.

**How can I see what version of WhatsApp Web I'm connected to?**
Call `await client.sync_engine.get_diagnostics()` and inspect the
`wa_version` field. Keeping this version in your logs helps when reporting
compatibility issues.

**Is there built-in support for message scheduling or retries?**
Not directly. You can use `asyncio` tasks or external schedulers to delay
calls, and wrap send operations in retry logic using the `retryable`
attribute of exceptions.

**What happens if the linked phone changes number?**
Astra is tied to the device session, not the phone number. If you change the
number or reinstall WhatsApp on the phone, the session will become invalid
and you will need to re‑authenticate with a new QR or pairing code.

