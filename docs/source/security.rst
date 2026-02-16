.. _security:

Security
========

Astra automates WhatsApp Web, which means it handles sensitive data:
authentication tokens, message content, and contact information. This page
covers how to keep things secure.

Session security
----------------

Session data (in ``.astra_sessions/``) contains your WhatsApp authentication
tokens. Anyone with access to this directory can impersonate your account.

- **Never commit ``.astra_sessions/`` to git.** It is already in the
 ``.gitignore`` template.
- **Restrict file permissions** on production servers:
 ``chmod 700 .astra_sessions/``
- **Back up sessions** to an encrypted location if needed.

Environment variables
---------------------

Never hardcode sensitive values in source code. Use environment variables
or a ``.env`` file:

.. code-block:: bash

 # .env (never commit this file)
 PHONE_NUMBER=+911234567890
 ASTRA_SESSION=prod

The ``.env`` file is already in ``.gitignore``.

Network considerations
----------------------

- Astra connects to ``web.whatsapp.com`` over HTTPS. All traffic between
 the browser and WhatsApp servers is end-to-end encrypted by WhatsApp's
 protocol.
- Astra does **not** proxy, intercept, or decrypt message content. It reads
 data from the already-decrypted browser DOM.
- On shared servers, ensure that only your process can access the browser's
 debugging port (Playwright manages this automatically).

Rate limiting
-------------

WhatsApp imposes rate limits on message sending. Astra detects rate-limit
responses and raises ``RateLimitedError`` (E7003). Best practices:

- Add delays between bulk operations (at least 1-2 seconds per message).
- Avoid sending to more than ~50 contacts in a tight loop.
- If you get rate-limited, back off for at least 30 seconds.

Responsible use
---------------

Astra is a tool for *personal automation* -- managing your own WhatsApp account
programmatically. Please:

- Respect WhatsApp's Terms of Service.
- Do not use Astra for unsolicited bulk messaging (spam).
- Do not use Astra to harvest user data without consent.
- Be aware that WhatsApp can ban accounts that exhibit bot-like behavior.
