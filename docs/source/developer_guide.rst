.. _developer_guide:

Developer Guide
===============

This page is for people who want to contribute to Astra itself.

Setting up a development environment
--------------------------------------

.. code-block:: bash

 git clone https://github.com/paman7647/Astra.git
 cd Astra
 python -m venv .venv && source .venv/bin/activate
 pip install -e ".[dev]"
 python -m playwright install chromium

Project structure
-----------------

.. code-block:: text

 astra/
 ├── __init__.py   # Public exports
 ├── constants.py   # Global config values
 ├── client/    # Client class and lifecycle
 │ ├── client.py  # Main Client
 │ ├── authenticator.py # QR / pairing auth
 │ ├── sync_engine.py # Background sync and health
 │ └── methods/   # Chat, Group, Account mixins
 ├── protocol/   # Bridge to WhatsApp Web JS
 │ ├── gateway.py  # ProtocolBridge.call()
 │ └── js_engine.py  # Injected JS
 ├── core/bridge/   # Domain-specific JS bridges
 ├── errors/    # Typed exceptions and error codes
 ├── events/    # Event dispatcher, filters
 ├── models/    # Data classes (Message, Chat, User)
 ├── connection/   # Browser manager, reconnection
 └── utils/    # Helpers (health, media, retry)

Code style
----------

- **Formatting**: ruff (configured in ``pyproject.toml``).
- **Type hints**: Use them on all public methods.
- **Docstrings**: Google style (Napoleon parses them for Sphinx).
- **Logging**: Use ``logging.getLogger(__name__)``. No emojis in log messages.
- **Errors**: Raise typed ``AstraError`` subclasses, never bare ``Exception``.

.. code-block:: bash

 # Check formatting
 ruff check astra/

 # Type check
 mypy astra/

Adding a new error code
-----------------------

1. Add the code to ``astra/errors/codes.py``:

 .. code-block:: python

  NEW_ERROR = _CodeDef("E3099", "Messaging", "Something failed.", "Try again.", True)

2. Add the exception class to ``astra/errors/exceptions.py``:

 .. code-block:: python

  class NewError(AstraError):
   def __init__(self, message=None, **kwargs):
    super().__init__(**_from_code(ErrorCode.NEW_ERROR, message, **kwargs))

3. Export it from ``astra/errors/__init__.py``.
4. Add a row to ``ERROR_CODES.md``.

Adding a new bridge method
--------------------------

1. Add the JavaScript function in ``astra/protocol/js_engine.py``.
2. Create or extend the domain bridge in ``astra/core/bridge/``.
3. Add the Python method to the appropriate mixin in ``astra/client/methods/``.
4. Wrap the call in a ``try/except`` with a typed error.

Building docs
-------------

.. code-block:: bash

 cd docs
 sphinx-build -b html source _build/html
 open _build/html/index.html
