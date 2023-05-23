# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Pyexotel'
copyright = '2023, Udit Mittal'
author = 'Udit Mittal'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage', 'sphinx.ext.napoleon', 'sphinx_autodoc_typehints', 'sphinx.ext.autosummary', 'sphinx.ext.githubpages']

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']




# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_material'
html_theme_options = {
    'nav_title': 'Pyexotel',
    'nav_links' : [
        {
            "href": "exotel",
            "title": "Exotel",
            "internal": True
        },
        {
            "href": "schedule",
            "title": "Schedule",
            "internal": True
        },
        {
            "href": "retry",
            "title": "Retry",
            "internal": True
        },
        {
            "href": "exceptions",
            "title": "Exceptions",
            "internal": True
        },
        {
            "href": "validators",
            "title": "Validators",
            "internal": True
        },
    ],
'globaltoc_depth': 1
}
html_static_path = ['_static']
html_permalinks = True
html_sidebars = {
    "**": ["globaltoc.html", "localtoc.html", "searchbox.html"]
}

import os
import sys
sys.path.insert(0, os.path.abspath(".."))