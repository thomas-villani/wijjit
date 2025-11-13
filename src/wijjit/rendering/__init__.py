"""Rendering subsystem for Wijjit.

This package provides the cell-based rendering infrastructure including
paint contexts, ANSI adapters, and rendering utilities.
"""

from wijjit.rendering.ansi_adapter import ansi_string_to_cells, cells_to_ansi
from wijjit.rendering.paint_context import PaintContext

__all__ = [
    "PaintContext",
    "ansi_string_to_cells",
    "cells_to_ansi",
]
