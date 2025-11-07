"""Tests for terminal screen management."""

from io import StringIO
import pytest

from wijjit.terminal.screen import ScreenManager, alternate_screen
from wijjit.terminal.ansi import ANSIScreen, ANSICursor


class TestScreenManager:
    """Tests for ScreenManager class."""

    def test_init_default_output(self):
        """Test ScreenManager initialization with default output."""
        manager = ScreenManager()
        assert manager.output is not None
        assert not manager.in_alternate_buffer
        assert not manager._cursor_hidden

    def test_init_custom_output(self):
        """Test ScreenManager initialization with custom output."""
        output = StringIO()
        manager = ScreenManager(output)
        assert manager.output is output

    def test_enter_alternate_buffer(self):
        """Test entering alternate buffer."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.enter_alternate_buffer()

        assert manager.in_alternate_buffer
        assert ANSIScreen.alternate_buffer_on() in output.getvalue()

    def test_enter_alternate_buffer_idempotent(self):
        """Test entering alternate buffer multiple times."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.enter_alternate_buffer()
        first_output = output.getvalue()

        manager.enter_alternate_buffer()
        second_output = output.getvalue()

        # Should not write the code again
        assert first_output == second_output

    def test_exit_alternate_buffer(self):
        """Test exiting alternate buffer."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.enter_alternate_buffer()
        output.truncate(0)  # Clear the buffer
        output.seek(0)

        manager.exit_alternate_buffer()

        assert not manager.in_alternate_buffer
        assert ANSIScreen.alternate_buffer_off() in output.getvalue()

    def test_exit_alternate_buffer_when_not_in(self):
        """Test exiting alternate buffer when not in it."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.exit_alternate_buffer()

        # Should not write anything
        assert output.getvalue() == ''

    def test_clear(self):
        """Test clearing the screen."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.clear()

        assert ANSIScreen.clear() in output.getvalue()

    def test_clear_line(self):
        """Test clearing the current line."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.clear_line()

        assert ANSIScreen.clear_line() in output.getvalue()

    def test_move_cursor(self):
        """Test moving the cursor."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.move_cursor(10, 20)

        assert ANSICursor.position(10, 20) in output.getvalue()

    def test_hide_cursor(self):
        """Test hiding the cursor."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.hide_cursor()

        assert manager._cursor_hidden
        assert ANSICursor.hide() in output.getvalue()

    def test_hide_cursor_idempotent(self):
        """Test hiding cursor multiple times."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.hide_cursor()
        first_output = output.getvalue()

        manager.hide_cursor()
        second_output = output.getvalue()

        # Should not write the code again
        assert first_output == second_output

    def test_show_cursor(self):
        """Test showing the cursor."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.hide_cursor()
        output.truncate(0)
        output.seek(0)

        manager.show_cursor()

        assert not manager._cursor_hidden
        assert ANSICursor.show() in output.getvalue()

    def test_show_cursor_when_not_hidden(self):
        """Test showing cursor when not hidden."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.show_cursor()

        # Should not write anything
        assert output.getvalue() == ''

    def test_write(self):
        """Test writing text."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.write('Hello, World!')

        assert output.getvalue() == 'Hello, World!'

    def test_cleanup_exits_alternate_buffer(self):
        """Test cleanup exits alternate buffer."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.enter_alternate_buffer()
        output.truncate(0)
        output.seek(0)

        manager.cleanup()

        assert not manager.in_alternate_buffer
        assert ANSIScreen.alternate_buffer_off() in output.getvalue()

    def test_cleanup_shows_cursor(self):
        """Test cleanup shows cursor."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.hide_cursor()
        output.truncate(0)
        output.seek(0)

        manager.cleanup()

        assert not manager._cursor_hidden
        assert ANSICursor.show() in output.getvalue()

    def test_cleanup_full(self):
        """Test full cleanup with alternate buffer and hidden cursor."""
        output = StringIO()
        manager = ScreenManager(output)

        manager.enter_alternate_buffer()
        manager.hide_cursor()
        output.truncate(0)
        output.seek(0)

        manager.cleanup()

        result = output.getvalue()
        assert ANSICursor.show() in result
        assert ANSIScreen.alternate_buffer_off() in result
        assert not manager.in_alternate_buffer
        assert not manager._cursor_hidden


class TestAlternateScreenContext:
    """Tests for alternate_screen context manager."""

    def test_enters_and_exits_alternate_buffer(self):
        """Test context manager enters and exits alternate buffer."""
        output = StringIO()

        with alternate_screen(output) as screen:
            assert screen.in_alternate_buffer

        # After exit, should be cleaned up
        assert not screen.in_alternate_buffer

    def test_hides_and_shows_cursor(self):
        """Test context manager hides and shows cursor."""
        output = StringIO()

        with alternate_screen(output, hide_cursor=True) as screen:
            assert screen._cursor_hidden

        # After exit, cursor should be shown
        assert not screen._cursor_hidden

    def test_no_hide_cursor_option(self):
        """Test context manager without hiding cursor."""
        output = StringIO()

        with alternate_screen(output, hide_cursor=False) as screen:
            assert not screen._cursor_hidden

    def test_cleanup_on_exception(self):
        """Test context manager cleans up on exception."""
        output = StringIO()

        try:
            with alternate_screen(output) as screen:
                assert screen.in_alternate_buffer
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should still clean up even with exception
        assert not screen.in_alternate_buffer
        assert not screen._cursor_hidden

    def test_writes_correct_codes(self):
        """Test context manager writes correct ANSI codes."""
        output = StringIO()

        with alternate_screen(output) as screen:
            pass

        result = output.getvalue()
        # Should contain enter and exit codes
        assert ANSIScreen.alternate_buffer_on() in result
        assert ANSIScreen.alternate_buffer_off() in result
        assert ANSICursor.hide() in result
        assert ANSICursor.show() in result

    def test_yields_screen_manager(self):
        """Test context manager yields a ScreenManager instance."""
        output = StringIO()

        with alternate_screen(output) as screen:
            assert isinstance(screen, ScreenManager)
            assert screen.output is output
