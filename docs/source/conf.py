# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

print(os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../..'))

# -- Project information -----------------------------------------------------

project = 'pg-jsonapi'
copyright = '2019, Omar Zabaneh'
author = 'Omar Zabaneh'

# The full version, including alpha/beta/rc tags
release = '0.1.0.dev0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.todo',
              'sphinx.ext.viewcode',
              'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'
html_short_title = 'Home'
html_theme_options = {
    'description': 'Build JSON API v1.0 compliant RESTFul api for PostgreSQL backends. '
                   'Powered by asyncpgsa, SQLAlchemy Core, and marshmallow libraries.',
    'description_font_style': '',
    'page_width': '60%',
    'sidebar_collapse': False,
    'show_related': False,
    'fixed_sidebar': False,
    'github_user': 'zabano',
    'github_repo': 'pg-jsonapi',
    'github_type': 'star',
    'show_relbars': True,
    'show_powered_by': False,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
