"""Text processing utilities for Wijjit applications.

This module provides ANSI-aware text manipulation utilities including
text wrapping with word boundary detection while preserving ANSI escape codes.
"""

from .terminal.ansi import clip_to_width, strip_ansi, visible_length


def is_wrap_boundary(char: str) -> bool:
    """Check if a character is a valid wrap boundary for line wrapping.

    Parameters
    ----------
    char : str
        Character to check

    Returns
    -------
    bool
        True if character is a wrap boundary (space, hyphen, or punctuation)

    Notes
    -----
    Smart word boundary detection for text wrapping.
    Allows breaking at spaces, hyphens, and common punctuation marks.

    Examples
    --------
    >>> is_wrap_boundary(' ')
    True
    >>> is_wrap_boundary('-')
    True
    >>> is_wrap_boundary('a')
    False
    >>> is_wrap_boundary('.')
    True
    """
    if not char:
        return False

    # Spaces are always wrap boundaries
    if char.isspace():
        return True

    # Hyphens allow wrapping after them
    if char == "-":
        return True

    # Common punctuation marks
    punctuation = ".,;:!?)]}\"'"
    if char in punctuation:
        return True

    return False


def wrap_text(text: str, width: int) -> list[str]:
    """Wrap a single line of text into multiple segments based on width.

    This function wraps text to the specified width while preserving ANSI
    escape codes. It uses smart word boundary detection to break at spaces,
    hyphens, and punctuation when possible, falling back to hard breaks at
    width boundaries when no suitable break point is found.

    Parameters
    ----------
    text : str
        Text to wrap (may contain ANSI escape codes)
    width : int
        Maximum width for each segment

    Returns
    -------
    list of str
        List of wrapped text segments, preserving ANSI codes

    Notes
    -----
    - Empty text returns a single empty string segment
    - Text shorter than width returns as-is in a single-element list
    - ANSI escape codes are preserved and don't count toward visible length
    - Smart word boundary detection prefers breaking at:
      1. Spaces
      2. Hyphens
      3. Punctuation marks
    - Falls back to hard break at width if no boundary found

    Examples
    --------
    Basic wrapping without ANSI codes:

    >>> wrap_text("Hello world this is a test", 10)
    ['Hello ', 'world this', ' is a test']

    Wrapping with ANSI codes (codes are preserved):

    >>> from wijjit.terminal.ansi import ANSIColor
    >>> text = f"{ANSIColor.RED}Hello{ANSIColor.RESET} world"
    >>> segments = wrap_text(text, 8)
    >>> # ANSI codes preserved, visible length respected

    Empty or short text:

    >>> wrap_text("", 10)
    ['']
    >>> wrap_text("Short", 10)
    ['Short']
    """
    if width <= 0:
        return [""]

    # Empty text returns single empty segment
    if not text:
        return [""]

    # Calculate visible length
    vis_len = visible_length(text)

    # If text fits within width, return as-is
    if vis_len <= width:
        return [text]

    # Text needs wrapping
    segments = []
    remaining = text

    while remaining:
        vis_len = visible_length(remaining)

        if vis_len <= width:
            # Remaining text fits
            segments.append(remaining)
            break

        # Find best wrap point within width
        # Scan through the visible characters to find last boundary before width
        last_boundary_vis = None
        last_boundary_actual = None

        # Strip ANSI to find visible character positions
        stripped = strip_ansi(remaining)

        # Build mapping of visible positions to actual positions
        # This accounts for ANSI codes in the original string
        for i, char in enumerate(stripped):
            if i >= width:
                break

            # Check if this is a wrap boundary
            if is_wrap_boundary(char):
                last_boundary_vis = i + 1  # Break after the boundary char
                last_boundary_actual = i + 1

        # Decide where to break
        if last_boundary_actual is not None and last_boundary_actual < len(stripped):
            # Found a wrap boundary within width
            # Use clip_to_width to get the segment with ANSI codes preserved
            segment = clip_to_width(remaining, last_boundary_vis, ellipsis="")
            segments.append(segment)

            # Calculate actual position in original string for the split
            # clip_to_width returns the string up to the visible width
            actual_cut_pos = len(segment)

            # Skip past the segment and remove leading spaces
            remaining = remaining[actual_cut_pos:].lstrip()

        else:
            # No wrap boundary found, force break at width
            segment = clip_to_width(remaining, width, ellipsis="")
            segments.append(segment)

            # Calculate actual position to cut
            actual_cut_pos = len(segment)
            remaining = remaining[actual_cut_pos:]

    return segments if segments else [""]
