"""Template rendering with Jinja2 for Wijjit applications.

This module provides a renderer that processes Jinja2 templates with
custom extensions and filters for terminal UI rendering.
"""

import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, DictLoader, Template


class Renderer:
    """Template renderer using Jinja2.

    This class manages Jinja2 template rendering with support for
    both string templates and file-based templates.

    Parameters
    ----------
    template_dir : str, optional
        Directory containing template files
    autoescape : bool, optional
        Whether to enable autoescaping (default: False for terminal output)

    Attributes
    ----------
    env : jinja2.Environment
        The Jinja2 environment
    _string_templates : dict
        Cache of string templates
    """

    def __init__(self, template_dir: Optional[str] = None, autoescape: bool = False):
        # Create loader based on template_dir
        if template_dir and os.path.isdir(template_dir):
            loader = FileSystemLoader(template_dir)
        else:
            # Use DictLoader for string templates
            loader = DictLoader({})

        # Create Jinja2 environment
        self.env = Environment(
            loader=loader,
            autoescape=autoescape,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Cache for string templates
        self._string_templates: Dict[str, Template] = {}

        # Add custom filters
        self._setup_filters()

    def _setup_filters(self) -> None:
        """Set up custom Jinja2 filters for terminal rendering."""
        # Add common filters
        self.env.filters['upper'] = str.upper
        self.env.filters['lower'] = str.lower
        self.env.filters['title'] = str.title

    def render_string(self, template_string: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a template from a string.

        Parameters
        ----------
        template_string : str
            The template string to render
        context : dict, optional
            Context variables for template rendering

        Returns
        -------
        str
            The rendered template output
        """
        context = context or {}

        # Check cache first
        if template_string in self._string_templates:
            template = self._string_templates[template_string]
        else:
            # Compile and cache
            template = self.env.from_string(template_string)
            self._string_templates[template_string] = template

        return template.render(**context)

    def render_file(self, template_name: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Render a template from a file.

        Parameters
        ----------
        template_name : str
            Name of the template file
        context : dict, optional
            Context variables for template rendering

        Returns
        -------
        str
            The rendered template output

        Raises
        ------
        jinja2.TemplateNotFound
            If the template file doesn't exist
        """
        context = context or {}
        template = self.env.get_template(template_name)
        return template.render(**context)

    def add_filter(self, name: str, func: callable) -> None:
        """Add a custom filter to the Jinja2 environment.

        Parameters
        ----------
        name : str
            Name of the filter
        func : callable
            Filter function
        """
        self.env.filters[name] = func

    def add_global(self, name: str, value: Any) -> None:
        """Add a global variable to the Jinja2 environment.

        Parameters
        ----------
        name : str
            Name of the global variable
        value : Any
            Value of the global variable
        """
        self.env.globals[name] = value

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._string_templates.clear()
