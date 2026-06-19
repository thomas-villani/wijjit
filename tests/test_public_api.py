"""Tests for the top-level ``wijjit`` public API surface.

These guard the re-export contract: documented/headline names must be
importable directly from ``wijjit`` (not only via deep module paths), and
``__all__`` must stay consistent with what the package actually exposes.
"""

import wijjit


class TestAllConsistency:
    """``__all__`` must be self-consistent and fully resolvable."""

    def test_all_entries_are_resolvable(self):
        missing = [name for name in wijjit.__all__ if not hasattr(wijjit, name)]
        assert not missing, f"__all__ names not defined on package: {missing}"

    def test_all_has_no_duplicates(self):
        seen = set()
        dupes = set()
        for name in wijjit.__all__:
            if name in seen:
                dupes.add(name)
            seen.add(name)
        assert not dupes, f"duplicate __all__ entries: {sorted(dupes)}"


class TestAutocompleteReexports:
    """Autocomplete is a headline feature - its classes must be top-level."""

    def test_completer_classes_importable(self):
        from wijjit import (
            AsyncCompleter,
            CallbackCompleter,
            Completer,
            CompleterConfig,
            StateCompleter,
            WordCompleter,
        )

        # Each should be the same object as the canonical module export.
        from wijjit.autocomplete import completer as canon

        assert Completer is canon.Completer
        assert WordCompleter is canon.WordCompleter
        assert CallbackCompleter is canon.CallbackCompleter
        assert AsyncCompleter is canon.AsyncCompleter
        assert StateCompleter is canon.StateCompleter
        assert CompleterConfig is canon.CompleterConfig

    def test_completer_classes_in_all(self):
        for name in (
            "Completer",
            "WordCompleter",
            "CallbackCompleter",
            "AsyncCompleter",
            "StateCompleter",
            "CompleterConfig",
        ):
            assert name in wijjit.__all__


class TestModalNotificationAliases:
    """Documented friendly names ``Modal`` / ``Notification`` resolve."""

    def test_modal_alias_is_modal_element(self):
        from wijjit import Modal, ModalElement

        assert Modal is ModalElement
        assert "Modal" in wijjit.__all__

    def test_notification_alias_is_notification_element(self):
        from wijjit import Notification, NotificationElement

        assert Notification is NotificationElement
        assert "Notification" in wijjit.__all__

    def test_legacy_element_names_still_exported(self):
        # Backward compatibility: the *Element names remain available.
        assert "ModalElement" in wijjit.__all__
        assert "NotificationElement" in wijjit.__all__


class TestDialogReexports:
    """Dialog classes are documented public elements - re-export them."""

    def test_dialog_classes_importable(self):
        from wijjit import AlertDialog, ConfirmDialog, ModalElement, TextInputDialog

        # All three are ModalElement subclasses.
        assert issubclass(ConfirmDialog, ModalElement)
        assert issubclass(AlertDialog, ModalElement)
        assert issubclass(TextInputDialog, ModalElement)

    def test_dialog_classes_in_all(self):
        for name in ("ConfirmDialog", "AlertDialog", "TextInputDialog"):
            assert name in wijjit.__all__
