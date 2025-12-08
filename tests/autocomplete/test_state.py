"""Tests for autocomplete state management."""

from wijjit.autocomplete.state import AutocompleteState


class TestAutocompleteState:
    """Tests for AutocompleteState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = AutocompleteState()
        assert state.is_open is False
        assert state.suggestions == []
        assert state.highlighted_index == 0
        assert state.word_start == 0
        assert state.word_end == 0
        assert state.prefix == ""

    def test_custom_initialization(self):
        """Test custom initialization values."""
        state = AutocompleteState(
            is_open=True,
            suggestions=["a", "b", "c"],
            highlighted_index=1,
            word_start=5,
            word_end=8,
            prefix="abc",
        )
        assert state.is_open is True
        assert state.suggestions == ["a", "b", "c"]
        assert state.highlighted_index == 1
        assert state.word_start == 5
        assert state.word_end == 8
        assert state.prefix == "abc"

    def test_reset(self):
        """Test reset method clears all state."""
        state = AutocompleteState(
            is_open=True,
            suggestions=["a", "b", "c"],
            highlighted_index=2,
            word_start=10,
            word_end=15,
            prefix="test",
        )

        state.reset()

        assert state.is_open is False
        assert state.suggestions == []
        assert state.highlighted_index == 0
        assert state.word_start == 0
        assert state.word_end == 0
        assert state.prefix == ""

    def test_move_highlight_down(self):
        """Test moving highlight down."""
        state = AutocompleteState(suggestions=["a", "b", "c"])
        assert state.highlighted_index == 0

        state.move_highlight(1)
        assert state.highlighted_index == 1

        state.move_highlight(1)
        assert state.highlighted_index == 2

    def test_move_highlight_up(self):
        """Test moving highlight up."""
        state = AutocompleteState(suggestions=["a", "b", "c"], highlighted_index=2)

        state.move_highlight(-1)
        assert state.highlighted_index == 1

        state.move_highlight(-1)
        assert state.highlighted_index == 0

    def test_move_highlight_clamps_at_bottom(self):
        """Test highlight clamps at bottom (no wrap)."""
        state = AutocompleteState(suggestions=["a", "b", "c"], highlighted_index=2)

        state.move_highlight(1)
        assert state.highlighted_index == 2  # Stays at bottom

    def test_move_highlight_clamps_at_top(self):
        """Test highlight clamps at top (no wrap)."""
        state = AutocompleteState(suggestions=["a", "b", "c"], highlighted_index=0)

        state.move_highlight(-1)
        assert state.highlighted_index == 0  # Stays at top

    def test_move_highlight_empty_suggestions(self):
        """Test moving highlight with empty suggestions does nothing."""
        state = AutocompleteState(suggestions=[])

        state.move_highlight(1)
        assert state.highlighted_index == 0

        state.move_highlight(-1)
        assert state.highlighted_index == 0

    def test_move_highlight_large_jump(self):
        """Test highlight with large jump is clamped."""
        state = AutocompleteState(suggestions=["a", "b", "c", "d", "e"])
        state.highlighted_index = 2

        state.move_highlight(10)
        assert state.highlighted_index == 4  # Clamped to last

        state.move_highlight(-10)
        assert state.highlighted_index == 0  # Clamped to first

    def test_selected_suggestion(self):
        """Test selected_suggestion property."""
        state = AutocompleteState(suggestions=["apple", "banana", "cherry"])

        state.highlighted_index = 0
        assert state.selected_suggestion == "apple"

        state.highlighted_index = 1
        assert state.selected_suggestion == "banana"

        state.highlighted_index = 2
        assert state.selected_suggestion == "cherry"

    def test_selected_suggestion_empty(self):
        """Test selected_suggestion with empty suggestions."""
        state = AutocompleteState(suggestions=[])
        assert state.selected_suggestion is None

    def test_selected_suggestion_out_of_bounds(self):
        """Test selected_suggestion with out of bounds index."""
        state = AutocompleteState(suggestions=["a"], highlighted_index=5)
        assert state.selected_suggestion is None

        state = AutocompleteState(suggestions=["a"], highlighted_index=-1)
        assert state.selected_suggestion is None

    def test_has_suggestions(self):
        """Test has_suggestions property."""
        state = AutocompleteState()
        assert state.has_suggestions is False

        state.suggestions = ["a"]
        assert state.has_suggestions is True

        state.suggestions = []
        assert state.has_suggestions is False

    def test_suggestion_count(self):
        """Test suggestion_count property."""
        state = AutocompleteState()
        assert state.suggestion_count == 0

        state.suggestions = ["a", "b", "c"]
        assert state.suggestion_count == 3

    def test_update_suggestions_opens_popup(self):
        """Test update_suggestions opens popup when suggestions exist."""
        state = AutocompleteState()
        assert state.is_open is False

        state.update_suggestions(["a", "b"], prefix="test", word_start=0, word_end=4)

        assert state.is_open is True
        assert state.suggestions == ["a", "b"]
        assert state.prefix == "test"
        assert state.word_start == 0
        assert state.word_end == 4
        assert state.highlighted_index == 0

    def test_update_suggestions_closes_popup_when_empty(self):
        """Test update_suggestions closes popup when no suggestions."""
        state = AutocompleteState(is_open=True, suggestions=["a", "b"])

        state.update_suggestions([], prefix="x", word_start=0, word_end=1)

        assert state.is_open is False
        assert state.suggestions == []

    def test_update_suggestions_resets_highlight(self):
        """Test update_suggestions resets highlight to first item."""
        state = AutocompleteState(
            is_open=True, suggestions=["a", "b", "c"], highlighted_index=2
        )

        state.update_suggestions(
            ["x", "y", "z"], prefix="new", word_start=0, word_end=3
        )

        assert state.highlighted_index == 0

    def test_select_first(self):
        """Test select_first method."""
        state = AutocompleteState(suggestions=["a", "b", "c"], highlighted_index=2)

        state.select_first()
        assert state.highlighted_index == 0

    def test_select_last(self):
        """Test select_last method."""
        state = AutocompleteState(suggestions=["a", "b", "c"], highlighted_index=0)

        state.select_last()
        assert state.highlighted_index == 2

    def test_select_last_empty_suggestions(self):
        """Test select_last with empty suggestions."""
        state = AutocompleteState(suggestions=[])

        state.select_last()
        assert state.highlighted_index == 0  # Unchanged
