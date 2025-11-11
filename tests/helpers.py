"""Custom test assertions and utilities for Wijjit tests.

This module provides domain-specific assertions and helper functions
for testing terminal UI components.
"""

import os
from pathlib import Path

from wijjit.terminal.ansi import strip_ansi, visible_length


def assert_renders_correctly(
    element,
    expected_width: int = None,
    expected_height: int = None,
    allow_empty_lines: bool = False,
):
    """Assert that an element renders with correct dimensions.

    Parameters
    ----------
    element : Element
        Element to test
    expected_width : int, optional
        Expected width of all lines
    expected_height : int, optional
        Expected number of lines
    allow_empty_lines : bool, optional
        Whether to allow empty lines, by default False

    Raises
    ------
    AssertionError
        If rendering doesn't match expectations
    """
    output = element.render()
    lines = output.split("\n") if output else []

    if expected_height is not None:
        assert len(lines) == expected_height, (
            f"Expected {expected_height} lines, got {len(lines)}\n"
            f"Output: {repr(output)}"
        )

    if expected_width is not None:
        for i, line in enumerate(lines):
            actual_width = visible_length(line)
            assert actual_width == expected_width, (
                f"Line {i} has width {actual_width}, expected {expected_width}\n"
                f"Line: {repr(line)}\n"
                f"Visible: {repr(strip_ansi(line))}"
            )

    if not allow_empty_lines:
        for i, line in enumerate(lines):
            visible = strip_ansi(line).strip()
            assert visible or line.strip(), f"Line {i} is empty or only whitespace"


def assert_ansi_preserved(text: str, expected_codes: list[str] = None):
    """Assert that ANSI codes are present and preserved in text.

    Parameters
    ----------
    text : str
        Text to check
    expected_codes : List[str], optional
        Specific ANSI codes that must be present

    Raises
    ------
    AssertionError
        If ANSI codes are missing
    """
    # Check that text differs from stripped version (has ANSI codes)
    stripped = strip_ansi(text)
    assert (
        text != stripped or not expected_codes
    ), "Expected ANSI codes but text has none"

    if expected_codes:
        for code in expected_codes:
            assert code in text, f"Expected ANSI code {repr(code)} not found in text"


def assert_layout_bounds(element, x: int, y: int, width: int, height: int):
    """Assert that element has correct layout bounds.

    Parameters
    ----------
    element : Element
        Element to check
    x : int
        Expected x position
    y : int
        Expected y position
    width : int
        Expected width
    height : int
        Expected height

    Raises
    ------
    AssertionError
        If bounds don't match
    """
    assert element.bounds is not None, "Element has no bounds set"
    assert element.bounds.x == x, f"Expected x={x}, got {element.bounds.x}"
    assert element.bounds.y == y, f"Expected y={y}, got {element.bounds.y}"
    assert (
        element.bounds.width == width
    ), f"Expected width={width}, got {element.bounds.width}"
    assert (
        element.bounds.height == height
    ), f"Expected height={height}, got {element.bounds.height}"


def assert_has_border(output: str, border_chars: str = None):
    """Assert that output contains border characters.

    Parameters
    ----------
    output : str
        Rendered output
    border_chars : str, optional
        Specific border characters to look for

    Raises
    ------
    AssertionError
        If no border is found
    """
    lines = output.split("\n")
    assert len(lines) >= 3, "Output too small to contain border"

    top_line = strip_ansi(lines[0])
    bottom_line = strip_ansi(lines[-1])

    if border_chars:
        assert any(
            char in top_line for char in border_chars
        ), f"Top line missing border characters: {repr(top_line)}"
        assert any(
            char in bottom_line for char in border_chars
        ), f"Bottom line missing border characters: {repr(bottom_line)}"
    else:
        # Check for common border characters
        border_set = {
            "─",
            "│",
            "┌",
            "┐",
            "└",
            "┘",
            "═",
            "║",
            "╔",
            "╗",
            "╚",
            "╝",
            "╭",
            "╮",
            "╰",
            "╯",
            "-",
            "|",
            "+",
        }
        assert any(
            char in border_set for char in top_line
        ), f"Top line has no border characters: {repr(top_line)}"


def assert_contains_text(output: str, expected: str, strip_ansi_codes: bool = True):
    """Assert that output contains expected text.

    Parameters
    ----------
    output : str
        Rendered output
    expected : str
        Expected text to find
    strip_ansi_codes : bool, optional
        Whether to strip ANSI codes before checking, by default True

    Raises
    ------
    AssertionError
        If text not found
    """
    search_in = strip_ansi(output) if strip_ansi_codes else output
    assert expected in search_in, (
        f"Expected text {repr(expected)} not found in output\n"
        f"Output: {repr(search_in)}"
    )


def assert_lines_equal(
    actual: str, expected: str, ignore_trailing_whitespace: bool = True
):
    """Assert that two multi-line strings are equal line-by-line.

    Parameters
    ----------
    actual : str
        Actual output
    expected : str
        Expected output
    ignore_trailing_whitespace : bool, optional
        Whether to ignore trailing whitespace, by default True

    Raises
    ------
    AssertionError
        If lines don't match
    """
    actual_lines = actual.split("\n")
    expected_lines = expected.split("\n")

    if ignore_trailing_whitespace:
        actual_lines = [line.rstrip() for line in actual_lines]
        expected_lines = [line.rstrip() for line in expected_lines]

    assert len(actual_lines) == len(expected_lines), (
        f"Line count mismatch: expected {len(expected_lines)}, got {len(actual_lines)}\n"
        f"Actual:\n{actual}\n\nExpected:\n{expected}"
    )

    for i, (actual_line, expected_line) in enumerate(
        zip(actual_lines, expected_lines, strict=True)
    ):
        assert actual_line == expected_line, (
            f"Line {i} mismatch:\n"
            f"  Actual:   {repr(actual_line)}\n"
            f"  Expected: {repr(expected_line)}"
        )


def assert_matches_golden(output: str, golden_file: str, update: bool = None):
    """Assert that output matches saved golden file.

    Set UPDATE_GOLDEN=1 environment variable to update golden files.

    Parameters
    ----------
    output : str
        Actual output
    golden_file : str
        Path to golden file (relative to tests/golden/)
    update : bool, optional
        Override environment variable to force update

    Raises
    ------
    AssertionError
        If output doesn't match golden file
    """
    if update is None:
        update = os.environ.get("UPDATE_GOLDEN", "0") == "1"

    golden_path = Path(__file__).parent / "golden" / golden_file

    if update:
        # Create directory if needed
        golden_path.parent.mkdir(parents=True, exist_ok=True)
        # Write golden file
        golden_path.write_text(output, encoding="utf-8")
        print(f"Updated golden file: {golden_file}")
    else:
        # Compare to golden file
        assert golden_path.exists(), (
            f"Golden file not found: {golden_file}\n"
            f"Set UPDATE_GOLDEN=1 to create it:\n"
            f"  UPDATE_GOLDEN=1 pytest {os.environ.get('PYTEST_CURRENT_TEST', 'test')}"
        )

        expected = golden_path.read_text(encoding="utf-8")
        assert output == expected, (
            f"Output doesn't match golden file: {golden_file}\n"
            f"Run with UPDATE_GOLDEN=1 to update:\n"
            f"  UPDATE_GOLDEN=1 pytest {os.environ.get('PYTEST_CURRENT_TEST', 'test')}\n"
            f"\nExpected:\n{expected}\n\nActual:\n{output}"
        )


def assert_focusable(element, should_be_focusable: bool = True):
    """Assert that element is focusable or not.

    Parameters
    ----------
    element : Element
        Element to check
    should_be_focusable : bool, optional
        Whether element should be focusable, by default True

    Raises
    ------
    AssertionError
        If focusability doesn't match expectation
    """
    if should_be_focusable:
        assert element.focusable, f"Element {element.id} should be focusable"
    else:
        assert not element.focusable, f"Element {element.id} should not be focusable"


def assert_element_has_id(element, expected_id: str = None):
    """Assert that element has an ID assigned.

    Parameters
    ----------
    element : Element
        Element to check
    expected_id : str, optional
        Expected ID value

    Raises
    ------
    AssertionError
        If element has no ID or ID doesn't match
    """
    assert element.id is not None, "Element has no ID assigned"
    if expected_id:
        assert (
            element.id == expected_id
        ), f"Expected element ID {repr(expected_id)}, got {repr(element.id)}"


def get_visible_lines(output: str) -> list[str]:
    """Get visible text lines from output (ANSI codes stripped).

    Parameters
    ----------
    output : str
        Output with potential ANSI codes

    Returns
    -------
    List[str]
        List of visible text lines
    """
    lines = output.split("\n")
    return [strip_ansi(line) for line in lines]


def get_line_widths(output: str) -> list[int]:
    """Get visible width of each line in output.

    Parameters
    ----------
    output : str
        Output with potential ANSI codes

    Returns
    -------
    List[int]
        List of visible widths
    """
    lines = output.split("\n")
    return [visible_length(line) for line in lines]


def print_debug_output(output: str, label: str = "Output"):
    """Print debug representation of output for test debugging.

    Parameters
    ----------
    output : str
        Output to debug
    label : str, optional
        Label for output, by default "Output"
    """
    print(f"\n{'='*60}")
    print(f"{label}:")
    print(f"{'='*60}")
    print(output)
    print(f"{'='*60}")
    print("Visible:")
    print(f"{'='*60}")
    for i, line in enumerate(output.split("\n")):
        visible = strip_ansi(line)
        width = visible_length(line)
        print(f"{i:2d} ({width:2d}): {repr(visible)}")
    print(f"{'='*60}\n")
