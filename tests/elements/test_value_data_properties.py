"""Uniform value/data/lines/max_value access surface (audit D6 / CC-6).

Sibling elements previously diverged on how "the current content" is read and
written: TextArea/CodeEditor had only get_value/set_value (no ``.value``),
Table exposed ``data`` as a raw field that desynced ``_raw_data`` and scroll,
LogView had only ``set_lines`` (no ``lines`` property), and ProgressBar used a
builtin-shadowing ``max``. These tests pin the unified, delegating surface.
"""

from wijjit.elements.display.logview import LogView
from wijjit.elements.display.progress import ProgressBar
from wijjit.elements.display.table import Table
from wijjit.elements.input.code_editor import CodeEditor
from wijjit.elements.input.text import TextArea


class TestTextAreaValue:
    def test_read(self):
        assert TextArea(value="a\nb").value == "a\nb"

    def test_write_delegates_to_set_value(self):
        ta = TextArea(value="old")
        ta.value = "new content"
        assert ta.value == "new content"
        assert ta.get_value() == "new content"

    def test_noop_write_preserves_cursor(self):
        # value is reconciled (not ephemeral); re-assigning the same content
        # must not reset the cursor (which set_value would do).
        ta = TextArea(value="hello\nworld")
        ta.cursor_row, ta.cursor_col = 1, 3
        ta.value = "hello\nworld"
        assert (ta.cursor_row, ta.cursor_col) == (1, 3)

    def test_code_editor_inherits_value(self):
        ce = CodeEditor(value="x = 1")
        assert ce.value == "x = 1"
        ce.value = "y = 2"
        assert ce.value == "y = 2"


class TestTableData:
    def test_assignment_syncs_raw_and_scroll(self):
        t = Table(data=[{"a": 1}], columns=["a"])
        t.data = [{"a": 1}, {"a": 2}, {"a": 3}]
        assert t.data == [{"a": 1}, {"a": 2}, {"a": 3}]
        assert t._raw_data == [{"a": 1}, {"a": 2}, {"a": 3}]
        assert t.scroll_manager.state.content_size == 3

    def test_set_data_matches_property(self):
        t = Table(data=[], columns=["a"])
        t.set_data([{"a": 9}])
        assert t.data == [{"a": 9}]
        assert t._raw_data == [{"a": 9}]


class TestLogViewLines:
    def test_assignment_delegates_to_set_lines(self):
        lv = LogView(lines=["a"])
        lv.lines = ["x", "y", "z"]
        assert lv.lines == ["x", "y", "z"]
        assert lv.scroll_manager.state.content_size >= 3


class TestProgressBarMaxValue:
    def test_max_value_canonical(self):
        p = ProgressBar(value=25, max_value=50)
        assert p.max_value == 50
        assert abs(p.get_percentage() - 50.0) < 0.01

    def test_max_alias_constructor(self):
        p = ProgressBar(value=25, max=200)
        assert p.max_value == 200
        assert p.max == 200

    def test_alias_assignment_both_directions(self):
        p = ProgressBar()
        p.max = 10
        assert p.max_value == 10
        p.max_value = 20
        assert p.max == 20
