"""Template system for declarative UI definition.

This module provides Jinja2 extensions for creating UI layouts using
template syntax.
"""

from .tags import (
    ButtonExtension,
    FrameExtension,
    HStackExtension,
    TextInputExtension,
    VStackExtension,
)

__all__ = [
    "FrameExtension",
    "VStackExtension",
    "HStackExtension",
    "TextInputExtension",
    "ButtonExtension",
]
