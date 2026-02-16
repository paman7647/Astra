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