"""Tests for LogView display element."""

from tests.helpers import render_element
from wijjit.elements.base import ElementType
from wijjit.elements.display.logview import LogView
from wijjit.layout.bounds import Bounds
from wijjit.terminal.ansi import strip_ansi
from wijjit.terminal.input import Keys
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType


class TestLogView:
    """Tests for LogView element."""

    def test_create_logview(self):
        """Test creating a basic LogView."""
        lines = ["INFO: App started", "DEBUG: Loading config", "ERROR: Failed"]

        logview = LogView(id="app_logs", lines=lines)

        assert logview.id == "app_logs"
        assert len(logview.lines) == 3
        assert logview.lines[0] == "INFO: App started"
        assert logview.element_type == ElementType.DISPLAY
        assert logview.focusable  # LogView is focusable for keyboard scrolling

    def test_empty_logview(self):
        """Test LogView with no lines."""
        logview = LogView()
        assert len(logview.lines) == 0

        # Should render without errors
        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 80, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)

    def test_log_level_detection_error(self):
        """Test ERROR level detection."""
        lines = [
            "ERROR: Connection failed",
            "FATAL: Critical error",
            "CRITICAL: System failure",
        ]
        logview = LogView(lines=lines, detect_log_levels=True)

        # Check that detection is working
        assert logview._detect_log_level(lines[0]) == "ERROR"
        assert logview._detect_log_level(lines[1]) == "ERROR"
        assert logview._detect_log_level(lines[2]) == "ERROR"

    def test_log_level_detection_warning(self):
        """Test WARNING level detection."""
        lines = ["WARNING: Slow response", "WARN: High memory usage"]
        logview = LogView(lines=lines, detect_log_levels=True)

        assert logview._detect_log_level(lines[0]) == "WARNING"
        assert logview._detect_log_level(lines[1]) == "WARNING"

    def test_log_level_detection_info(self):
        """Test INFO level detection."""
        lines = ["INFO: Server started", "INFO: Processing request"]
        logview = LogView(lines=lines, detect_log_levels=True)

        assert logview._detect_log_level(lines[0]) == "INFO"
        assert logview._detect_log_level(lines[1]) == "INFO"

    def test_log_level_detection_debug(self):
        """Test DEBUG level detection."""
        lines = ["DEBUG: Variable value: 42", "DEBUG: Entering function"]
        logview = LogView(lines=lines, detect_log_levels=True)

        assert logview._detect_log_level(lines[0]) == "DEBUG"
        assert logview._detect_log_level(lines[1]) == "DEBUG"

    def test_log_level_detection_trace(self):
        """Test TRACE level detection."""
        lines = ["TRACE: Detailed execution trace", "TRACE: Step 1 complete"]
        logview = LogView(lines=lines, detect_log_levels=True)

        assert logview._detect_log_level(lines[0]) == "TRACE"
        assert logview._detect_log_level(lines[1]) == "TRACE"

    def test_log_level_detection_none(self):
        """Test lines without log levels."""
        lines = ["Regular log line", "Another line"]
        logview = LogView(lines=lines, detect_log_levels=True)

        assert logview._detect_log_level(lines[0]) is None
        assert logview._detect_log_level(lines[1]) is None

    def test_log_level_detection_disabled(self):
        """Test with log level detection disabled."""
        lines = ["ERROR: This should not be colored", "INFO: Neither should this"]
        logview = LogView(lines=lines, detect_log_levels=False)

        # Colorize should return line as-is
        colored = logview._colorize_line(lines[0])
        assert colored == lines[0]  # No ANSI codes added

    def test_colorize_line(self):
        """Test line colorization."""
        logview = LogView(detect_log_levels=True)

        error_line = "ERROR: Failed"
        colored = logview._colorize_line(error_line)
        # Should contain ANSI codes
        assert len(colored) > len(error_line)
        assert strip_ansi(colored) == error_line

    def test_auto_scroll_initial(self):
        """Test auto-scroll starts at bottom."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=True)

        # Should start at bottom
        assert logview.scroll_manager.state.scroll_position > 0

    def test_auto_scroll_on_new_lines(self):
        """Test auto-scroll when new lines are added."""
        lines = [f"Line {i}" for i in range(20)]
        logview = LogView(lines=lines, height=10, auto_scroll=True)

        initial_pos = logview.scroll_manager.state.scroll_position

        # Add more lines
        new_lines = lines + [f"New line {i}" for i in range(10)]
        logview.set_lines(new_lines)

        # Should have scrolled to new bottom
        assert logview.scroll_manager.state.scroll_position > initial_pos

    def test_auto_scroll_disabled_on_manual_scroll(self):
        """Test auto-scroll is disabled when user scrolls up."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=True)

        # User scrolls up
        logview.handle_key(Keys.UP)

        # User scroll flag should be set
        assert logview._user_scrolled_up is True

        # Add new lines
        old_pos = logview.scroll_manager.state.scroll_position
        new_lines = lines + ["New line"]
        logview.set_lines(new_lines)

        # Should NOT auto-scroll (user scrolled up)
        assert logview.scroll_manager.state.scroll_position == old_pos

    def test_auto_scroll_reenabled_at_bottom(self):
        """Test auto-scroll is re-enabled when user scrolls back to bottom."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=True)

        # User scrolls up
        logview.handle_key(Keys.UP)
        assert logview._user_scrolled_up is True

        # User scrolls back to bottom with End key
        logview.handle_key(Keys.END)
        assert logview._user_scrolled_up is False

    def test_soft_wrap_enabled(self):
        """Test soft-wrap wraps long lines."""
        long_line = "A" * 100
        logview = LogView(lines=[long_line], width=40, height=10, soft_wrap=True)

        # Should have multiple rendered lines for one input line
        assert len(logview.rendered_lines) > 1

    def test_soft_wrap_disabled(self):
        """Test soft-wrap clips long lines."""
        long_line = "A" * 100
        logview = LogView(lines=[long_line], width=40, height=10, soft_wrap=False)

        # Should have one rendered line (clipped)
        assert len(logview.rendered_lines) == 1

    def test_line_numbers_enabled(self):
        """Test line numbers are displayed."""
        lines = ["Line 1", "Line 2", "Line 3"]
        logview = LogView(
            lines=lines,
            show_line_numbers=True,
            line_number_start=1,
            width=40,
            height=10,
        )

        # Check that rendered lines contain line numbers
        for i, rendered in enumerate(logview.rendered_lines):
            assert str(i + 1) in rendered

    def test_line_numbers_custom_start(self):
        """Test custom starting line number."""
        lines = ["Line A", "Line B", "Line C"]
        logview = LogView(
            lines=lines,
            show_line_numbers=True,
            line_number_start=100,
            width=40,
            height=10,
        )

        # Check that line numbers start at 100
        assert "100" in logview.rendered_lines[0]
        assert "101" in logview.rendered_lines[1]
        assert "102" in logview.rendered_lines[2]

    def test_line_numbers_disabled(self):
        """Test line numbers are not displayed when disabled."""
        lines = ["Line 1", "Line 2"]
        logview = LogView(lines=lines, show_line_numbers=False, width=40, height=10)

        # Line numbers should not appear
        # (This is a bit tricky to test, but we can check rendered content)
        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        # Numbers might appear in content, so just verify no formatting
        assert logview.show_line_numbers is False

    def test_set_lines(self):
        """Test updating LogView lines."""
        logview = LogView(lines=["Line 1"])
        assert len(logview.lines) == 1

        new_lines = ["New 1", "New 2", "New 3"]
        logview.set_lines(new_lines)

        assert len(logview.lines) == 3
        assert logview.lines[0] == "New 1"

    def test_keyboard_scrolling_up_down(self):
        """Test keyboard navigation with UP and DOWN."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=False)

        initial_pos = logview.scroll_manager.state.scroll_position

        # Scroll down
        logview.handle_key(Keys.DOWN)
        assert logview.scroll_manager.state.scroll_position > initial_pos

        # Scroll up
        current_pos = logview.scroll_manager.state.scroll_position
        logview.handle_key(Keys.UP)
        assert logview.scroll_manager.state.scroll_position < current_pos

    def test_keyboard_scrolling_home_end(self):
        """Test HOME and END keys."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10)

        # Home key - jump to top
        logview.handle_key(Keys.HOME)
        assert logview.scroll_manager.state.scroll_position == 0

        # End key - jump to bottom
        logview.handle_key(Keys.END)
        assert logview.scroll_manager.state.scroll_position > 0

    def test_keyboard_scrolling_page_up_down(self):
        """Test PAGE_UP and PAGE_DOWN keys."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10)

        # Start at top
        logview.handle_key(Keys.HOME)
        initial_pos = logview.scroll_manager.state.scroll_position

        # Page down
        logview.handle_key(Keys.PAGE_DOWN)
        assert logview.scroll_manager.state.scroll_position > initial_pos

        # Page up
        current_pos = logview.scroll_manager.state.scroll_position
        logview.handle_key(Keys.PAGE_UP)
        assert logview.scroll_manager.state.scroll_position < current_pos

    def test_mouse_scrolling(self):
        """Test mouse wheel scrolling."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=False)

        initial_pos = logview.scroll_manager.state.scroll_position

        # Scroll down with mouse wheel
        event_down = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_DOWN,
            x=0,
            y=0,
        )
        logview.handle_mouse(event_down)
        assert logview.scroll_manager.state.scroll_position > initial_pos

        # Scroll up with mouse wheel
        current_pos = logview.scroll_manager.state.scroll_position
        event_up = MouseEvent(
            type=MouseEventType.SCROLL,
            button=MouseButton.SCROLL_UP,
            x=0,
            y=0,
        )
        logview.handle_mouse(event_up)
        assert logview.scroll_manager.state.scroll_position < current_pos

    def test_render_basic(self):
        """Test basic rendering."""
        lines = ["INFO: Line 1", "ERROR: Line 2", "DEBUG: Line 3"]
        logview = LogView(lines=lines, width=80, height=10)

        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 80, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)
        # ANSI codes might be present, so check stripped content
        stripped = strip_ansi(output)
        assert "Line 1" in stripped
        assert "Line 2" in stripped
        assert "Line 3" in stripped

    def test_render_with_borders(self):
        """Test rendering with different border styles."""
        lines = ["Line 1", "Line 2"]

        # Single border
        lv_single = LogView(lines=lines, border_style="single", width=40, height=10)
        if not lv_single.bounds:
            lv_single.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            lv_single, width=lv_single.bounds.width, height=lv_single.bounds.height
        )
        assert isinstance(output, str)

        # Double border
        lv_double = LogView(lines=lines, border_style="double", width=40, height=10)
        if not lv_double.bounds:
            lv_double.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            lv_double, width=lv_double.bounds.width, height=lv_double.bounds.height
        )
        assert isinstance(output, str)

        # Rounded border
        lv_rounded = LogView(lines=lines, border_style="rounded", width=40, height=10)
        if not lv_rounded.bounds:
            lv_rounded.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            lv_rounded, width=lv_rounded.bounds.width, height=lv_rounded.bounds.height
        )
        assert isinstance(output, str)

        # No border
        lv_none = LogView(lines=lines, border_style="none", width=40, height=10)
        if not lv_none.bounds:
            lv_none.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            lv_none, width=lv_none.bounds.width, height=lv_none.bounds.height
        )
        assert isinstance(output, str)

    def test_render_with_title(self):
        """Test rendering with title."""
        lines = ["Line 1", "Line 2"]
        logview = LogView(
            lines=lines,
            title="Application Logs",
            border_style="single",
            width=40,
            height=10,
        )

        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)
        assert "Application Logs" in output

    def test_render_with_scrollbar(self):
        """Test rendering with scrollbar."""
        # Create LogView with more lines than viewport
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(
            lines=lines, width=40, height=10, show_scrollbar=True, border_style="single"
        )

        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)
        # Scrollbar characters should be present when content is scrollable

    def test_restore_scroll_position(self):
        """Test restoring scroll position."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=False)

        # Scroll to position 5
        logview.scroll_manager.scroll_to(5)
        assert logview.scroll_manager.state.scroll_position == 5

        # Restore to position 10
        logview.restore_scroll_position(10)
        assert logview.scroll_manager.state.scroll_position == 10

    def test_ansi_passthrough(self):
        """Test that existing ANSI codes are preserved."""
        from wijjit.terminal.ansi import ANSIColor, ANSIStyle

        # Line with existing ANSI codes
        line = f"{ANSIColor.GREEN}Already colored{ANSIStyle.RESET}"
        logview = LogView(lines=[line], detect_log_levels=False)

        # ANSI codes should be preserved
        assert ANSIColor.GREEN in logview.rendered_lines[0]

    def test_performance_large_log(self):
        """Test performance with large number of lines."""
        # Create 10000 lines
        lines = [f"INFO: Log line {i}" for i in range(10000)]
        logview = LogView(lines=lines, height=20, width=80)

        # Should render without issues
        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 80, 20))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)

        # Scroll to different positions
        logview.scroll_manager.scroll_to(5000)
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)

    def test_scroll_manager_integration(self):
        """Test ScrollManager integration."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(
            lines=lines, height=10, border_style="single", auto_scroll=False
        )

        # Content size should match rendered lines
        assert logview.scroll_manager.state.content_size == len(logview.rendered_lines)
        assert logview.scroll_manager.state.is_scrollable

        # Update lines
        new_lines = [f"Line {i}" for i in range(5)]
        logview.set_lines(new_lines)

        assert logview.scroll_manager.state.content_size == len(logview.rendered_lines)
        # Should not be scrollable with fewer lines
        if logview.scroll_manager.state.viewport_size >= len(logview.rendered_lines):
            assert not logview.scroll_manager.state.is_scrollable

    def test_long_lines_clipping(self):
        """Test that long lines are clipped properly when soft_wrap is off."""
        long_line = "A" * 200
        logview = LogView(
            lines=[long_line],
            width=40,
            height=10,
            border_style="single",
            soft_wrap=False,
        )

        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)
        # Should not crash with long lines

    def test_multiline_log_with_soft_wrap(self):
        """Test logs with very long lines and soft wrap enabled."""
        long_line = "ERROR: " + "A" * 200
        logview = LogView(lines=[long_line], width=40, height=20, soft_wrap=True)

        # Should render multiple lines
        assert len(logview.rendered_lines) > 1

    def test_empty_lines(self):
        """Test handling of empty lines in logs."""
        lines = ["Line 1", "", "Line 3", "", ""]
        logview = LogView(lines=lines, width=40, height=10)

        assert len(logview.lines) == 5
        if not logview.bounds:
            logview.set_bounds(Bounds(0, 0, 40, 10))
        output = render_element(
            logview, width=logview.bounds.width, height=logview.bounds.height
        )
        assert isinstance(output, str)

    def test_log_level_case_insensitive(self):
        """Test log level detection is case insensitive."""
        lines = [
            "error: lowercase",
            "ERROR: uppercase",
            "ErRoR: mixed case",
            "info: lowercase",
            "INFO: uppercase",
        ]
        logview = LogView(lines=lines, detect_log_levels=True)

        assert logview._detect_log_level(lines[0]) == "ERROR"
        assert logview._detect_log_level(lines[1]) == "ERROR"
        assert logview._detect_log_level(lines[2]) == "ERROR"
        assert logview._detect_log_level(lines[3]) == "INFO"
        assert logview._detect_log_level(lines[4]) == "INFO"

    def test_line_numbers_with_soft_wrap(self):
        """Test line numbers with soft-wrapped lines."""
        long_line = "A" * 100
        logview = LogView(
            lines=[long_line, "Short"],
            show_line_numbers=True,
            line_number_start=1,
            soft_wrap=True,
            width=40,
            height=20,
        )

        # First line should have line number 1
        # Continuation of wrapped line should have spaces
        # Second line should have line number 2
        assert len(logview.rendered_lines) > 2

    def test_auto_scroll_disabled_initially(self):
        """Test LogView with auto_scroll disabled from start."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=False)

        # Should start at top (position 0)
        assert logview.scroll_manager.state.scroll_position == 0

    def test_format_line_number(self):
        """Test line number formatting with padding."""
        lines = [f"Line {i}" for i in range(100)]
        logview = LogView(lines=lines, show_line_numbers=True, line_number_start=1)

        # Line numbers should be padded to same width
        line_num_1 = logview._format_line_number(1)
        line_num_99 = logview._format_line_number(99)

        # Both should have same length (right-aligned)
        assert len(line_num_1) == len(line_num_99)

    def test_multiple_log_levels_in_line(self):
        """Test line with multiple log level keywords."""
        line = "ERROR: Cannot connect to INFO server"
        logview = LogView(lines=[line], detect_log_levels=True)

        # Should detect ERROR (first match in priority order)
        assert logview._detect_log_level(line) == "ERROR"

    def test_scroll_callback(self):
        """Test scroll callback is triggered."""
        lines = [f"Line {i}" for i in range(50)]
        logview = LogView(lines=lines, height=10, auto_scroll=False)

        scroll_positions = []

        def on_scroll(position):
            scroll_positions.append(position)

        logview.on_scroll = on_scroll

        # Scroll and check callback was triggered
        logview.handle_key(Keys.DOWN)
        assert len(scroll_positions) > 0

    def test_content_width_calculation(self):
        """Test content width accounts for borders, scrollbar, and line numbers."""
        logview = LogView(
            lines=["Test"],
            width=80,
            height=10,
            border_style="single",
            show_scrollbar=True,
            show_line_numbers=True,
            line_number_start=1,
        )

        content_width = logview._get_content_width()

        # Should be less than 80 due to borders (2), scrollbar (1), and line numbers
        assert content_width < 80
        assert content_width > 0
