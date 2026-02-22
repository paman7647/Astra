import os
import sys
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------
project = 'Astra Engine'
copyright = '2026, Aman Kumar Pandey'
author = 'Aman Kumar Pandey'
release = '0.0.2b10'
version = '0.0.1'

# -- Extensions --------------------------------------------------------
extensions = [
 'sphinx.ext.autodoc',
 'sphinx.ext.napoleon',
 'sphinx.ext.viewcode',
 'sphinx.ext.autosummary',
 'sphinx.ext.intersphinx',
]

# Autodoc settings
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_mock_imports = [
 'playwright',
 'qrcode',
 'PIL',
 'requests',
]

# Intersphinx mapping to Python stdlib docs
intersphinx_mapping = {
 'python': ('https://docs.python.org/3', None),
}

# Napoleon settings (Google-style docstrings)
napoleon_google_docstrings = True
napoleon_numpy_docstrings = False
napoleon_include_init_with_doc = True

# -- HTML output -------------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
templates_path = ['_templates']
exclude_patterns = []

html_theme_options = {
 'navigation_depth': 4,
 'collapse_navigation': False,
 'sticky_navigation': True,
 'style_external_links': True,
}

# Disable Sphinx footer and sourcelink
html_show_sphinx = False
html_show_sourcelink = False

# -- General -----------------------------------------------------------
add_module_names = False
toc_object_entries_show_parents = 'hide'

# Custom CSS registration
def setup(app):
    app.add_css_file('css/custom.css')
