"""Helper utilities for Wijjit applications.

This module provides utility functions for common tasks like loading
filesystem trees, converting data formats, etc.
"""

import fnmatch
from collections.abc import Callable
from pathlib import Path
from typing import Any


def load_filesystem_tree(
    root_path: str | Path,
    max_depth: int | None = None,
    show_hidden: bool = False,
    include_files: bool = True,
    include_metadata: bool = True,
    exclude: list[str] | None = None,
    filter_func: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    """Load a filesystem directory structure as a tree.

    Recursively scans a directory and returns a nested dictionary structure
    suitable for use with the Tree display element.

    Parameters
    ----------
    root_path : str or Path
        Root directory to scan
    max_depth : int, optional
        Maximum depth to traverse (None for unlimited)
    show_hidden : bool
        Include hidden files and directories (default: False)
    include_files : bool
        Include files in the tree (default: True)
    include_metadata : bool
        Include file size and modification time (default: True)
    exclude : list of str, optional
        List of glob patterns to exclude (e.g., ["*.pyc", "__pycache__"])
    filter_func : callable, optional
        Custom filter function that takes a Path and returns True to include

    Returns
    -------
    dict
        Tree structure with keys:
        - label: Display name
        - value: Full path as string
        - type: "folder" or "file"
        - children: List of child nodes (for folders)
        - size: Human-readable size (if include_metadata=True and is file)
        - mtime: Modification time (if include_metadata=True)

    Examples
    --------
    Basic usage:

        from wijjit.helpers import load_filesystem_tree

        tree_data = load_filesystem_tree("/path/to/dir")

    With options:

        tree_data = load_filesystem_tree(
            "/path/to/dir",
            max_depth=3,
            show_hidden=False,
            exclude=["*.pyc", "*.pyo", "__pycache__", ".git"]
        )

    Use with Tree element:

        app = Wijjit(initial_state={
            "file_tree": load_filesystem_tree("./src"),
            "expanded_nodes": [],
        })
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root_path}")

    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root_path}")

    def _should_include(path: Path) -> bool:
        """Check if path should be included based on filters."""
        # Check hidden files
        if not show_hidden and path.name.startswith("."):
            return False

        # Check exclude patterns
        if exclude:
            for pattern in exclude:
                if fnmatch.fnmatch(path.name, pattern):
                    return False

        # Check custom filter
        if filter_func and not filter_func(path):
            return False

        return True

    def _format_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        size_float: float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024.0:
                if unit == "B":
                    return f"{int(size_float)} {unit}"
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} PB"

    def _build_tree(path: Path, depth: int = 0) -> dict[str, Any]:
        """Recursively build tree structure."""
        node: dict[str, Any] = {
            "label": path.name if path != root else path.name or str(path),
            "value": str(path),
            "type": "folder" if path.is_dir() else "file",
        }

        # Add metadata if requested
        if include_metadata:
            try:
                stat = path.stat()
                if path.is_file():
                    node["size"] = _format_size(stat.st_size)
                # Could add mtime if needed:
                # node["mtime"] = stat.st_mtime
            except (OSError, PermissionError):
                # Skip metadata if we can't access it
                pass

        # Recursively process children if this is a directory
        if path.is_dir():
            # Check depth limit
            if max_depth is not None and depth >= max_depth:
                return node

            children = []
            try:
                # Get all items in directory
                items = sorted(
                    path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
                )

                for item in items:
                    # Apply filters
                    if not _should_include(item):
                        continue

                    # Skip files if not including them
                    if item.is_file() and not include_files:
                        continue

                    # Recursively build child node
                    child_node = _build_tree(item, depth + 1)
                    children.append(child_node)

            except PermissionError:
                # Can't read directory, skip children
                pass

            if children:
                node["children"] = children

        return node

    return _build_tree(root)
