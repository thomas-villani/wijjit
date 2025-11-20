# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath('../../src'))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Wijjit'
copyright = '2025, Tom Villani, Ph.D.'
author = 'Tom Villani, Ph.D.'
release = '0.1.0'
version = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',         # Auto-generate API docs from docstrings
    'sphinx.ext.autosummary',     # Summary tables for API reference
    'sphinx.ext.autosectionlabel',# Unique labels per section
    'sphinx.ext.duration',        # Report build timings
    'sphinx.ext.napoleon',        # Support for NumPy-style docstrings
    'sphinx.ext.viewcode',        # Add links to source code
    'sphinx.ext.intersphinx',     # Link to other documentation
    'sphinx.ext.todo',            # Support for TODO items
    'sphinx.ext.coverage',        # Check documentation coverage
    'sphinx_copybutton',          # Copy button for code blocks
    'myst_parser',                # Optional Markdown support
]

# Autosummary/autodoc defaults
autosummary_generate = True
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autodoc_typehints = 'description'

# Autosectionlabel configuration
autosectionlabel_prefix_document = True

# Napoleon settings (for NumPy-style docstrings)
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = True
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'jinja2': ('https://jinja.palletsprojects.com/en/3.1.x/', None),
    'prompt_toolkit': ('https://python-prompt-toolkit.readthedocs.io/en/master/', None),
    'rich': ('https://rich.readthedocs.io/en/stable/', None),
}

# MyST configuration
myst_enable_extensions = [
    'colon_fence',
    'deflist',
]
myst_heading_anchors = 4

templates_path = ['_templates']
exclude_patterns = []

# The suffix(es) of source filenames
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master toctree document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# Use Read the Docs theme (install with: pip install sphinx-rtd-theme)
html_theme = 'sphinx_rtd_theme'
html_title = 'Wijjit Documentation'

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False
}

html_static_path = ['_static']

# Custom sidebar templates
html_sidebars = {
    '**': [
        'globaltoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
    ]
}

# Output file base name for HTML help builder
htmlhelp_basename = 'wijjitdoc'

# -- Options for LaTeX output ------------------------------------------------
latex_elements = {}

# Grouping the document tree into LaTeX files
latex_documents = [
    (master_doc, 'wijjit.tex', 'Wijjit Documentation',
     'Tom Villani, Ph.D.', 'manual'),
]

# -- Options for manual page output ------------------------------------------
man_pages = [
    (master_doc, 'wijjit', 'Wijjit Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------
texinfo_documents = [
    (master_doc, 'wijjit', 'Wijjit Documentation',
     author, 'wijjit', 'Flask for the Console - A declarative TUI framework for Python.',
     'Miscellaneous'),
]

# -- Extension configuration -------------------------------------------------
todo_include_todos = True
