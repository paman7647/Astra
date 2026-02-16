.. _readthedocs:

Read the Docs
=============

This documentation is built with `Sphinx <https://www.sphinx-doc.org/>`_ and
the `Read the Docs theme <https://sphinx-rtd-theme.readthedocs.io/>`_.

Building locally
----------------

.. code-block:: bash

 cd docs
 pip install sphinx sphinx-rtd-theme
 sphinx-build -b html source _build/html
 open _build/html/index.html

Hosting on Read the Docs
-------------------------

To deploy this documentation to `readthedocs.org <https://readthedocs.org/>`_:

1. Push the repository to GitHub at `paman7647/Astra <https://github.com/paman7647/Astra>`_.
2. Sign in to Read the Docs and import the project.
3. The build will use ``docs/source/conf.py`` automatically.

Create a ``.readthedocs.yaml`` in the project root:

.. code-block:: yaml

 version: 2
 build:
  os: ubuntu-22.04
  tools:
  python: "3.12"
 sphinx:
  configuration: docs/source/conf.py
 python:
  install:
  - method: pip
   path: .
   extra_requirements:
   - dev
