"""Tests for modal dialog elements."""

from unittest.mock import Mock

from wijjit.elements.modal import AlertDialog, ConfirmDialog, TextInputDialog


class TestConfirmDialog:
    """Tests for ConfirmDialog element."""

    def test_create_confirm_dialog(self):
        """Test creating a confirm dialog."""
        dialog = ConfirmDialog(
            message="Are you sure?",
            title="Confirm Action",
        )

        assert dialog.message == "Are you sure?"
        assert dialog.title == "Confirm Action"
        assert len(dialog.children) == 3  # message text, confirm button, cancel button
        assert dialog.confirm_button.label == "Confirm"
        assert dialog.cancel_button.label == "Cancel"

    def test_custom_button_labels(self):
        """Test confirm dialog with custom button labels."""
        dialog = ConfirmDialog(
            message="Delete file?",
            confirm_label="Delete",
            cancel_label="Keep",
        )

        assert dialog.confirm_button.label == "Delete"
        assert dialog.cancel_button.label == "Keep"

    def test_confirm_callback(self):
        """Test confirm button callback."""
        confirmed = Mock()
        dialog = ConfirmDialog(
            message="Continue?",
            on_confirm=confirmed,
        )

        # Simulate confirm button click
        dialog.confirm_button.activate()

        # Callback should be called
        confirmed.assert_called_once()

    def test_cancel_callback(self):
        """Test cancel button callback."""
        cancelled = Mock()
        dialog = ConfirmDialog(
            message="Continue?",
            on_cancel=cancelled,
        )

        # Simulate cancel button click
        dialog.cancel_button.activate()

        # Callback should be called
        cancelled.assert_called_once()

    def test_auto_close_on_confirm(self):
        """Test dialog auto-closes when confirm is clicked."""
        close_callback = Mock()
        dialog = ConfirmDialog(
            message="Continue?",
            on_confirm=lambda: None,
        )
        dialog.close_callback = close_callback

        # Simulate confirm button click
        dialog.confirm_button.activate()

        # Close callback should be called
        close_callback.assert_called_once()

    def test_auto_close_on_cancel(self):
        """Test dialog auto-closes when cancel is clicked."""
        close_callback = Mock()
        dialog = ConfirmDialog(
            message="Continue?",
            on_cancel=lambda: None,
        )
        dialog.close_callback = close_callback

        # Simulate cancel button click
        dialog.cancel_button.activate()

        # Close callback should be called
        close_callback.assert_called_once()

    def test_custom_dimensions(self):
        """Test confirm dialog with custom dimensions."""
        dialog = ConfirmDialog(
            message="Test",
            width=60,
            height=15,
        )

        assert dialog.width == 60
        assert dialog.height == 15


class TestAlertDialog:
    """Tests for AlertDialog element."""

    def test_create_alert_dialog(self):
        """Test creating an alert dialog."""
        dialog = AlertDialog(
            message="Operation completed!",
            title="Success",
        )

        assert dialog.message == "Operation completed!"
        assert dialog.title == "Success"
        assert len(dialog.children) == 2  # message text, ok button
        assert dialog.ok_button.label == "OK"

    def test_custom_ok_label(self):
        """Test alert dialog with custom OK button label."""
        dialog = AlertDialog(
            message="Info",
            ok_label="Got it",
        )

        assert dialog.ok_button.label == "Got it"

    def test_ok_callback(self):
        """Test OK button callback."""
        ok_pressed = Mock()
        dialog = AlertDialog(
            message="Done!",
            on_ok=ok_pressed,
        )

        # Simulate OK button click
        dialog.ok_button.activate()

        # Callback should be called
        ok_pressed.assert_called_once()

    def test_auto_close_on_ok(self):
        """Test dialog auto-closes when OK is clicked."""
        close_callback = Mock()
        dialog = AlertDialog(
            message="Done!",
            on_ok=lambda: None,
        )
        dialog.close_callback = close_callback

        # Simulate OK button click
        dialog.ok_button.activate()

        # Close callback should be called
        close_callback.assert_called_once()

    def test_custom_dimensions(self):
        """Test alert dialog with custom dimensions."""
        dialog = AlertDialog(
            message="Test",
            width=45,
            height=7,
        )

        assert dialog.width == 45
        assert dialog.height == 7


class TestTextInputDialog:
    """Tests for TextInputDialog element."""

    def test_create_input_dialog(self):
        """Test creating a text input dialog."""
        dialog = TextInputDialog(
            prompt="Enter your name:",
            title="Name Input",
        )

        assert dialog.prompt == "Enter your name:"
        assert dialog.title == "Name Input"
        assert (
            len(dialog.children) == 4
        )  # prompt text, input, submit button, cancel button
        assert dialog.text_input.value == ""
        assert dialog.submit_button.label == "Submit"
        assert dialog.cancel_button.label == "Cancel"

    def test_initial_value(self):
        """Test input dialog with initial value."""
        dialog = TextInputDialog(
            prompt="Rename:",
            initial_value="oldname.txt",
        )

        assert dialog.text_input.value == "oldname.txt"

    def test_placeholder(self):
        """Test input dialog with placeholder."""
        dialog = TextInputDialog(
            prompt="Enter filename:",
            placeholder="untitled.txt",
        )

        assert dialog.text_input.placeholder == "untitled.txt"

    def test_submit_callback(self):
        """Test submit button callback with input value."""
        submitted_value = None

        def on_submit(value):
            nonlocal submitted_value
            submitted_value = value

        dialog = TextInputDialog(
            prompt="Name:",
            on_submit=on_submit,
        )

        # Set input value
        dialog.text_input.value = "test.txt"

        # Simulate submit button click
        dialog.submit_button.activate()

        # Callback should receive the input value
        assert submitted_value == "test.txt"

    def test_cancel_callback(self):
        """Test cancel button callback."""
        cancelled = Mock()
        dialog = TextInputDialog(
            prompt="Name:",
            on_cancel=cancelled,
        )

        # Simulate cancel button click
        dialog.cancel_button.activate()

        # Callback should be called
        cancelled.assert_called_once()

    def test_auto_close_on_submit(self):
        """Test dialog auto-closes when submit is clicked."""
        close_callback = Mock()
        dialog = TextInputDialog(
            prompt="Name:",
            on_submit=lambda value: None,
        )
        dialog.close_callback = close_callback

        # Simulate submit button click
        dialog.submit_button.activate()

        # Close callback should be called
        close_callback.assert_called_once()

    def test_auto_close_on_cancel(self):
        """Test dialog auto-closes when cancel is clicked."""
        close_callback = Mock()
        dialog = TextInputDialog(
            prompt="Name:",
            on_cancel=lambda: None,
        )
        dialog.close_callback = close_callback

        # Simulate cancel button click
        dialog.cancel_button.activate()

        # Close callback should be called
        close_callback.assert_called_once()

    def test_custom_button_labels(self):
        """Test input dialog with custom button labels."""
        dialog = TextInputDialog(
            prompt="Name:",
            submit_label="Save",
            cancel_label="Discard",
        )

        assert dialog.submit_button.label == "Save"
        assert dialog.cancel_button.label == "Discard"

    def test_custom_dimensions(self):
        """Test input dialog with custom dimensions."""
        dialog = TextInputDialog(
            prompt="Name:",
            width=55,
            height=14,
            input_width=35,
        )

        assert dialog.width == 55
        assert dialog.height == 14
        assert dialog.text_input.width == 35
