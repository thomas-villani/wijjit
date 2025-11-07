"""Tests for keyboard input handling."""

from unittest.mock import Mock, patch
import pytest

from prompt_toolkit.keys import Keys as PTKeys
from prompt_toolkit.key_binding.key_processor import KeyPress

from wijjit.terminal.input import (
    Key,
    KeyType,
    Keys,
    InputHandler,
    ESCAPE_SEQUENCES,
    SINGLE_CHAR_KEYS,
    PROMPT_TOOLKIT_KEY_MAP,
)


class TestKey:
    """Tests for Key dataclass."""

    def test_key_creation(self):
        """Test creating a Key instance."""
        key = Key("a", KeyType.CHARACTER, "a")
        assert key.name == "a"
        assert key.key_type == KeyType.CHARACTER
        assert key.char == "a"

    def test_key_without_char(self):
        """Test creating a Key without char."""
        key = Key("up", KeyType.SPECIAL)
        assert key.name == "up"
        assert key.key_type == KeyType.SPECIAL
        assert key.char is None

    def test_key_str(self):
        """Test Key string representation."""
        key = Key("enter", KeyType.SPECIAL)
        assert str(key) == "enter"

    def test_is_char(self):
        """Test is_char property."""
        char_key = Key("a", KeyType.CHARACTER, "a")
        special_key = Key("up", KeyType.SPECIAL)

        assert char_key.is_char
        assert not special_key.is_char

    def test_is_special(self):
        """Test is_special property."""
        char_key = Key("a", KeyType.CHARACTER, "a")
        special_key = Key("up", KeyType.SPECIAL)

        assert not char_key.is_special
        assert special_key.is_special

    def test_is_control(self):
        """Test is_control property."""
        char_key = Key("a", KeyType.CHARACTER, "a")
        control_key = Key("ctrl+c", KeyType.CONTROL, "\x03")

        assert not char_key.is_control
        assert control_key.is_control

    def test_key_immutable(self):
        """Test that Key is immutable (frozen dataclass)."""
        key = Key("a", KeyType.CHARACTER, "a")

        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.10+
            key.name = "b"


class TestKeys:
    """Tests for Keys constants."""

    def test_special_keys(self):
        """Test special key definitions."""
        assert Keys.ENTER.name == "enter"
        assert Keys.TAB.name == "tab"
        assert Keys.ESCAPE.name == "escape"
        assert Keys.BACKSPACE.name == "backspace"

    def test_arrow_keys(self):
        """Test arrow key definitions."""
        assert Keys.UP.name == "up"
        assert Keys.DOWN.name == "down"
        assert Keys.LEFT.name == "left"
        assert Keys.RIGHT.name == "right"

    def test_navigation_keys(self):
        """Test navigation key definitions."""
        assert Keys.HOME.name == "home"
        assert Keys.END.name == "end"
        assert Keys.PAGE_UP.name == "pageup"
        assert Keys.PAGE_DOWN.name == "pagedown"

    def test_control_keys(self):
        """Test control key definitions."""
        assert Keys.CTRL_C.name == "ctrl+c"
        assert Keys.CTRL_D.name == "ctrl+d"
        assert Keys.CTRL_Z.name == "ctrl+z"


class TestEscapeSequences:
    """Tests for escape sequence mappings."""

    def test_arrow_sequences(self):
        """Test arrow key escape sequences."""
        assert ESCAPE_SEQUENCES["\x1b[A"] == Keys.UP
        assert ESCAPE_SEQUENCES["\x1b[B"] == Keys.DOWN
        assert ESCAPE_SEQUENCES["\x1b[C"] == Keys.RIGHT
        assert ESCAPE_SEQUENCES["\x1b[D"] == Keys.LEFT

    def test_navigation_sequences(self):
        """Test navigation key escape sequences."""
        assert ESCAPE_SEQUENCES["\x1b[H"] == Keys.HOME
        assert ESCAPE_SEQUENCES["\x1b[F"] == Keys.END
        assert ESCAPE_SEQUENCES["\x1b[5~"] == Keys.PAGE_UP
        assert ESCAPE_SEQUENCES["\x1b[6~"] == Keys.PAGE_DOWN

    def test_delete_sequence(self):
        """Test delete key escape sequence."""
        assert ESCAPE_SEQUENCES["\x1b[3~"] == Keys.DELETE


class TestSingleCharKeys:
    """Tests for single character key mappings."""

    def test_enter_mapping(self):
        """Test enter key mappings."""
        assert SINGLE_CHAR_KEYS["\r"] == Keys.ENTER
        assert SINGLE_CHAR_KEYS["\n"] == Keys.ENTER

    def test_special_char_mappings(self):
        """Test special character mappings."""
        assert SINGLE_CHAR_KEYS["\t"] == Keys.TAB
        assert SINGLE_CHAR_KEYS["\x1b"] == Keys.ESCAPE
        assert SINGLE_CHAR_KEYS[" "] == Keys.SPACE

    def test_control_char_mappings(self):
        """Test control character mappings."""
        assert SINGLE_CHAR_KEYS["\x03"] == Keys.CTRL_C
        assert SINGLE_CHAR_KEYS["\x04"] == Keys.CTRL_D


class TestPromptToolkitKeyMap:
    """Tests for prompt_toolkit key mapping."""

    def test_arrow_key_mappings(self):
        """Test arrow key mappings."""
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Up] == Keys.UP
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Down] == Keys.DOWN
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Left] == Keys.LEFT
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Right] == Keys.RIGHT

    def test_navigation_key_mappings(self):
        """Test navigation key mappings."""
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Home] == Keys.HOME
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.End] == Keys.END
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.PageUp] == Keys.PAGE_UP
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.PageDown] == Keys.PAGE_DOWN

    def test_special_key_mappings(self):
        """Test special key mappings."""
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Enter] == Keys.ENTER
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Tab] == Keys.TAB
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Escape] == Keys.ESCAPE
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Delete] == Keys.DELETE
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.Backspace] == Keys.BACKSPACE

    def test_control_key_mappings(self):
        """Test control key mappings."""
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.ControlC] == Keys.CTRL_C
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.ControlD] == Keys.CTRL_D
        assert PROMPT_TOOLKIT_KEY_MAP[PTKeys.ControlZ] == Keys.CTRL_Z


class TestInputHandler:
    """Tests for InputHandler class."""

    @patch("wijjit.terminal.input.create_input")
    def test_init(self, mock_create_input):
        """Test InputHandler initialization."""
        mock_input = Mock()
        mock_create_input.return_value = mock_input

        handler = InputHandler()

        assert handler._input == mock_input
        mock_create_input.assert_called_once()

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_regular_char(self, mock_create_input):
        """Test reading a regular character."""
        mock_input = Mock()
        mock_input.read_keys.return_value = [KeyPress("a", "a")]
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is not None
        assert key.name == "a"
        assert key.is_char
        assert key.char == "a"

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_space(self, mock_create_input):
        """Test reading space key."""
        mock_input = Mock()
        mock_input.read_keys.return_value = [KeyPress(" ", " ")]
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is not None
        assert key == Keys.SPACE

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_arrow_up(self, mock_create_input):
        """Test reading up arrow key."""
        mock_input = Mock()
        mock_input.read_keys.return_value = [KeyPress(PTKeys.Up, "")]
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is not None
        assert key.name == "up"
        assert key == Keys.UP

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_enter(self, mock_create_input):
        """Test reading enter key."""
        mock_input = Mock()
        mock_input.read_keys.return_value = [KeyPress(PTKeys.Enter, "")]
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is not None
        assert key.name == "enter"
        assert key == Keys.ENTER

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_ctrl_c(self, mock_create_input):
        """Test reading Ctrl+C."""
        mock_input = Mock()
        mock_input.read_keys.return_value = [KeyPress(PTKeys.ControlC, "")]
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is not None
        assert key.name == "ctrl+c"
        assert key == Keys.CTRL_C

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_control_letter(self, mock_create_input):
        """Test reading Ctrl+letter combination."""
        mock_input = Mock()
        # Create a mock KeyPress with the proper structure
        key_press = Mock()
        key_press.key = "c-a"
        key_press.data = ""
        mock_input.read_keys.return_value = [key_press]
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is not None
        assert key.name == "ctrl+a"
        assert key.is_control

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_eof(self, mock_create_input):
        """Test reading on EOF."""
        mock_input = Mock()
        mock_input.read_keys.side_effect = EOFError()
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is None

    @patch("wijjit.terminal.input.create_input")
    def test_read_key_keyboard_interrupt(self, mock_create_input):
        """Test reading on keyboard interrupt."""
        mock_input = Mock()
        mock_input.read_keys.side_effect = KeyboardInterrupt()
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        key = handler.read_key()

        assert key is None

    @patch("wijjit.terminal.input.create_input")
    def test_close(self, mock_create_input):
        """Test closing input handler."""
        mock_input = Mock()
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        handler.close()

        mock_input.close.assert_called_once()

    @patch("wijjit.terminal.input.create_input")
    def test_cleanup(self, mock_create_input):
        """Test cleanup method."""
        mock_input = Mock()
        mock_create_input.return_value = mock_input

        handler = InputHandler()
        handler.cleanup()

        mock_input.close.assert_called_once()
