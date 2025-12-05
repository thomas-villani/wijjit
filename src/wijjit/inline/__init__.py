"""Inline rendering module for CLI applications.

This module provides utilities for rendering Wijjit templates inline in
terminal scrollback, without using the alternate screen buffer. This is
useful for CLI tools that want styled output without full-screen mode.

Two main APIs are provided:

1. render_inline() - One-shot static rendering
2. InlineApp - Interactive inline with in-place updates
"""

from wijjit.inline.render import render_inline
from wijjit.inline.app import InlineApp

__all__ = ["render_inline", "InlineApp"]
