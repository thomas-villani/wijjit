"""Template system for declarative UI definition.

This module provides Jinja2 extensions for creating UI layouts using
template syntax.
"""

from .tags import (
    ButtonExtension,
    CodeBlockExtension,
    FrameExtension,
    HStackExtension,
    MarkdownExtension,
    SelectExtension,
    TableExtension,
    TextAreaExtension,
    TextInputExtension,
    TreeExtension,
    VStackExtension,
)

__all__ = [
    "FrameExtension",
    "VStackExtension",
    "HStackExtension",
    "TextInputExtension",
    "ButtonExtension",
    "SelectExtension",
    "TableExtension",
    "TreeExtension",
    "MarkdownExtension",
    "CodeBlockExtension",
    "TextAreaExtension",
]
