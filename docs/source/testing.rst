.. _testing:

Testing
=======

How to test your Astra bots and contribute tests to the framework.

Testing your bot
----------------

Since Astra needs a real browser and a WhatsApp session, full integration tests
require a live environment. For unit testing your handler logic, you can
separate it from the Astra-specific code:

.. code-block:: python

 # handlers.py -- pure logic, easy to test
 def format_help_text(commands: list[str]) -> str:
  return "\\n".join(f"`.{cmd}`" for cmd in commands)

 # bot.py -- Astra integration
 from astra import Client, Filters
 from handlers import format_help_text

 client = Client(session_id="test")

 @client.on_message(Filters.command(".help"))
 async def help_cmd(msg):
  text = format_help_text(["ping", "echo", "help"])
  await msg.respond(text)

 # test_handlers.py
 from handlers import format_help_text

 def test_format_help():
  result = format_help_text(["ping", "echo"])
  assert "`.ping`" in result
  assert "`.echo`" in result

Running tests
-------------

.. code-block:: bash

 pip install -e ".[dev]"
 pytest

Framework tests
---------------

The ``tests/`` directory contains tests for Astra's internal modules.
These use ``pytest-asyncio`` for async test support.

.. code-block:: bash

 pytest tests/ -v

Syntax validation
-----------------

A quick way to validate all Python files parse correctly:

.. code-block:: bash

 python -c "
 import ast, pathlib
 for f in pathlib.Path('astra').rglob('*.py'):
  ast.parse(f.read_text())
  print(f'OK {f}')
 "

Import chain test
-----------------

Verify the full import chain works:

.. code-block:: bash

 python -c "
 from astra import Client, Filters
 from astra.errors import AstraError, ErrorCode
 print(f'Loaded {len(ErrorCode)} error codes')
 print('All imports OK')
 "